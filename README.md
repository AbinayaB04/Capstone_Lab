# StudyMate - AI-Powered Education Platform

StudyMate is an advanced, AI-driven educational platform designed for students and staff. It features a microservice architecture with a FastAPI backend, a Streamlit frontend, and robust integrations with MongoDB, Redis, and ChromaDB for Retrieval-Augmented Generation (RAG) capabilities.

## 🚀 Features
- **Role-Based Access Control (RBAC)**: Secure separation between Admins, Staff, and Students.
- **Enterprise IAM & Security**:
  - Two-Factor Authentication (2FA / TOTP) compatible with Google Authenticator and Microsoft Authenticator.
  - Strict password complexity, password reuse prevention, and 90-day expiration policy.
  - Auto-account lockout after 5 failed attempts and Admin override controls (Unlock Account / Force Password Reset).
  - Date of Birth (DOB) verification for password self-recovery.
- **AI Query Engine & Transparent RAG**:
  - Chat with course materials powered by Google Gemini and Groq (Llama-3) fallback.
  - Transparent citations: Expandable "Verified Course Syllabus References" showing exact lecture excerpts and page chunks.
  - Semantic caching via Redis vector search to save API tokens.
- **AI Practice Exams & Student Analytics**:
  - Custom exam generation by Difficulty (*Easy*, *Medium*, *Hard*) and Question Count (*3*, *5*, *10*).
  - Instant grading with detailed **Explanations & Concept Rationales** for each question.
  - Persistent exam history in MongoDB with score progression line charts.
- **Course & Curriculum Management (Admin Portal)**:
  - Full UI controls to create Departments, Branches, and Semester Courses without direct database manipulation.
- **Document Management & Vector Synchronization**:
  - Support for `.pdf` and `.pptx` documents.
  - Automatic document deletion purging raw files from GridFS and corresponding vector chunks from ChromaDB.
- **Automated Test Suite**:
  - Built-in `pytest` coverage for RBAC, authentication, JWT tokens, TOTP verification, curriculum CRUD, and exam scoring.


## 🛠️ Tech Stack
- **Frontend**: Streamlit
- **Backend**: FastAPI (Python)
- **Database**: MongoDB Atlas (Cloud)
- **Vector Store**: ChromaDB (Local SQLite)
- **Caching & Background Tasks**: Redis Stack (Dockerized)
- **Containerization**: Docker & Docker Compose

---

## ⚙️ How to Setup the Environment

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

## ▶️ How to Run the Application

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

## 🔄 How to Update the Application

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

## 🧪 Running Automated Tests

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