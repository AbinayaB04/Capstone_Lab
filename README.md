# StudyMate - AI-Powered Education Platform

StudyMate is an advanced, AI-driven educational platform designed for students and staff. It features a microservice architecture with a FastAPI backend, a Streamlit frontend, and robust integrations with MongoDB, Redis, and ChromaDB for Retrieval-Augmented Generation (RAG) capabilities.

## Features
- **Role-Based Access Control (RBAC) & Separation of Duties**: 
  - Fine-grained permission matrix across Super Admins, Department Admins, Staff, and Students.
- **Enterprise IAM Lifecycle Governance (JMLM Model)**:
  - **Joiner Phase**: Secure user onboarding with branch assignment, initial semester, and enrollment date tracking.
  - **Mover Phase (Automated Time-Based Progression)**: Just-In-Time (JIT) 6-month term progression calculated on login; admin override controls and Academic Hold flags to freeze auto-promotion for medical leave or term repeats.
  - **Maintainer Phase**: 90-day password rotation, password history tracking (last 3 hashes), 2FA/TOTP authenticator app support with single-use recovery codes, and brute-force lockout after 5 failed attempts.
  - **Leaver Phase (Soft-Deprovisioning & Session Killswitch)**: Instant Redis-backed JWT session revocation upon account suspension; automated transition to Alumni status upon graduation (> Semester 8).
- **Academic Semester Isolation & Zero-Trust Boundary**:
  - Students are strictly restricted to querying, accessing, and downloading course documents in their actively enrolled semester.
  - Cross-semester queries, exam generation, and material downloads are blocked at both backend API (`HTTP 403 Forbidden`) and frontend UI levels.
- **Hardened Document Ingestion & Upload Security**:
  - Cryptographic identity extraction from JWT claims (anti-spoofing).
  - Multi-tenant department isolation enforcing that staff only upload within their assigned department.
  - Directory traversal defense (`os.path.basename` path sanitization).
  - Strict extension whitelisting (`.pdf` and `.pptx` only).
  - Magic byte binary signature verification (`%PDF-` and `PK\x03\x04`) preventing extension masquerading.
  - 50 MB file size limit and memory exhaustion protection.
  - Immutable audit logging in MongoDB for compliance tracking.
- **Dual-Mesh AI Engine & Transparent RAG**:
  - Conversational tutoring powered by Google Gemini with automated fallback to Groq (Llama-3 / Qwen) for resilience.
  - Typo correction and query normalization (`correct_spelling`).
  - Corrective RAG (CRAG) with multi-source internet search fallback (DuckDuckGo + Wikipedia).
  - Transparent syllabus citations with expandable source excerpts.
  - Vector semantic caching via Redis vector search (`RediSearch` cosine indexing).
- **AI Practice Exams & Analytics**:
  - Dynamic multiple-choice exam generation with difficulty levels and technical dependency/schema diagrams.
  - Instant grading with comprehensive concept explanations.
  - Persistent exam history with performance tracking line charts.
- **Curriculum & Document Management**:
  - Administrative CRUD controls for Departments, Branches, and Courses.
  - GridFS document storage and ChromaDB vector chunk synchronization.
- **Automated Test Suite**:
  - Comprehensive `pytest` test suites validating all IAM lifecycle phases, semester isolation, upload defenses, RBAC permissions, and quiz engine flows.


## Tech Stack
- **Frontend**: Streamlit
- **Backend**: FastAPI (Python)
- **Database**: MongoDB Atlas (Cloud)
- **Vector Store**: ChromaDB (Local SQLite)
- **Caching & Background Tasks**: Redis Stack (Dockerized)
- **Containerization**: Docker & Docker Compose

---

## How to Setup the Environment

### 1. Prerequisites
Ensure you have the following installed on your machine:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Running)
- [Git](https://git-scm.com/)

### 2. Configure Environment Variables
The repository contains an example environment file. You must create your own `.env` file before running the application.

1. Locate `.env.example` in the root directory.
2. Copy it and rename the copy to `.env`.
3. Open `.env` and fill in your actual API keys and database credentials:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   MONGO_URI="mongodb+srv://<username>:<password>@cluster0.example.mongodb.net/..."
   GROQ_API_KEY=your_groq_api_key
   API_BASE_URL=http://backend:8000
   JWT_SECRET=your_secure_random_string
   ```

---

## How to Run the Application

Because the application is fully Dockerized, starting the entire stack (Frontend, Backend, and Redis) is simple.

1. Open a terminal in the root directory of the project.
2. Run the following command:
   ```bash
   docker compose up --build
   ```
3. Wait for the containers to build and spin up.
4. **Access the Application**:
   - **Frontend UI**: [http://localhost:8501](http://localhost:8501)
   - **Backend API Docs (Swagger)**: [http://localhost:8002/docs](http://localhost:8002/docs)

*Note: Since hot-reloading is enabled via Docker volumes, any changes you make to the `.py` files locally will instantly reflect in the app upon browser refresh!*

---

## How to Update the Application

If changes are made to the dependencies (e.g., modifying `requirements.txt`) or `Dockerfile`s, you must rebuild the containers:

1. Stop the currently running containers by pressing `Ctrl+C` in the terminal, or run:
   ```bash
   docker compose down
   ```
2. Pull the latest code from GitHub:
   ```bash
   git pull origin main
   ```
3. Rebuild and start the containers:
   ```bash
   docker compose up --build
   ```

For standard Python code updates (`app.py`, `views/`, `api/`, etc.), **no rebuild is required**. Just refresh your browser!

---

## Running Automated Tests

To verify the test suite:
```bash
pytest tests
```
This runs 25 automated tests across 6 suites covering:
- **5-Phase IAM Lifecycle (JMLC)** (Joiner, Active, Maintainer, Mover, Leaver)
- **Role-Based Access Control (RBAC)** permissions
- **Password Complexity, History & Expiration** validation
- **JWT Authentication & Lifecycle**
- **Two-Factor Authentication (2FA / TOTP) & Recovery Codes**
- **Curriculum Management CRUD** (Departments, Branches, Courses)
- **Exam Generation, Diagrams & Scoring**
- **Search Typo Auto-Correction & Internet Fallback Citations**

---

## 🔑 Pre-Seeded Demo Credentials

For academic evaluation and quick testing, the database includes pre-configured personas:

| Persona | Username / Rollno | Password | Role / Access Scope | Key Demonstration Features |
| :--- | :--- | :--- | :--- | :--- |
| **Super Admin** | `admin` | `pass` | `admin` (Global Scope) | IAM Governance, Academic Holds, User Unlock, Curriculum CRUD |
| **Faculty / Staff** | `staff1` | `pass` | `staff` (CS Department) | Lecture Note Upload (PDF/PPTX), Vector Sync, Knowledge Base |
| **Student (CSE)** | `test` | `1234` | `student` (Sem 5, CSE) | Transparent RAG Chat, Course Material Downloads |
| **Student (Cyber)** | `22PC17` | `Password@123` *(or reset)* | `student` (MSc Cyber Security) | AI Practice Exams with ASCII Diagrams, 6-Month Auto-Promotion |

---

## 📚 Capstone Academic Deliverables

* 📖 **[Comprehensive Capstone Project Report](CAPSTONE_FINAL_REPORT.md)**: Full academic whitepaper with architecture diagrams, threat models, RAG/IAM module specifications, and latency benchmarks.
* 🎯 **[Live Viva & Demonstration Defense Guide](VIVA_DEMO_GUIDE.md)**: Step-by-step 5-minute evaluation walkthrough script with anticipated examiner Q&A.