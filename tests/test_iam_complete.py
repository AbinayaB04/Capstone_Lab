import pytest
import datetime
import os
import jwt
from fastapi import HTTPException
from auth.rbac_manager import RBACManager
from api.dependencies import (
    get_current_user, 
    require_permission, 
    require_role, 
    enforce_tenant_isolation, 
    JWT_SECRET
)
from database.mongo_manager import (
    generate_backup_codes, 
    enable_user_2fa, 
    disable_user_2fa, 
    verify_totp, 
    unlock_user_account,
    users_col
)
from auth.session_manager import is_password_strong, create_jwt

def test_rbac_permissions_matrix():
    """Verify RBAC permissions for all 4 roles."""
    assert RBACManager.has_permission("admin", "manage_users") is True
    assert RBACManager.has_permission("admin", "manage_departments") is True
    assert RBACManager.has_permission("staff", "upload_materials") is True
    assert RBACManager.has_permission("staff", "delete_materials") is True
    assert RBACManager.has_permission("student", "ask_ai") is True
    assert RBACManager.has_permission("student", "download_materials") is True
    
    # Students cannot upload or manage users
    assert RBACManager.has_permission("student", "upload_materials") is False
    assert RBACManager.has_permission("student", "manage_users") is False
    # Staff cannot manage users
    assert RBACManager.has_permission("staff", "manage_users") is False

def test_jwt_dependency_validation():
    """Verify get_current_user parses valid Bearer tokens and rejects invalid ones."""
    # 1. Missing header
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None)
    assert exc_info.value.status_code == 401

    # 2. Malformed header
    with pytest.raises(HTTPException) as exc_info:
        get_current_user("Basic dXNlcjpwYXNz")
    assert exc_info.value.status_code == 401

    # 3. Valid token
    payload = {
        "username": "test_user_777",
        "role": "student",
        "department_id": "dept_cse",
        "branch_id": "branch_ai",
        "semester": 4,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    }
    valid_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    user = get_current_user(f"Bearer {valid_token}")
    assert user["username"] == "test_user_777"
    assert user["role"] == "student"

    # 4. Expired token
    expired_payload = {
        "username": "expired_user",
        "role": "student",
        "exp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=10)
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(f"Bearer {expired_token}")
    assert exc_info.value.status_code == 401

def test_require_permission_dependency():
    """Verify require_permission allows permitted roles and raises 403 on forbidden roles."""
    student_user = {"username": "s1", "role": "student"}
    staff_user = {"username": "prof1", "role": "staff"}

    check_upload = require_permission("upload_materials")
    check_ask_ai = require_permission("ask_ai")

    # Staff can upload
    assert check_upload(staff_user) == staff_user

    # Student cannot upload -> 403
    with pytest.raises(HTTPException) as exc_info:
        check_upload(student_user)
    assert exc_info.value.status_code == 403

    # Student can ask AI
    assert check_ask_ai(student_user) == student_user

def test_multi_tenant_isolation_enforcement():
    """Verify student cross-tenant and cross-semester isolation enforcement."""
    admin_user = {"username": "admin", "role": "admin"}
    student_user = {
        "username": "cse_student", 
        "role": "student",
        "department_id": "dept_cse",
        "branch_id": "branch_aiml",
        "semester": 8
    }

    # Admin can access anything across departments, branches, semesters, and courses
    assert enforce_tenant_isolation(
        admin_user, 
        requested_dept_id="dept_ece", 
        requested_branch_id="branch_comm", 
        requested_semester=3, 
        requested_course_code="CS301"
    ) is True

    # Student accessing their own department, branch, and enrolled semester (8)
    assert enforce_tenant_isolation(
        student_user, 
        requested_dept_id="dept_cse", 
        requested_branch_id="branch_aiml",
        requested_semester=8
    ) is True

    # Student trying to access another department -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        enforce_tenant_isolation(student_user, requested_dept_id="dept_ece", requested_branch_id="branch_aiml")
    assert exc_info.value.status_code == 403

    # Student trying to access another branch in the same department -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        enforce_tenant_isolation(student_user, requested_dept_id="dept_cse", requested_branch_id="branch_robotics")
    assert exc_info.value.status_code == 403

    # Student enrolled in Sem 8 trying to access Sem 3 -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        enforce_tenant_isolation(student_user, requested_semester=3)
    assert exc_info.value.status_code == 403
    assert "Cross-semester access forbidden" in str(exc_info.value.detail)

    # Student enrolled in Sem 8 trying to access a Sem 3 course (CS301) -> 403 Forbidden
    from database.mongo_manager import courses_col
    courses_col.update_one(
        {"course_code": "CS301"},
        {"$set": {"course_code": "CS301", "course_name": "Data Structures", "branch_id": "branch_aiml", "semester_number": 3}},
        upsert=True
    )
    with pytest.raises(HTTPException) as exc_info:
        enforce_tenant_isolation(student_user, requested_course_code="CS301")
    assert exc_info.value.status_code == 403
    assert "Cross-semester access forbidden" in str(exc_info.value.detail)

def test_2fa_backup_recovery_codes_lifecycle():
    """Verify 2FA backup codes generation, consumption, and one-time use."""
    test_username = "test_2fa_user_999"
    # Seed temporary test user
    users_col.delete_one({"username": test_username})
    users_col.insert_one({
        "username": test_username,
        "name": "Test 2FA User",
        "role": "student"
    })

    try:
        import pyotp
        secret = pyotp.random_base32()
        
        # Enable 2FA: generates backup codes
        backup_codes = enable_user_2fa(test_username, secret)
        assert len(backup_codes) == 8
        first_code = backup_codes[0]

        # Verify with first backup code -> True
        assert verify_totp(test_username, first_code) is True

        # Second attempt with same backup code MUST FAIL (single-use guarantee!)
        assert verify_totp(test_username, first_code) is False

        # Another backup code from the list should still work
        second_code = backup_codes[1]
        assert verify_totp(test_username, second_code) is True
        assert verify_totp(test_username, second_code) is False
    finally:
        users_col.delete_one({"username": test_username})

def test_account_unlock():
    """Verify account unlock mechanism resets failed attempts and lockout flag."""
    test_username = "locked_user_555"
    users_col.delete_one({"username": test_username})
    users_col.insert_one({
        "username": test_username,
        "locked_out": True,
        "failed_attempts": 5
    })

    try:
        assert unlock_user_account(test_username) is True
        user = users_col.find_one({"username": test_username})
        assert user["locked_out"] is False
        assert user["failed_attempts"] == 0
    finally:
        users_col.delete_one({"username": test_username})
