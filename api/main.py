from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import auth_routes, document_routes, chat_routes

app = FastAPI(title="StudyMate API", description="Backend API for StudyMate AI")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"], # Restrict to frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(document_routes.router)
app.include_router(chat_routes.router)

@app.get("/")
async def root():
    return {"message": "Welcome to StudyMate API"}
