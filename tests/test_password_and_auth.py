import os
import pyotp
from auth.session_manager import is_password_strong, create_jwt, verify_jwt

def test_password_strength_validation():
    # Weak passwords
    is_strong, _ = is_password_strong("short")
    assert is_strong is False
    
    is_strong, _ = is_password_strong("alllowercase1!")
    assert is_strong is False

    is_strong, _ = is_password_strong("ALLUPPERCASE1!")
    assert is_strong is False

    is_strong, _ = is_password_strong("NoNumbersHere!")
    assert is_strong is False

    is_strong, _ = is_password_strong("NoSpecialChars123")
    assert is_strong is False

    # Strong password
    is_strong, msg = is_password_strong("ValidStrongPass123@")
    assert is_strong is True
    assert msg == "Valid"

def test_jwt_token_flow():
    user_payload = {
        "username": "student_test_101",
        "name": "Jane Doe",
        "role": "student",
        "department_id": "dept_123",
        "branch_id": "branch_456",
        "semester": 5
    }
    token = create_jwt(user_payload)
    assert token is not None
    assert isinstance(token, str)

    valid, decoded = verify_jwt(token)
    assert valid is True
    assert decoded["username"] == "student_test_101"
    assert decoded["role"] == "student"

def test_totp_generation_and_verification():
    secret = pyotp.random_base32()
    assert len(secret) == 32

    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    assert len(current_code) == 6
    assert current_code.isdigit()

    assert totp.verify(current_code) is True
    assert totp.verify("000000") is False
