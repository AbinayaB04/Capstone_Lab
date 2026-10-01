# 📚 StudyMate: Comprehensive Project Documentation

This document outlines the complete feature set, technical architecture, models, databases, and third-party libraries used to build the StudyMate application from start to finish.

---

## 🌟 1. Core Application Features

StudyMate is a multi-tenant, AI-powered learning management system designed to securely deliver context-aware education. 

### 🔐 Multi-Tenant & Role-Based Access Control (RBAC)
- **Hierarchical Isolation:** Data and context are strictly organized by `Department -> Branch -> Semester -> Course`. A Computer Science student cannot accidentally access Mechanical Engineering materials.
- **Three-Tier Portals:** Distinct, customized dashboards for **Students** (Learning & Exams), **Staff** (Content Uploads), and **Admins** (User Management & Analytics).
- **Secure Authentication:** All passwords are cryptographically hashed using `bcrypt`. Students can securely manage their settings, while Admins handle initial onboarding.

### 🤖 Intelligent AI Capabilities
- **RAG-Powered Tutor (Retrieval-Augmented Generation):** When a student asks a question, the system searches through their specific course materials (PDFs/PPTs) and forces the AI to answer *only* based on the professor's syllabus.
- **AI Practice Exams:** The system can autonomously read the textbook context and generate an interactive 5-question multiple-choice quiz on demand, complete with instant grading and corrections.
- **Live Web Fallback:** If a student asks a question outside the scope of the uploaded syllabus, the AI autonomously recognizes this, browses the live internet (via DuckDuckGo), and returns a real-time answer.
- **Dual-Mesh Reliability:** The AI engine uses a highly resilient architecture. If the primary AI (Gemini) crashes or is overloaded, the system instantly hot-swaps to the backup AI (Llama-3) so the student is never left hanging.
- **Persistent Chat History:** Similar to ChatGPT, all conversations are saved as sessions in the sidebar. Students can revisit older chats and resume studying exactly where they left off.

### 📊 System Administration & Analytics
- **Document Management:** Staff can seamlessly upload course materials. The system securely stores the raw files for later downloading, while simultaneously extracting the text for the AI.
- **Live Analytics Dashboard:** Admins have access to a real-time dashboard that parses raw system logs into interactive Pandas data charts, tracking login counts, document access, and system events.

---

## 🖥️ 2. Core Application Framework
**Streamlit** powers the entire frontend and backend event loop of the application. It allows for rapid prototyping of data-driven dashboards and AI chatbots in pure Python.
- `streamlit`: The core framework for rendering UI components, handling state (`st.session_state`), and managing multi-page logic.
- `streamlit-option-menu`: Used to build the custom, stylised sidebar navigation menus across the Student, Staff, and Admin portals.
- `streamlit-lottie`: Used to render lightweight, scalable JSON animations (like the welcome animation on the login screen).

---

## 🗄️ 3. Database Architecture
StudyMate uses a hybrid database architecture, combining a NoSQL document store for application state with a Vector database for semantic AI searches.

### MongoDB (Primary Database)
Handled via the `pymongo` library. MongoDB is used for persistent, structured data storage.
- **Collections:** Stores data for `users`, `departments`, `branches`, `courses`, and `chat_sessions`.
- **GridFS:** A specialized MongoDB specification used to securely store and chunk large raw binary files (like the original uploaded PDFs and PPTXs) so they can be downloaded later.
- **Purpose:** Handles Role-Based Access Control (RBAC), multi-tenant mappings, persistent chat history, and audit logging.

### ChromaDB (Vector Database)
Handled via the `chromadb` library. ChromaDB is a local, persistent vector store.
- **Purpose:** Powers the RAG (Retrieval-Augmented Generation) pipeline.
- **Process:** When documents are uploaded, their text is split into chunks, converted into mathematical vectors (embeddings), and stored here alongside metadata (course code, branch ID). During a search, it retrieves the chunks mathematically closest to the user's query.

---

## 🧠 4. Artificial Intelligence & Machine Learning Models
StudyMate employs a highly resilient "Dual-Mesh" AI architecture, leveraging both Google and Meta models to ensure high availability and diverse capabilities.

### Gemini 3.6 Flash (Primary Engine)
- **Provider:** Google (via `google-genai` SDK)
- **Role:** The main "brain" of the application. It handles contextual student Q&A, reads textbook contexts from ChromaDB to answer accurately, and acts as the "expert professor" to autonomously generate JSON-structured Practice Exams.

### Llama-3.3-70b-versatile (Fallback & Routing Engine)
- **Provider:** Meta (via `groq` API)
- **Role 1 (Failover):** If the Gemini API is rate-limited or fails, the system automatically redirects the query to Groq's high-speed inference engine running Llama-3 to ensure the user always gets an answer.
- **Role 2 (Router):** Used as a lightning-fast router to analyze a user's prompt and determine if it requires live internet access.

### all-MiniLM-L6-v2 (Embedding Model)
- **Provider:** SentenceTransformers (bundled within ChromaDB by default)
- **Role:** The natural language processing model that converts raw extracted text from PDFs/PPTXs into high-dimensional vector embeddings, allowing the system to "understand" semantic similarity.

---

## 🛠️ 5. Utilities & Supporting Libraries

### Security & Authentication
- `bcrypt`: The industry standard for cryptographic password hashing. It salts and hashes user passwords before storing them in MongoDB, ensuring that raw passwords are never exposed.

### Document Processing (Ingestion)
- `PyMuPDF` (imported as `pymupdf`): A high-performance library used to parse, read, and extract text from uploaded `.pdf` files.
- `python-pptx`: Used to iterate through slides and extract textual content from uploaded `.pptx` presentations.

### Real-Time Internet Search
- `duckduckgo-search`: A lightweight, unofficial API wrapper that allows the LLM engine to perform live web searches and scrape search results when a student asks a question outside the scope of their uploaded syllabus.

### Data Manipulation & Analytics
- `pandas`: Used within the Admin portal to parse local audit logs (`audit.log`) into DataFrames. This allows for quick, in-memory filtering and aggregations to render the interactive system metric charts.

### Configuration
- `python-dotenv`: Loads environment variables from the local `.env` file (like `MONGO_URI`, `GEMINI_API_KEY`, `GROQ_API_KEY`) into the application environment securely without hardcoding secrets in the source code.
