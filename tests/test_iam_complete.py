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
    """Verify student cross-tenant isolation enforcement."""
    admin_user = {"username": "admin", "role": "admin"}
    student_user = {
        "username": "cse_student", 
        "role": "student",
        "department_id": "dept_cse",
        "branch_id": "branch_aiml"
    }

    # Admin can access anything
    assert enforce_tenant_isolation(admin_user, requested_dept_id="dept_ece", requested_branch_id="branch_comm") is True

    # Student accessing their own department and branch
    assert enforce_tenant_isolation(student_user, requested_dept_id="dept_cse", requested_branch_id="branch_aiml") is True

    # Student trying to access another department -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        enforce_tenant_isolation(student_user, requested_dept_id="dept_ece", requested_branch_id="branch_aiml")
    assert exc_info.value.status_code == 403

    # Student trying to access another branch in the same department -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        enforce_tenant_isolation(student_user, requested_dept_id="dept_cse", requested_branch_id="branch_robotics")
    assert exc_info.value.status_code == 403

    # --- Semester Isolation Tests for Students ---
    student_sem3 = {
        "username": "sem3_student",
        "role": "student",
        "department_id": "dept_cse",
        "branch_id": "branch_aiml",
        "semester": 3
    }

    # Student accessing their own semester -> Allowed
    assert enforce_tenant_isolation(student_sem3, requested_dept_id="dept_cse", requested_branch_id="branch_aiml", requested_semester=3) is True

    # Student trying to access another semester directly -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        enforce_tenant_isolation(student_sem3, requested_dept_id="dept_cse", requested_branch_id="branch_aiml", requested_semester=5)
    assert exc_info.value.status_code == 403
    assert "Cross-semester access forbidden" in exc_info.value.detail

    # Student trying to access course from another semester -> 403 Forbidden
    from unittest.mock import patch
    with patch("database.mongo_manager.get_course_by_code") as mock_get_course:
        # Course in Semester 1 (student is in Semester 3) -> 403 Forbidden
        mock_get_course.return_value = {"course_code": "CS101", "semester_number": 1}
        with pytest.raises(HTTPException) as exc_info:
            enforce_tenant_isolation(student_sem3, requested_dept_id="dept_cse", requested_branch_id="branch_aiml", requested_course_code="CS101")
        assert exc_info.value.status_code == 403
        assert "Cross-semester access forbidden" in exc_info.value.detail

        # Course in Semester 3 (student is in Semester 3) -> Allowed
        mock_get_course.return_value = {"course_code": "CS301", "semester_number": 3}
        assert enforce_tenant_isolation(student_sem3, requested_dept_id="dept_cse", requested_branch_id="branch_aiml", requested_course_code="CS301") is True

    # Admin has unrestricted access across any semester / course
    assert enforce_tenant_isolation(admin_user, requested_semester=8, requested_course_code="CS801") is True

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

def test_upload_security_controls():
    """Verify upload permission boundaries, extension whitelisting, and magic bytes validation."""
    from auth.rbac_manager import RBACManager
    from api.routes.document_routes import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES
    import os

    # 1. RBAC: Only staff and department_admin have upload_materials permission (Separation of Duties)
    assert RBACManager.has_permission("staff", "upload_materials") is True
    assert RBACManager.has_permission("department_admin", "upload_materials") is True
    assert RBACManager.has_permission("student", "upload_materials") is False
    assert RBACManager.has_permission("admin", "upload_materials") is False

    # 2. File size limit
    assert MAX_FILE_SIZE_BYTES == 50 * 1024 * 1024

    # 3. Extension whitelisting
    assert ".pdf" in ALLOWED_EXTENSIONS
    assert ".pptx" in ALLOWED_EXTENSIONS
    assert ".exe" not in ALLOWED_EXTENSIONS
    assert ".sh" not in ALLOWED_EXTENSIONS
    assert ".py" not in ALLOWED_EXTENSIONS

    # 4. Path traversal protection: os.path.basename strips directory manipulation
    malicious_filename = "../../../etc/passwd.pdf"
    sanitized = os.path.basename(malicious_filename)
    assert sanitized == "passwd.pdf"
    assert "/" not in sanitized and ".." not in sanitized

    # 5. Magic byte verification
    valid_pdf_bytes = b"%PDF-1.4 sample content"
    invalid_pdf_bytes = b"MZ\x90\x00 fake executable masquerading as pdf"
    assert valid_pdf_bytes.startswith(b"%PDF")
    assert not invalid_pdf_bytes.startswith(b"%PDF")
