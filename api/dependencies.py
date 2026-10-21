import os
import jwt
from fastapi import Header, HTTPException, Depends
from typing import Optional, Callable
from auth.rbac_manager import RBACManager
from database.redis_manager import is_token_blacklisted

JWT_SECRET = os.environ.get("JWT_SECRET", "super-secret-capstone-key-2026")

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Extracts and cryptographically validates the JWT Bearer token.
    Verifies that the token has not been revoked (via Redis blacklist).
    """
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Missing Authorization header. Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401, 
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    token = parts[1]
    
    # Check if token is blacklisted in Redis
    try:
        if is_token_blacklisted(token):
            raise HTTPException(
                status_code=401, 
                detail="Session token has been revoked / logged out.",
                headers={"WWW-Authenticate": "Bearer"}
            )
    except Exception as e:
        # If Redis is temporarily down, log warning and continue JWT verification
        print(f"Warning: Redis blacklist check failed: {e}")

    # Decode and verify JWT
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, 
            detail="Session token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401, 
            detail="Invalid session token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

def require_permission(permission: str) -> Callable:
    """
    FastAPI dependency factory enforcing granular RBAC permissions.
    """
    def permission_checker(current_user: dict = Depends(get_current_user)) -> dict:
        role = current_user.get("role", "")
        if not RBACManager.has_permission(role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden: Role '{role}' lacks '{permission}' permission."
            )
        return current_user
    return permission_checker

def require_role(allowed_roles: list) -> Callable:
    """
    FastAPI dependency factory restricting access to specific roles.
    """
    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        role = str(current_user.get("role", "")).lower()
        if role not in [r.lower() for r in allowed_roles]:
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden: Required one of roles {allowed_roles}, got '{role}'."
            )
        return current_user
    return role_checker

def enforce_tenant_isolation(
    user: dict, 
    requested_dept_id: Optional[str] = None, 
    requested_branch_id: Optional[str] = None,
    requested_course_code: Optional[str] = None,
    requested_semester: Optional[int] = None
) -> bool:
    """
    Validates that a user is not performing a cross-tenant or cross-semester privilege escalation.
    - Admin: Global access across all departments, branches, courses, and semesters.
    - Staff / Dept Admin: Scoped to their own department.
    - Student: Strictly scoped to their own department, branch, and enrolled semester.
               Students CANNOT access or query materials/courses from other semesters.
    """
    role = str(user.get("role", "")).lower()
    
    if role == "admin":
        return True
        
    user_dept = str(user.get("department_id") or "")
    user_branch = str(user.get("branch_id") or "")
    user_sem = user.get("semester")
    
    # 1. Department Isolation Check
    if requested_dept_id:
        req_dept_str = str(requested_dept_id)
        if user_dept and user_dept != req_dept_str:
            raise HTTPException(
                status_code=403, 
                detail="Cross-tenant access forbidden: You cannot access materials outside your department."
            )
            
    # 2. Student-Specific Branch and Semester Boundary Enforcement
    if role == "student":
        # Check Branch Isolation
        if requested_branch_id:
            req_branch_str = str(requested_branch_id)
            if user_branch and user_branch != req_branch_str:
                raise HTTPException(
                    status_code=403, 
                    detail="Cross-tenant access forbidden: Students can only access materials for their assigned branch."
                )

        # Check Requested Semester Isolation
        if requested_semester is not None and user_sem is not None:
            try:
                if int(requested_semester) != int(user_sem):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Cross-semester access forbidden: You are enrolled in Semester {user_sem} and cannot access Semester {requested_semester} materials."
                    )
            except (ValueError, TypeError):
                pass

        # Check Course Code Semester and Branch Mapping
        if requested_course_code:
            from database.mongo_manager import courses_col
            course = courses_col.find_one({"course_code": str(requested_course_code).upper().strip()})
            if course:
                # Enforce course branch restriction
                course_branch = str(course.get("branch_id") or "")
                if user_branch and course_branch and user_branch != course_branch:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Cross-tenant access forbidden: Course '{requested_course_code}' belongs to another branch."
                    )
                # Enforce course semester restriction
                course_sem = course.get("semester_number")
                if course_sem is not None and user_sem is not None:
                    try:
                        if int(course_sem) != int(user_sem):
                            raise HTTPException(
                                status_code=403,
                                detail=f"Cross-semester access forbidden: Course '{requested_course_code}' is taught in Semester {course_sem}, but you are enrolled in Semester {user_sem}."
                            )
                    except (ValueError, TypeError):
                        pass
            
    return True

