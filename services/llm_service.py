import os
import urllib.parse
import re
import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv(override=True)
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

    def correct_spelling(self, query: str) -> str:
        """
        Detects and fixes spelling mistakes, typographical errors, and phonetic slips in queries.
        Returns the clean, normalized query string.
        """
        if not query or len(query.strip()) < 3:
            return query

        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key and groq_api_key != "your_api_key_here" and Groq:
            try:
                client = Groq(api_key=groq_api_key)
                prompt = (
                    "You are an academic search query spell-checker. Correct all typographical errors, "
                    "spelling mistakes, and phonetic slips in the user query while preserving exact technical "
                    "terms (e.g. DBMS, SQL, B-tree, normalization, ACID, OOP, recursion, etc.). "
                    "Return ONLY the corrected query string without any quotes, explanations, or introductory text. "
                    "If there are no spelling mistakes, return the query exactly as it is.\n\n"
                    f"User Query: {query}"
                )
                res = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.fallback_model,
                    temperature=0.0,
                    max_tokens=60
                )
                corrected = res.choices[0].message.content.strip().strip('"\'')
                if corrected and len(corrected) > 0 and len(corrected) < len(query) * 2:
                    return corrected
            except Exception as e:
                print(f"Spelling correction warning: {e}")
                
        return query
        
    def needs_search(self, query: str) -> bool:
        """Determine if a query requires external/live internet search."""
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key or not Groq:
            return False
            
        try:
            client = Groq(api_key=groq_api_key)
            prompt = f"Does this query require current, live internet data or external facts beyond typical textbook knowledge? Answer only 'yes' or 'no'. Query: '{query}'"
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.fallback_model,
                temperature=0.1,
                max_tokens=10
            )
            return "yes" in response.choices[0].message.content.lower()
        except Exception:
            return False

    def perform_web_search(self, query: str):
        """
        Performs web search across DuckDuckGo and Wikipedia to retrieve authoritative context.
        Returns (formatted_context_string, sources_list)
        """
        web_sources = []
        context_parts = []
        
        # 1. DuckDuckGo Instant Answer API
        try:
            ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
            r = requests.get(ddg_url, headers={"User-Agent": "StudyMateApp/1.0"}, timeout=3.5)
            if r.status_code == 200:
                data = r.json()
                abstract = data.get("AbstractText")
                if abstract:
                    title = data.get("Heading", "DuckDuckGo Knowledge")
                    url = data.get("AbstractURL") or "https://duckduckgo.com"
                    web_sources.append({"source": f"🌐 {title}", "content": abstract, "url": url})
                    context_parts.append(f"Source: {title} ({url})\n{abstract}")
                for topic in data.get("RelatedTopics", [])[:2]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        t_text = topic.get("Text")
                        t_url = topic.get("FirstURL", "")
                        web_sources.append({"source": "🌐 Related Web Reference", "content": t_text, "url": t_url})
                        context_parts.append(f"Related Topic ({t_url}):\n{t_text}")
        except Exception as e:
            print(f"DuckDuckGo search warning: {e}")
            
        # 2. Wikipedia API Search + Summary
        try:
            wiki_search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&utf8=&srlimit=2"
            r = requests.get(wiki_search_url, headers={"User-Agent": "StudyMateApp/1.0"}, timeout=3.5)
            if r.status_code == 200:
                hits = r.json().get("query", {}).get("search", [])
                for item in hits:
                    t = item.get("title")
                    s = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
                    wiki_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(t)}"
                    try:
                        sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(t)}"
                        sr = requests.get(sum_url, headers={"User-Agent": "StudyMateApp/1.0"}, timeout=2.5)
                        if sr.status_code == 200 and sr.json().get("extract"):
                            s = sr.json().get("extract")
                    except Exception:
                        pass
                    web_sources.append({"source": f"🌐 Wikipedia: {t}", "content": s, "url": wiki_url})
                    context_parts.append(f"Source: Wikipedia - {t} ({wiki_url})\n{s}")
                    if len(web_sources) >= 3:
                        break
        except Exception as e:
            print(f"Wikipedia search warning: {e}")
            
        formatted_context = "\n\n".join(context_parts)
        return formatted_context, web_sources

    def perform_search(self, query: str) -> str:
        """Legacy helper returning context string only."""
        ctx, _ = self.perform_web_search(query)
        return ctx

    def generate_response(self, query, chat_history=None, department_id=None, branch_id=None, course_code=None, return_sources=False):
        load_dotenv(override=True)
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        if (not gemini_api_key or gemini_api_key == "your_api_key_here") and (not groq_api_key or groq_api_key == "your_api_key_here"):
            err_msg = "⚠️ **API Keys not configured.** Please add GEMINI_API_KEY or GROQ_API_KEY to `.env`."
            return {"answer": err_msg, "sources": [], "source_type": "error", "corrected_query": query} if return_sources else err_msg

        # 1. Spelling correction & query normalization
        corrected_query = self.correct_spelling(query)
        is_spelling_corrected = corrected_query.strip().lower() != query.strip().lower()
            
        # 2. Vector Semantic Caching (check cache for corrected query)
        from database.redis_manager import check_cache, set_cache, init_redis_index
        from chromadb.utils import embedding_functions
        
        init_redis_index()
        emb_fn = embedding_functions.DefaultEmbeddingFunction()
        query_vector = emb_fn([corrected_query])[0]
        
        if course_code:
            cached_answer = check_cache(query_vector, str(course_code))
            if cached_answer:
                print("🟢 CACHE HIT! Serving from Redis cache.")
                res_str = cached_answer + "\n\n*(Served from AI Cache ⚡)*"
                if is_spelling_corrected:
                    res_str = f"*(🔍 Showing results for: **{corrected_query}** — corrected from: \"{query}\")*\n\n" + res_str
                return {"answer": res_str, "sources": [], "source_type": "cache", "corrected_query": corrected_query} if return_sources else res_str

        # 3. RAG: Fetch from ChromaDB if course_code is provided
        rag_context = ""
        sources_list = []
        has_relevant_docs = False
        MAX_CONTEXT_CHARS = 15000
        
        if department_id and branch_id and course_code:
            search_results = search_documents(corrected_query, department_id, branch_id, course_code, n_results=3)
            docs = search_results.get("documents", [])
            metas = search_results.get("metadatas", [])
            distances = search_results.get("distances", [])
            
            if docs and len(docs) > 0 and len(docs[0]) > 0:
                # In ChromaDB, distance > 1.35 indicates very weak or irrelevant semantic similarity
                top_dist = distances[0][0] if distances and len(distances[0]) > 0 else 0.0
                if top_dist <= 1.35:
                    has_relevant_docs = True
                    rag_context = "Here is relevant context directly from the course syllabus/lecture notes:\n"
                    current_chars = len(rag_context)
                    for i, doc_chunk in enumerate(docs[0]):
                        source_meta = metas[0][i].get("source", f"Lecture Material {i+1}") if metas and len(metas[0]) > i else f"Lecture Material {i+1}"
                        sources_list.append({"source": source_meta, "content": doc_chunk[:250] + ("..." if len(doc_chunk) > 250 else "")})
                        chunk_text = f"--- Source: {source_meta} ---\n{doc_chunk}\n\n"
                        if current_chars + len(chunk_text) > MAX_CONTEXT_CHARS:
                            remaining_space = MAX_CONTEXT_CHARS - current_chars
                            if remaining_space > 100:
                                rag_context += f"--- Source: {source_meta} ---\n{doc_chunk[:remaining_space]}... [TRUNCATED]\n\n"
                            break
                        rag_context += chunk_text
                        current_chars += len(chunk_text)

        # 4. Handle Case: No relevant answer found in uploaded documents -> Fallback to Internet
        source_type = "course_material"
        if not has_relevant_docs:
            source_type = "internet"
            web_context, web_sources = self.perform_web_search(corrected_query)
            sources_list = web_sources
            
            final_query = f"""
SYSTEM INSTRUCTIONS:
1. You are StudyMate's Academic AI Assistant.
2. IMPORTANT NOTICE: The student is asking an academic question, but NO relevant answer was found in the uploaded course documents.
3. You MUST begin your response explicitly with this notice:
"> ℹ️ **Notice:** No relevant answer was found in the uploaded course documents. The following response has been retrieved from verified internet sources:"
4. Based on the internet context below and verified academic knowledge, provide a thorough, structured, and helpful explanation to fully answer the student's question.
5. Provide citations to the internet references at the conclusion of your explanation.

Verified Context from the Web:
{web_context}

User Question: {corrected_query}
"""
        else:
            # Relevant course materials found; check if external web facts are also needed
            search_context = ""
            if self.needs_search(corrected_query):
                search_context, extra_sources = self.perform_web_search(corrected_query)
                sources_list.extend(extra_sources)

            final_query = f"""
{rag_context}
{search_context}

SYSTEM INSTRUCTIONS:
1. Based on the course materials provided above, answer the student's question accurately.
2. If you use information from the context, cite the source (e.g. "According to [Document Name]...").
3. If the course documents do not fully answer the question, state:
"> ℹ️ **Notice:** The uploaded course materials do not fully cover this specific topic. Here is an explanation based on verified academic principles:"

User Question: {corrected_query}
"""

        # 5. Dual-Mesh Generation (Groq / Gemini)
        answer = None
        # Try Groq first for high-speed response
        if groq_api_key and groq_api_key != "your_api_key_here" and Groq:
            try:
                client = Groq(api_key=groq_api_key)
                messages = []
                if chat_history:
                    for msg in chat_history:
                        role = msg["role"]
                        if role == "model": role = "assistant"
                        messages.append({"role": role, "content": msg["content"]})
                messages.append({"role": "user", "content": final_query})
                
                completion = client.chat.completions.create(
                    messages=messages,
                    model=self.fallback_model,
                    temperature=0.2,
                    max_tokens=800
                )
                answer = completion.choices[0].message.content
            except Exception as ge:
                print(f"Groq generation warning: {ge}")

        # Fallback to Gemini
        if not answer and gemini_api_key and gemini_api_key != "your_api_key_here":
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
            except Exception as gme:
                print(f"Gemini generation error: {gme}")

        if not answer:
            err = "❌ Failed to generate response from both Groq and Gemini."
            return {"answer": err, "sources": [], "source_type": "error", "corrected_query": corrected_query} if return_sources else err

        # Prepend spelling auto-correction notice if applicable
        if is_spelling_corrected:
            spelling_banner = f"*(🔍 Showing results for: **{corrected_query}** — corrected from: \"{query}\")*\n\n"
            answer = spelling_banner + answer

        # Cache the result
        if course_code:
            set_cache(query_vector, query, str(course_code), answer)
            
        return {
            "answer": answer, 
            "sources": sources_list, 
            "source_type": source_type, 
            "corrected_query": corrected_query
        } if return_sources else answer
                
    def generate_exam(self, course_code, department_id, branch_id, num_questions=5, difficulty="medium"):
        """
        Generates complex, higher-order multiple choice quiz questions based on course context.
        Supports scenarios, technical debugging, schematics, and visual diagrams.
        """
        load_dotenv(override=True)
        from database.vector_manager import search_documents
        context = search_documents("Key concepts, definitions, core principles, system design, and algorithms", department_id, branch_id, course_code, n_results=4)
        
        if not context or not context.get("documents") or len(context["documents"][0]) == 0:
            return None
            
        formatted_context = ""
        MAX_EXAM_CHARS = 4500
        for chunk in context["documents"][0]:
            if len(formatted_context) + len(chunk) > MAX_EXAM_CHARS:
                formatted_context += chunk[:MAX_EXAM_CHARS - len(formatted_context)] + "..."
                break
            formatted_context += chunk + "\n\n"
            
        prompt = f"""You are an expert university professor designing an advanced examination.
Based on the course context provided, generate {num_questions} challenging, complex multiple-choice questions at a {difficulty} difficulty level.

Guidelines for question complexity:
1. Higher-Order Cognitive Evaluation: Formulate scenario-based problems, output prediction, edge-case analysis, schema evaluation, or architectural trade-offs. Avoid simplistic, 1-line trivial recall.
2. Visual Diagrams & Schematics: For questions that benefit from visual schemas (e.g., table schemas with keys, tree/graph structures, dependency graphs, state machines, or architecture workflows), include:
   - "diagram": A compact 3-5 line clean ASCII / box / tree schematic (e.g. using +, -, |, arrows) illustrating the scenario, or null if not needed.
   - "image_url": A valid web URL to a relevant educational diagram if applicable, or null.
3. Plausible Options: Provide 4 rigorous, thoughtful options (Option A, Option B, Option C, Option D) with plausible distractors targeting common misconceptions.
4. Concise Explanation: Provide a crisp 1-2 sentence explanation strictly under 40 words explaining why the answer is correct. Keep it concise.

Return strictly raw JSON format as an array of objects:
[
  {{
    "question": "Scenario or problem statement...",
    "diagram": "compact 3-5 line ASCII diagram or null",
    "image_url": null,
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": "Option B",
    "explanation": "Crisp 1-2 sentence explanation under 40 words."
  }}
]

Context:
{formatted_context}
"""
        
        groq_api_key = os.getenv("GROQ_API_KEY")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        response_text = None
        
        # 1. High-speed completion using Groq (prioritizing high-OTPM models)
        if groq_api_key and groq_api_key != "your_api_key_here" and Groq:
            for exam_model in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", self.fallback_model]:
                try:
                    client = Groq(api_key=groq_api_key)
                    completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": "You are a university exam generator. Output ONLY a valid JSON array of questions, nothing else."},
                            {"role": "user", "content": prompt}
                        ],
                        model=exam_model,
                        temperature=0.2,
                        max_tokens=1800 if exam_model != "qwen/qwen3.8-27b" else 900
                    )
                    response_text = completion.choices[0].message.content
                    if response_text and len(response_text.strip()) > 20:
                        break
                except Exception as ge:
                    print(f"Groq exam generation warning on {exam_model}: {ge}")
                
        # 2. Fallback to Gemini if Groq is unavailable
        if not response_text and gemini_api_key and gemini_api_key != "your_api_key_here":
            try:
                if genai:
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
        import re
        raw_str = response_text.strip()
        if "```json" in raw_str:
            raw_str = raw_str.split("```json")[1].split("```")[0]
        elif "```" in raw_str:
            raw_str = raw_str.split("```")[1].split("```")[0]
        raw_str = raw_str.strip()

        quiz = None
        # Attempt 1: Direct JSON parse
        try:
            quiz = json.loads(raw_str)
        except Exception:
            pass

        # Attempt 2: Truncation repair by finding last closing brace
        if quiz is None:
            last_brace = raw_str.rfind("}")
            if last_brace != -1:
                try:
                    quiz = json.loads(raw_str[:last_brace + 1] + "]")
                except Exception:
                    pass

        # Attempt 3: Regex extraction of complete question objects
        if quiz is None:
            pattern = re.compile(r'\{\s*"question":.*?"explanation":\s*".*?"\s*\}', re.DOTALL)
            matches = pattern.findall(raw_str)
            recovered = []
            for m in matches:
                try:
                    recovered.append(json.loads(m))
                except Exception:
                    pass
            if recovered:
                quiz = recovered

        if not quiz or not isinstance(quiz, list):
            print(f"Failed to parse exam JSON. Raw response: {response_text[:300]}...")
            return None

        for q in quiz:
            if "explanation" not in q or not q["explanation"]:
                q["explanation"] = f"Correct answer is '{q.get('answer', '')}' based on course materials."
            if "options" not in q or not isinstance(q["options"], list):
                q["options"] = []
            if "diagram" not in q:
                q["diagram"] = None
            if "image_url" not in q:
                q["image_url"] = None
        return quiz
