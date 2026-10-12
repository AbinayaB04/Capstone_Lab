import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from database.vector_manager import search_documents

try:
    # pyrefly: ignore [missing-import]
    from groq import Groq
except ImportError:
    Groq = None

try:
    # pyrefly: ignore [missing-import]
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

class AIEngine:
    def __init__(self, primary_model="gemini-3.8-flash", fallback_model="qwen/qwen3.8-27b"):
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        
    def needs_search(self, query):
        """Use Groq (fast) to determine if a web search is needed."""
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key or not Groq:
            return False
            
        try:
            client = Groq(api_key=groq_api_key)
            prompt = f"Does this query require current, live internet data or extremely specific external facts to answer correctly? Answer only 'yes' or 'no'. Query: '{query}'"
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="qwen/qwen3.8-27b",
                temperature=0.1
            )
            return "yes" in response.choices[0].message.content.lower()
        except Exception:
            return False

    def perform_search(self, query):
        """CRAG: Perform a web search."""
        if not DDGS: return ""
        try:
            results = DDGS().text(query, max_results=3)
            context = "Here is some context from the web:\n"
            for res in results:
                context += f"- {res.get('title', '')}: {res.get('body', '')}\n"
            return context
        except Exception:
            return ""

    def generate_response(self, query, chat_history=None, department_id=None, branch_id=None, course_code=None, return_sources=False):
        load_dotenv(override=True)
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        if (not gemini_api_key or gemini_api_key == "your_api_key_here") and (not groq_api_key or groq_api_key == "your_api_key_here"):
            err_msg = "⚠️ **API Keys not configured.** Please add GEMINI_API_KEY or GROQ_API_KEY to `.env`."
            return {"answer": err_msg, "sources": []} if return_sources else err_msg
            
        # 0. Vector Semantic Caching
        from database.redis_manager import check_cache, set_cache, init_redis_index
        from chromadb.utils import embedding_functions
        
        # Initialize index if it doesn't exist
        init_redis_index()
        
        # Embed the question
        emb_fn = embedding_functions.DefaultEmbeddingFunction()
        query_vector = emb_fn([query])[0]
        
        # Check cache
        if course_code:
            cached_answer = check_cache(query_vector, str(course_code))
            if cached_answer:
                print("🟢 CACHE HIT! Saving API money.")
                res_str = cached_answer + "\n\n*(Served from AI Cache ⚡)*"
                return {"answer": res_str, "sources": []} if return_sources else res_str

        # 1. RAG: Fetch from ChromaDB if course_code is provided
        rag_context = ""
        sources_list = []
        MAX_CONTEXT_CHARS = 15000
        if department_id and branch_id and course_code:
            search_results = search_documents(query, department_id, branch_id, course_code, n_results=3)
            docs = search_results.get("documents", [])
            metas = search_results.get("metadatas", [])
            if docs and len(docs) > 0:
                rag_context = "Here is some relevant context directly from the course syllabus/materials:\n"
                current_chars = len(rag_context)
                for i, doc_chunk in enumerate(docs[0]):
                    source_meta = metas[0][i].get("source", f"Excerpt {i+1}") if metas and len(metas[0]) > i else f"Excerpt {i+1}"
                    sources_list.append({"source": source_meta, "content": doc_chunk[:250] + ("..." if len(doc_chunk) > 250 else "")})
                    chunk_text = f"--- Source: {source_meta} ---\n{doc_chunk}\n\n"
                    if current_chars + len(chunk_text) > MAX_CONTEXT_CHARS:
                        remaining_space = MAX_CONTEXT_CHARS - current_chars
                        if remaining_space > 100:
                            rag_context += f"--- Source: {source_meta} ---\n{doc_chunk[:remaining_space]}... [TRUNCATED DUE TO LENGTH]\n\n"
                        break
                    rag_context += chunk_text
                    current_chars += len(chunk_text)

        # 2. CRAG: Check if we need live internet search context
        search_context = ""
        if self.needs_search(query):
            search_context = self.perform_search(query)
            
        final_query = query
        if rag_context or search_context:
            final_query = f"""
{rag_context}
{search_context}

SYSTEM INSTRUCTIONS:
1. Based on the context provided above, please answer the student's question.
2. If you use information from the context, you MUST cite the source (e.g. "According to Page 4...").
3. GUARDRAIL: Do not answer questions that require you to write code, do homework, or perform tasks entirely unrelated to the provided syllabus context unless it is explicitly requested in the context.

User Question: {query}
"""

        # 2. Try Primary LLM (Gemini)
        if gemini_api_key and gemini_api_key != "your_api_key_here":
            try:
                client = genai.Client(api_key=gemini_api_key)
                history = []
                if chat_history:
                    for msg in chat_history:
                        role = "user" if msg["role"] == "user" else "model"
                        history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))
                
                chat = client.chats.create(model=self.primary_model, history=history)
                response = chat.send_message(final_query)
                answer = response.text
                
                # Cache the answer
                if course_code:
                    set_cache(query_vector, query, str(course_code), answer)
                    
                return {"answer": answer, "sources": sources_list} if return_sources else answer
            except Exception as e:
                error_str = str(e).lower()
                # If it's a 503, quota, or 404 issue, failover to Groq
                if "503" in error_str or "unavailable" in error_str or "quota" in error_str or "429" in error_str or "404" in error_str or "not_found" in error_str:
                    print("Gemini API failed, falling back to Groq...")
                    pass # Fall through to Groq
                else:
                    err = f"❌ Gemini Error: {str(e)}"
                    return {"answer": err, "sources": []} if return_sources else err

        # 3. Failover to Groq (Llama-3)
        if groq_api_key and groq_api_key != "your_api_key_here":
            if not Groq:
                err = "❌ Groq library not installed. Please run: pip install groq"
                return {"answer": err, "sources": []} if return_sources else err
            try:
                client = Groq(api_key=groq_api_key)
                messages = []
                if chat_history:
                    for msg in chat_history:
                        # Map assistant back to assistant for standard OpenAI/Groq API
                        role = msg["role"]
                        if role == "model": role = "assistant"
                        messages.append({"role": role, "content": msg["content"]})
                messages.append({"role": "user", "content": final_query})
                
                completion = client.chat.completions.create(
                    messages=messages,
                    model=self.fallback_model,
                )
                
                answer = completion.choices[0].message.content + "\n\n*(Answered by Llama-3 Backup Engine due to high Gemini traffic)*"
                
                # Cache the fallback answer too
                if course_code:
                    set_cache(query_vector, query, str(course_code), answer)
                    
                return {"answer": answer, "sources": sources_list} if return_sources else answer
            except Exception as e:
                err = f"❌ Dual-Mesh Failure (Both Gemini & Groq failed): {str(e)}"
                return {"answer": err, "sources": []} if return_sources else err
                
    def generate_exam(self, course_code, department_id, branch_id, num_questions=5, difficulty="medium"):
        """Generates a JSON multiple choice quiz rapidly and directly based on course context."""
        load_dotenv(override=True)
        from database.vector_manager import search_documents
        context = search_documents("Key concepts, definitions, and core principles", department_id, branch_id, course_code, n_results=4)
        
        if not context or not context.get("documents") or len(context["documents"][0]) == 0:
            return None
            
        # Limit context to 4,500 characters for high speed and precision
        formatted_context = ""
        MAX_EXAM_CHARS = 4500
        for chunk in context["documents"][0]:
            if len(formatted_context) + len(chunk) > MAX_EXAM_CHARS:
                formatted_context += chunk[:MAX_EXAM_CHARS - len(formatted_context)] + "..."
                break
            formatted_context += chunk + "\n\n"
            
        prompt = f"""You are an expert professor. Based ONLY on the following textbook context, generate a {num_questions}-question multiple choice quiz at a {difficulty} difficulty level.
The quiz MUST be returned in raw JSON format as an array of objects:
[
  {{
    "question": "Clear question text?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": "Option B",
    "explanation": "Detailed explanation of why this option is correct based on the syllabus."
  }}
]

Context:
{formatted_context}
"""
        
        groq_api_key = os.getenv("GROQ_API_KEY")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        response_text = None
        
        # 1. High-speed completion using Groq (approx 2-3 seconds)
        if groq_api_key and groq_api_key != "your_api_key_here" and Groq:
            try:
                client = Groq(api_key=groq_api_key)
                completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.fallback_model,
                    temperature=0.2
                )
                response_text = completion.choices[0].message.content
            except Exception as ge:
                print(f"Groq exam generation warning: {ge}")
                
        # 2. Fallback to Gemini if Groq is unavailable
        if not response_text and gemini_api_key and gemini_api_key != "your_api_key_here":
            try:
                client = genai.Client(api_key=gemini_api_key)
                res = client.models.generate_content(
                    model=self.primary_model,
                    contents=prompt
                )
                response_text = res.text
            except Exception as gme:
                print(f"Gemini exam generation warning: {gme}")
                
        if not response_text:
            return None
            
        import json
        try:
            json_str = response_text.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            quiz = json.loads(json_str.strip())
            for q in quiz:
                if "explanation" not in q or not q["explanation"]:
                    q["explanation"] = f"Correct answer is '{q.get('answer', '')}' based on the course materials."
            return quiz
        except Exception as e:
            print(f"Failed to parse exam JSON: {e}\nRaw response: {response_text}")
            return None


