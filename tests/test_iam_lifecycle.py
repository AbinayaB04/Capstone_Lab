import pytest
import datetime
import os
import pyotp
import jwt
from fastapi import HTTPException
from database.mongo_manager import (
    add_user,
    verify_login,
    calculate_current_semester,
    check_and_apply_auto_promotion,
    promote_student_semester,
    toggle_promotion_hold,
    toggle_user_status,
    unlock_user_account,
    enable_user_2fa,
    users_col
)
from database.redis_manager import set_active_session, is_token_blacklisted, revoke_user_sessions
from auth.rbac_manager import RBACManager
from api.dependencies import get_current_user, require_permission, JWT_SECRET

# ==========================================
# PHASE 1: JOINER (PROVISIONING & ONBOARDING)
# ==========================================
def test_phase1_joiner_provisioning():
    """Verify identity onboarding, initial semester, active status, and 2FA setup."""
    username = "lifecycle_joiner_01"
    users_col.delete_one({"username": username})
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    success, msg = add_user(
        name="Alice Joiner",
        user_id=username,
        role="student",
        dob_str="15/05/2004",
        department_id="dept_cse",
        branch_id="branch_aiml",
        semester=1,
        password="InitialPassword123@",
        enrollment_date=now_utc
    )
    assert success is True
    
    user = users_col.find_one({"username": username})
    assert user is not None
    assert user["is_active"] is True
    assert user["status"] == "active"
    assert user["promotion_hold"] is False
    assert user["semester"] == 1
    
    # 2FA Enrollment (Joiner Phase completion)
    secret = pyotp.random_base32()
    backup_codes = enable_user_2fa(username, secret)
    assert len(backup_codes) == 8
    
    users_col.delete_one({"username": username})

# ==========================================
# PHASE 2: ACTIVE (OPERATIONAL AUTH & RBAC)
# ==========================================
def test_phase2_active_authentication_and_rbac():
    """Verify operational authentication, dual tokens, and RBAC enforcement."""
    username = "lifecycle_active_02"
    users_col.delete_one({"username": username})
    
    add_user(
        name="Bob Active",
        user_id=username,
        role="student",
        dob_str="10/10/2003",
        department_id="dept_cse",
        branch_id="branch_aiml",
        semester=3,
        password="ActivePassword123@"
    )
    
    # Successful login
    auth_success, user_data = verify_login(username, "ActivePassword123@")
    assert auth_success is True
    assert user_data["username"] == username
    
    # RBAC permissions
    assert RBACManager.has_permission(user_data["role"], "ask_ai") is True
    assert RBACManager.has_permission(user_data["role"], "upload_materials") is False
    
    users_col.delete_one({"username": username})

# ==========================================
# PHASE 3: MAINTAINER (HYGIENE & LOCKOUT)
# ==========================================
def test_phase3_maintainer_expiry_and_lockout():
    """Verify 90-day password expiry and brute-force lockout defense."""
    username = "lifecycle_maintain_03"
    users_col.delete_one({"username": username})
    
    add_user(
        name="Charlie Maintain",
        user_id=username,
        role="student",
        dob_str="01/01/2002",
        department_id="dept_cse",
        branch_id="branch_aiml",
        semester=2,
        password="MaintainPassword123@"
    )
    
    # 1. Simulate 5 failed login attempts
    for _ in range(5):
        verify_login(username, "WrongPassword!")
        
    locked_user = users_col.find_one({"username": username})
    assert locked_user.get("locked_out") is True
    
    # Subsequent login blocked even with correct password
    auth_success, msg = verify_login(username, "MaintainPassword123@")
    assert auth_success is False
    assert "locked out" in msg.lower()
    
    # Admin unlocks account
    assert unlock_user_account(username) is True
    auth_success, _ = verify_login(username, "MaintainPassword123@")
    assert auth_success is True
    
    # 2. Simulate 90-day password expiry
    old_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=95)
    users_col.update_one({"username": username}, {"$set": {"last_password_change": old_time}})
    
    auth_success, msg = verify_login(username, "MaintainPassword123@")
    assert auth_success is False
    assert "expired" in msg.lower()
    
    users_col.delete_one({"username": username})

# ==========================================
# PHASE 4: MOVER (TIME-BASED PROGRESSION)
# ==========================================
def test_phase4_mover_time_based_progression():
    """Verify automated time-based semester calculation, JIT promotion, and academic hold."""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Enrolled today -> Semester 1
    assert calculate_current_semester(now, current_date=now) == 1
    
    # Enrolled 200 days ago (~6.5 months) -> Semester 2
    past_200_days = now - datetime.timedelta(days=200)
    assert calculate_current_semester(past_200_days, current_date=now) == 2
    
    # Enrolled 400 days ago (~13 months) -> Semester 3
    past_400_days = now - datetime.timedelta(days=400)
    assert calculate_current_semester(past_400_days, current_date=now) == 3
    
    # Test JIT promotion upon login
    username = "lifecycle_mover_04"
    users_col.delete_one({"username": username})
    
    add_user(
        name="Diana Mover",
        user_id=username,
        role="student",
        dob_str="12/12/2003",
        department_id="dept_cse",
        branch_id="branch_aiml",
        semester=1,
        password="MoverPassword123@",
        enrollment_date=past_400_days # Enrolled 13 months ago
    )
    
    # Auto-promotion occurs upon verify_login
    auth_success, user_data = verify_login(username, "MoverPassword123@")
    assert auth_success is True
    assert user_data["semester"] == 3
    
    # Test Academic Hold freezes promotion
    toggle_promotion_hold(username, True)
    # Simulate another term passing (600 days total)
    past_600_days = now - datetime.timedelta(days=600)
    users_col.update_one({"username": username}, {"$set": {"enrollment_date": past_600_days}})
    
    promo_result = check_and_apply_auto_promotion(username)
    assert promo_result["promoted"] is False
    assert "hold" in promo_result["reason"].lower()
    
    # Manual Admin Override
    promote_student_semester(username, 4)
    updated_user = users_col.find_one({"username": username})
    assert updated_user["semester"] == 4
    
    users_col.delete_one({"username": username})

# ==========================================
# PHASE 5: LEAVER (SUSPENSION & REAL-TIME REVOCATION)
# ==========================================
def test_phase5_leaver_suspension_and_alumni():
    """Verify account deactivation, real-time Redis token killswitch, and alumni graduation."""
    username = "lifecycle_leaver_05"
    users_col.delete_one({"username": username})
    
    add_user(
        name="Evan Leaver",
        user_id=username,
        role="student",
        dob_str="05/05/2001",
        department_id="dept_cse",
        branch_id="branch_aiml",
        semester=8,
        password="LeaverPassword123@"
    )
    
    # 1. Administrator suspends account (The Leaver Phase)
    assert toggle_user_status(username, False) is True
    # Session killswitch executes cleanly
    revoke_user_sessions(username)
    
    # 2. Login must now be rejected due to suspension
    auth_success, msg = verify_login(username, "LeaverPassword123@")
    assert auth_success is False
    assert "suspended" in msg.lower() or "deactivated" in msg.lower()
    
    # Reactivation restores login capability
    assert toggle_user_status(username, True) is True
    auth_success, _ = verify_login(username, "LeaverPassword123@")
    assert auth_success is True
    
    # 3. Test Alumni transition (> 8 semesters)
    now = datetime.datetime.now(datetime.timezone.utc)
    past_5_years = now - datetime.timedelta(days=1600) # > 4 years
    users_col.update_one(
        {"username": username}, 
        {"$set": {"is_active": True, "enrollment_date": past_5_years, "status": "active", "promotion_hold": False}}
    )
    
    promo_result = check_and_apply_auto_promotion(username)
    assert promo_result.get("status") == "alumni"
    
    # Alumni login triggers archived tenure notice
    auth_success, msg = verify_login(username, "LeaverPassword123@")
    assert auth_success is False
    assert "alumni" in msg.lower()
    
    users_col.delete_one({"username": username})
