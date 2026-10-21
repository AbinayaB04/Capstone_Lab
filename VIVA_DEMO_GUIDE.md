# StudyMate AI: Live Demonstration Script & Viva Defense Guide
## Examiner Evaluation & Oral Presentation Manual

**Target Audience:** Capstone Review Board, Faculty Examiners, and External Evaluators  
**Estimated Demo Duration:** 5 to 7 Minutes  
**Companion Documents:** [README.md](README.md) | [CAPSTONE_FINAL_REPORT.md](CAPSTONE_FINAL_REPORT.md)

---

## 1. Evaluation Rubric & Feature Mapping

Use this quick-reference table to map evaluator scoring categories to working features in the codebase:

| Evaluation Criterion | Implementation Details | Code Evidence & Files |
| :--- | :--- | :--- |
| **System Architecture & Design** | Microservice architecture separating Streamlit UI from FastAPI gateway, MongoDB operational store, ChromaDB vector store, and Redis security broker. | • [docker-compose.yml](docker-compose.yml)<br>• [api/main.py](api/main.py)<br>• [app.py](app.py) |
| **Identity & Access Management (IAM)** | Full 5-Phase JMLC lifecycle (Joiner, Active, Maintainer, Mover, Leaver) with 90-day password expiry, 5-attempt lockout, and time-based progression. | • [database/mongo_manager.py](database/mongo_manager.py)<br>• [tests/test_iam_lifecycle.py](tests/test_iam_lifecycle.py) |
| **Authentication & 2FA** | Salted Bcrypt hashing, RFC 6238 TOTP 2FA, 8 single-use SHA-256 backup recovery codes, dual-token JWTs (15m/7d). | • [api/routes/auth_routes.py](api/routes/auth_routes.py)<br>• [auth/session_manager.py](auth/session_manager.py) |
| **Multi-Tenancy & Authorization (RBAC)** | 4-tier RBAC matrix (`admin`, `department_admin`, `staff`, `student`). Strict tenant boundary enforcement blocking cross-department/branch access. | • [auth/rbac_manager.py](auth/rbac_manager.py)<br>• [api/dependencies.py](api/dependencies.py) |
| **Information Retrieval & RAG** | Dense vector search (ChromaDB + MiniLM-L6) with transparent page-level citations. Semantic caching in Redis (<10ms). | • [database/vector_manager.py](database/vector_manager.py)<br>• [services/llm_service.py](services/llm_service.py) |
| **Advanced LLM Engineering** | Typo/spelling auto-correction (Groq 27B) + Multi-source web search fallback (DuckDuckGo + Wikipedia) + Dual-Mesh LLM orchestrator. | • [services/llm_service.py](services/llm_service.py)<br>• [tests/test_search_and_quiz_advanced.py](tests/test_search_and_quiz_advanced.py) |
| **Complex Practice Exams** | Bloom's taxonomy scenario questions with ASCII architecture schemas, plausible distractors, and concept rationales in ~3.5s. | • [services/llm_service.py](services/llm_service.py)<br>• [views/student_view.py](views/student_view.py) |
| **Testing & Quality Assurance** | 25 automated unit and integration tests covering all critical paths with 100% pass rate. | • [tests/](tests/) (`pytest tests`) |

---

## 2. 5-Minute Live Demonstration Walkthrough Script

Follow this sequence step-by-step for a seamless live presentation to examiners:

### Step 1: Administrator IAM Governance (1.5 Minutes)
1. **Navigate to:** `http://localhost:8501`
2. **Select Role:** `Admin`
3. **Login with:** Username: `admin` | Password: `pass`
4. **Showcase Actions:**
   * Go to **Curriculum Management**: Show multi-tenant hierarchy (*School of CS ➔ MSc Cyber Security ➔ 20XC34: DATABASE DESIGN*).
   * Go to **User Management ➔ IAM Lifecycle Actions**:
     * Select user `22PC17` (Student in Cyber Security).
     * Show **Academic Hold Status**: Demonstrate toggling `Academic Hold` to freeze/unfreeze automated semester progression.
     * Show **Account Security Overrides**: Point out the `Unlock Account` (clears 5-attempt brute-force lockout) and `Force Password Reset` controls.

### Step 2: Faculty Syllabus Management & Vector Sync (1 Minute)
1. **Click Logout** in top-right.
2. **Select Role:** `Staff`
3. **Login with:** Staff ID: `staff1` | Password: `pass`
4. **Showcase Actions:**
   * Notice department context: Automatically restricted to *School of Computer Science & Engineering*.
   * Select Course: `20XC34: DATABASE DESIGN`.
   * Explain: Uploaded PDF/PPTX materials are asynchronously sliced into 500-character chunks with 50-character overlap, stored in MongoDB GridFS, and vectorized into ChromaDB.
   * Point out the **Manage Existing Documents** section where documents can be purged with automatic vector cleanup.

### Step 3: Student RAG Chat with Typo Correction (1.5 Minutes)
1. **Click Logout**.
2. **Select Role:** `Student`
3. **Login with:** Rollno: `test` | Password: `1234` (or `22PC17` / reset)
4. **Showcase Actions:**
   * Select Course: `20XC34: DATABASE DESIGN`.
   * **Test Typo Query:** Type in the chat box:
     ```text
     give me an exaple sql query
     ```
   * **Highlight to Examiners:**
     * The auto-correction banner: `(🔍 Showing results for: give me an example sql query — corrected from: "give me an exaple sql query")`.
     * The structured SQL answer generated using syllabus context.
     * Click open **"📚 Verified Course Syllabus References"** to display the exact lecture slide excerpts and page references (e.g., Page 70 / Page 340).

### Step 4: Out-of-Syllabus Internet Fallback (1 Minute)
1. **In the same Student chat**, ask a query that does **not** exist in the uploaded database course notes:
   ```text
   What is quantum key distribution and BB84 protocol?
   ```
2. **Highlight to Examiners:**
   * ChromaDB relevance gate detects high cosine distance (> 1.35).
   * The assistant prepends the verified warning:
     `> ℹ️ Notice: No relevant answer was found in the uploaded course documents. The following response has been retrieved from verified internet sources:`
   * Click open **"🌐 Verified Internet / External Sources"** to show real-time citations from Wikipedia and DuckDuckGo with clickable URLs.

### Step 5: AI Practice Exams with ASCII Diagrams (1.5 Minutes)
1. **Navigate to:** Left sidebar ➔ **Practice Exams**.
2. **Configure Quiz:**
   * Course: `20XC34: DATABASE DESIGN`
   * Difficulty: `Medium`
   * Number of Questions: `5`
   * Click **Generate Quiz**.
3. **Highlight to Examiners:**
   * Watch the generation complete in **~3.5 seconds** using Groq `openai/gpt-oss-120b`.
   * Show question complexity: Higher-order scenario evaluation rather than trivial recall.
   * Show the **ASCII architecture diagrams** embedded in the questions (rendered with high-contrast code blocks).
   * Select answers and click **Submit Exam**:
     * Instant scoring percentage.
     * Detailed concept explanations dissecting both correct answers and distractors.
   * Click open **"📊 View Past Quiz Attempts & Score Analytics"** to display the longitudinal score progression chart.

### Step 6: Security Defense & Concurrent Session Killswitch (1 Minute)
1. **Demonstrate Concurrent Session Revocation:**
   * Open an Incognito window and log into the student account.
   * Return to the first window and perform an action: The previous session token has been automatically revoked in Redis (`active_session` collision).
2. **Demonstrate 5-Attempt Lockout:**
   * Intentionally fail login 5 times with a wrong password. Show the account lock notice (`Account locked out due to too many failed attempts. Contact admin.`).

---

## 3. Anticipated Viva Defense Q&A

Review these 10 high-probability examiner questions and model technical answers:

### Q1: What makes your RAG system transparent compared to standard ChatGPT wrappers?
> **Model Answer:** Standard LLM chat lacks verifiability and hallucinates without institutional context. StudyMate implements transparent, deterministic retrieval:
> 1. ChromaDB retrieves top-k semantic chunks from faculty-uploaded syllabi using `all-MiniLM-L6-v2`.
> 2. Chunks retain metadata (filename, page number, chunk index).
> 3. The UI presents exact excerpts in an expandable citations drawer so students and professors can verify answers against approved course notes.

### Q2: How do you prevent a student in Cyber Security from querying or generating exams for Computer Science materials?
> **Model Answer:** We enforce multi-tenant boundary isolation at the API gateway via `enforce_tenant_isolation()` in `api/dependencies.py`.
> The student's JWT cryptographically embeds their `department_id` and `branch_id`. Any request attempting to access another branch's course materials is rejected with HTTP 403 before any vector query or LLM invocation occurs.

### Q3: How is the IAM Lifecycle (JMLC) implemented beyond simple CRUD?
> **Model Answer:** We implement the complete 5 phases defined by NIST SP 800-63B:
> * **Joiner:** Onboarding with tenant scoping, Bcrypt hash, and 2FA recovery backup codes.
> * **Active:** Dual-token JWTs (15m/7d), RBAC matrix, and single concurrent device enforcement.
> * **Maintainer:** 90-day password expiration, 5-attempt brute-force lockout, and password history tracking.
> * **Mover:** Automated semester calculation based on 182.5-day elapsed periods with Just-In-Time (JIT) auto-promotion upon login, and Academic Hold controls.
> * **Leaver:** Automatic transition to `alumni` status after semester 8, and a real-time Redis token blacklist killswitch upon suspension.

### Q4: If JWTs are stateless, how does your session killswitch instantly log out or suspend users?
> **Model Answer:** Pure stateless JWTs cannot be revoked before expiration. We solve this using **Redis Token Blacklisting**:
> When a user logs out or is suspended by an admin, `revoke_user_sessions()` calculates the remaining token TTL and stores the token in Redis under `blacklist:<token>`.
> The FastAPI dependency `get_current_user` checks Redis in <1ms before decoding the token. If blacklisted, it rejects the request with HTTP 401. If Redis is temporarily down, a circuit breaker gracefully falls back to cryptographic signature verification.

### Q5: How did you fix the practice exam generation timeout?
> **Model Answer:** Initially, generating 5 complex questions exceeded Groq's 1,000 output tokens per minute (OTPM) rate limit on `qwen3.8-27b`, truncating the output and falling through to an unoptimized Gemini transport that timed out after 60 seconds.
> We re-engineered the engine into a high-throughput multi-model mesh:
> 1. Prioritizes Groq `openai/gpt-oss-120b` (2,000 output token buffer).
> 2. Standardized prompt instructions to concise rationales (<40 words) and compact 3–5 line ASCII schemas.
> 3. Implemented a resilient multi-stage JSON parser with regex truncation recovery.
> This reduced generation latency from >60 seconds to **3.54 seconds**.

### Q6: How does the system handle queries when course documents do not contain the answer?
> **Model Answer:** We implement a **Relevance Gate**:
> If ChromaDB returns 0 chunks or the closest cosine distance exceeds `1.35`, the engine flags the query as out-of-syllabus. It triggers an autonomous fallback using DuckDuckGo Instant Answers and Wikipedia REST summaries, formats the context, and instructs the LLM to prepend a clear disclaimer while providing clickable external web citations.

### Q7: Why did you choose ChromaDB over storing embeddings in MongoDB?
> **Model Answer:** ChromaDB operates as a lightweight, dedicated vector database with native HNSW (Hierarchical Navigable Small World) indexing for fast nearest-neighbor lookups. Keeping vector similarity separate from MongoDB Atlas reduces cloud operational costs and network latency, while MongoDB remains optimized for ACID relational documents and audit logs.

### Q8: How do you handle typos in technical queries?
> **Model Answer:** We use a high-speed Groq model (`qwen/qwen3.8-27b`) with temperature 0.0 to normalize the query before vector search in ~200ms. If spelling errors like `"b-tre indexx"` are detected, the system searches using `"B-tree index"` and displays a notification banner to the student.

### Q9: What security measures protect the Two-Factor Authentication (2FA) mechanism?
> **Model Answer:**
> 1. Complies with RFC 6238 TOTP using time-synchronized 30-second rotating codes.
> 2. Provides 8 single-use backup recovery codes.
> 3. To prevent database compromise of recovery codes, backup codes are stored as **SHA-256 hashes** in MongoDB and atomically consumed upon use.

### Q10: What are the key performance bottlenecks you identified and resolved?
> **Model Answer:**
> 1. **Windows IPv6 Loopback Delay:** Internal calls to `localhost` suffered a 2.0-second delay waiting for `::1` IPv6 socket timeouts. Replaced with `127.0.0.1` (reduced latency to 4ms).
> 2. **Redis Unavailability Latency:** Sequential connection timeouts across 5 functions delayed login by 25 seconds when Redis was offline. Added `is_redis_available()` with a 30s cache and 50ms connect timeout (reduced login to 0.37s).

---

## 4. Emergency Troubleshooting Cheat Sheet (During Demo)

If anything unexpected occurs during evaluation:

| Symptom | Cause | One-Line Fix |
| :--- | :--- | :--- |
| **Login says "Could not connect to API server"** | FastAPI backend stopped or port busy. | Run in terminal: `python -m uvicorn api.main:app --port 8002 --reload` |
| **Student says "Account locked out"** | 5 failed attempts triggered brute-force defense. | Log in as `admin`, go to **IAM Lifecycle Actions ➔ Unlock Account** for that user. |
| **Exam says "Documents not uploaded"** | Course has no syllabus chunks in ChromaDB. | Ensure course `20XC34` is selected (contains pre-seeded syllabus documents). |
| **Browser shows old UI state** | Streamlit caching session variables. | Press `Ctrl + Shift + R` (hard refresh) or click **Logout** in top-right. |
