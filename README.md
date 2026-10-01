# StudyMate - AI-Powered Education Platform

StudyMate is an advanced, AI-driven educational platform designed for students and staff. It features a microservice architecture with a FastAPI backend, a Streamlit frontend, and robust integrations with MongoDB, Redis, and ChromaDB for Retrieval-Augmented Generation (RAG) capabilities.

## 🚀 Features
- **Role-Based Access Control (RBAC)**: Secure separation between Admins, Staff, and Students.
- **Enterprise IAM**: Strict password complexity, auto-account lockouts after failed attempts, and Admin override controls (Unlock Account / Force Password Reset).
- **AI Query Engine**: Chat with course materials powered by Google Gemini / Groq and ChromaDB.
- **Chat Management**: Persistent chat sessions that can be renamed and deleted.
- **Background Task Processing**: Asynchronous PDF parsing, chunking, and vector embedding generation.
- **Hot-Reloading Environment**: Docker volume mounts allow instant UI and API updates without container rebuilds.

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