from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from api.routes import auth_routes, document_routes, chat_routes

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="StudyMate API", description="Backend API for StudyMate AI")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
