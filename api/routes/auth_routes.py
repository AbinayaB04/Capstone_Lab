from fastapi import APIRouter, HTTPException, Depends, Request, Header
from pydantic import BaseModel
from database.mongo_manager import verify_login, update_password, log_audit_action
from database.redis_manager import blacklist_token, is_token_blacklisted
from slowapi import Limiter
from slowapi.util import get_remote_address
import jwt
import os
import datetime

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)
JWT_SECRET = os.environ.get("JWT_SECRET", "super-secret-capstone-key-2026")

class LoginRequest(BaseModel):
    username: str
    password: str
    role: str = None

class ForgotPasswordVerifyRequest(BaseModel):
    username: str
    dob: str
    
class ForgotPasswordResetRequest(BaseModel):
    username: str
    dob: str
    new_password: str

def create_jwt(user_data, expires_delta=datetime.timedelta(minutes=15), token_type="access"):
    payload = {
        "username": user_data.get("username"),
        "name": user_data.get("name"),
        "role": user_data.get("role"),
        "department_id": str(user_data.get("department_id")) if user_data.get("department_id") else None,
        "branch_id": str(user_data.get("branch_id")) if user_data.get("branch_id") else None,
        "semester": user_data.get("semester"),
        "type": token_type,
        "exp": datetime.datetime.utcnow() + expires_delta
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, login_req: LoginRequest):
    success, response = verify_login(login_req.username, login_req.password)
    if not success:
        log_audit_action(login_req.username, "FAILED_LOGIN", "system", response)
        raise HTTPException(status_code=401, detail=response)
        
    user_data = response
    if login_req.role and str(user_data.get("role", "")).lower() != str(login_req.role).lower():
        raise HTTPException(status_code=403, detail=f"User is not registered as {login_req.role}. Found {user_data.get('role', 'unknown')}.")
        
    access_token = create_jwt(user_data, expires_delta=datetime.timedelta(minutes=15), token_type="access")
    refresh_token = create_jwt(user_data, expires_delta=datetime.timedelta(days=7), token_type="refresh")
    
    user_data["_id"] = str(user_data.get("_id", ""))
    for key in ["department_id", "branch_id"]:
        if user_data.get(key):
            user_data[key] = str(user_data[key])
            
    log_audit_action(login_req.username, "SUCCESSFUL_LOGIN", "system", "User logged in")
    return {"token": access_token, "refresh_token": refresh_token, "user": user_data}

@router.post("/logout")
async def logout(authorization: str = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], options={"verify_exp": False})
            exp = payload.get("exp")
            if exp:
                expires_in = int(exp - datetime.datetime.utcnow().timestamp())
                if expires_in > 0:
                    blacklist_token(token, expires_in)
                    log_audit_action(payload.get("username", "unknown"), "LOGOUT", "system")
        except jwt.InvalidTokenError:
            pass
    return {"message": "Logged out successfully"}

@router.post("/refresh")
async def refresh_token(request: Request, refresh_token: str = Header(None)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
        
    if is_token_blacklisted(refresh_token):
        raise HTTPException(status_code=401, detail="Token has been revoked")
        
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
            
        new_access_token = create_jwt(payload, expires_delta=datetime.timedelta(minutes=15), token_type="access")
        return {"token": new_access_token}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.post("/forgot-password/verify-dob")
async def verify_dob(req: ForgotPasswordVerifyRequest):
    from database.mongo_manager import verify_dob_for_reset
    if verify_dob_for_reset(req.username, req.dob):
        return {"message": "DOB verified."}
    else:
        raise HTTPException(status_code=400, detail="Invalid Username or Date of Birth.")

@router.post("/forgot-password/reset")
async def reset_forgotten_password(req: ForgotPasswordResetRequest):
    from database.mongo_manager import verify_dob_for_reset, update_password
    if not verify_dob_for_reset(req.username, req.dob):
        raise HTTPException(status_code=400, detail="Invalid Username or Date of Birth.")
        
    if update_password(req.username, req.new_password):
        log_audit_action(req.username, "PASSWORD_RESET", "system", "Password reset via forgot password")
        return {"message": "Password successfully reset."}
    else:
        raise HTTPException(status_code=400, detail="Could not reset password. Ensure it's not a recently used password.")
