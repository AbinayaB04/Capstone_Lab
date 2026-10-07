import streamlit as st
import jwt
import os
import datetime
from database.mongo_manager import verify_login

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("CRITICAL SECURITY ERROR: JWT_SECRET environment variable is not set!")

def create_jwt(user_data):
    payload = {
        "username": user_data.get("username"),
        "name": user_data.get("name"),
        "role": user_data.get("role"),
        "department_id": str(user_data.get("department_id")) if user_data.get("department_id") else None,
        "branch_id": str(user_data.get("branch_id")) if user_data.get("branch_id") else None,
        "semester": user_data.get("semester"),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=4) # 4 hour expiry
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt(token):
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return True, decoded
    except jwt.ExpiredSignatureError:
        return False, "Session expired. Please log in again."
    except jwt.InvalidTokenError:
        return False, "Invalid session token."

def init_session_state():
    """Initialize default session state variables if they don't exist."""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    
    if "user" not in st.session_state:
        st.session_state["user"] = None
        
    import time
    if "last_activity" not in st.session_state:
        st.session_state["last_activity"] = time.time()
        
    if "session_expired" not in st.session_state:
        st.session_state["session_expired"] = False
        
def check_idle_timeout(timeout_minutes=30):
    """Check if the user has been idle for too long."""
    import time
    if st.session_state.get("logged_in", False):
        current_time = time.time()
        last_activity = st.session_state.get("last_activity", current_time)
        
        if (current_time - last_activity) > (timeout_minutes * 60):
            logout_user()
            st.session_state["session_expired"] = True
            st.warning("Session expired due to inactivity.")
            return False
            
        st.session_state["last_activity"] = current_time
    return True

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
import requests

def login_user(username, password=None, role=None):
    if password:
        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/login",
                json={"username": username, "password": password, "role": role}
            )
            if response.status_code == 200:
                data = response.json()
                st.session_state["logged_in"] = True
                st.session_state["jwt_token"] = data["token"]
                st.session_state["refresh_token"] = data.get("refresh_token")
                st.session_state["user"] = data["user"]
                import time
                st.session_state["last_activity"] = time.time()
                return True, "Success"
            else:
                return False, response.json().get("detail", "Login failed")
        except requests.exceptions.RequestException as e:
            return False, f"Could not connect to API server: {e}"
    return False, "Password Required."
    
def logout_user():
    """Clear session state variables related to user and call backend to blacklist token."""
    token = st.session_state.get("jwt_token")
    if token:
        try:
            requests.post(
                f"{API_BASE_URL}/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5
            )
        except:
            pass # Fail silently if backend is unreachable during logout
            
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    if "jwt_token" in st.session_state:
        del st.session_state["jwt_token"]
    if "refresh_token" in st.session_state:
        del st.session_state["refresh_token"]
    if "last_activity" in st.session_state:
        del st.session_state["last_activity"]

def is_password_strong(password):
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    import re
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, "Valid"
