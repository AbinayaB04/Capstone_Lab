from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from services.llm_service import AIEngine
from database.mongo_manager import create_chat_session, get_chat_sessions_by_user, get_chat_session, add_message_to_session, update_chat_session_title, delete_chat_session

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize a global AI engine instance for the API
ai_engine = AIEngine()

class QueryRequest(BaseModel):
    query: str
    department_id: Optional[str] = None
    branch_id: Optional[str] = None
    course_code: Optional[str] = None
    chat_history: List[Dict[str, str]] = []
    session_id: Optional[str] = None
    username: Optional[str] = None

class ExamRequest(BaseModel):
    course_code: str
    department_id: str
    branch_id: str
    num_questions: int = 5
    difficulty: str = "medium"

class SessionCreateRequest(BaseModel):
    username: str
    course_code: str
    branch_id: str
    semester: int
    title: str

class SessionRenameRequest(BaseModel):
    title: str

class QuizSubmitRequest(BaseModel):
    username: str
    course_code: str
    branch_id: Optional[str] = None
    semester: Optional[int] = None
    score: int
    total_questions: int
    difficulty: str = "medium"
    user_answers: Dict[str, Any] = {}
    quiz_details: List[Dict[str, Any]] = []

@router.post("/query")
async def generate_query_response(request: QueryRequest):
    try:
        res = ai_engine.generate_response(
            query=request.query,
            department_id=request.department_id,
            branch_id=request.branch_id,
            course_code=request.course_code,
            chat_history=request.chat_history,
            return_sources=True
        )
        if isinstance(res, dict):
            response = res["answer"]
            sources = res["sources"]
        else:
            response = res
            sources = []
        
        if request.session_id and request.username:
            add_message_to_session(request.session_id, "user", request.query)
            add_message_to_session(request.session_id, "assistant", response)
            
        return {"response": response, "sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quiz/submit")
async def submit_quiz(request: QuizSubmitRequest):
    from database.mongo_manager import record_quiz_attempt
    attempt_id = record_quiz_attempt(
        username=request.username,
        course_code=request.course_code,
        branch_id=request.branch_id,
        semester=request.semester,
        score=request.score,
        total_questions=request.total_questions,
        difficulty=request.difficulty,
        user_answers=request.user_answers,
        quiz_details=request.quiz_details
    )
    return {"status": "success", "attempt_id": attempt_id}

@router.get("/quiz/history/{username}")
async def get_quiz_history(username: str, course_code: Optional[str] = None):
    from database.mongo_manager import get_quiz_attempts_by_user
    attempts = get_quiz_attempts_by_user(username, course_code)
    for a in attempts:
        a["_id"] = str(a["_id"])
        if "timestamp" in a and a["timestamp"]:
            a["timestamp"] = a["timestamp"].isoformat()
    return {"attempts": attempts}


@router.post("/generate-exam")
async def generate_exam(request: ExamRequest):
    try:
        exam_json = ai_engine.generate_exam(
            course_code=request.course_code,
            department_id=request.department_id,
            branch_id=request.branch_id,
            num_questions=request.num_questions,
            difficulty=request.difficulty
        )
        return {"exam": exam_json}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.post("/sessions")
async def create_session(request: SessionCreateRequest):
    session_id = create_chat_session(
        request.username, 
        request.course_code, 
        request.branch_id, 
        request.semester, 
        request.title
    )
    return {"session_id": session_id}

@router.get("/sessions/{username}")
async def get_user_sessions(username: str, course_code: Optional[str] = None):
    sessions = get_chat_sessions_by_user(username, course_code)
    for s in sessions:
        s["_id"] = str(s["_id"])
    return {"sessions": sessions}

@router.put("/sessions/{session_id}")
async def rename_session(session_id: str, request: SessionRenameRequest):
    try:
        update_chat_session_title(session_id, request.title)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    try:
        delete_chat_session(session_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
