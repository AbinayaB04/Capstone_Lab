from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database.mongo_manager import verify_login, update_password
import jwt
import os
import datetime

router = APIRouter(prefix="/auth", tags=["auth"])
JWT_SECRET = os.environ.get("JWT_SECRET", "super-secret-capstone-key-2026")

class LoginRequest(BaseModel):
    username: str
    password: str
    role: str = None

def create_jwt(user_data):
    payload = {
        "username": user_data.get("username"),
        "name": user_data.get("name"),
        "role": user_data.get("role"),
        "department_id": str(user_data.get("department_id")) if user_data.get("department_id") else None,
        "branch_id": str(user_data.get("branch_id")) if user_data.get("branch_id") else None,
        "semester": user_data.get("semester"),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=4)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

@router.post("/login")
async def login(request: LoginRequest):
    success, response = verify_login(request.username, request.password)
    if not success:
        raise HTTPException(status_code=401, detail=response)
        
    user_data = response
    if request.role and str(user_data.get("role", "")).lower() != str(request.role).lower():
        raise HTTPException(status_code=403, detail=f"User is not registered as {request.role}. Found {user_data.get('role', 'unknown')}.")
        
    token = create_jwt(user_data)
    
    user_data["_id"] = str(user_data.get("_id", ""))
    for key in ["department_id", "branch_id"]:
        if user_data.get(key):
            user_data[key] = str(user_data[key])
    return {"token": token, "user": user_data}
