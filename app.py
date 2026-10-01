import streamlit as st
import os

# Must be the first Streamlit command
st.set_page_config(
    page_title="StudyMate AI",
    page_icon="📘",
    layout="wide"
)

# BYPASS ANACONDA'S CORRUPTED OPENSSL LIBRARY
os.environ["MONGO_NO_PYOPENSSL"] = "1"

from utils.style import inject_custom_css
from auth.session_manager import init_session_state
from views.login_view import render_login_view
from views.student_view import render_student_view
from views.staff_view import render_staff_view
from views.admin_view import render_admin_view

def main():
    # Inject CSS styles
    inject_custom_css()
    
    # Initialize session state variables
    init_session_state()
    
    import time
    SESSION_TIMEOUT_SECONDS = 300 # 5 minutes
    
    if st.session_state["logged_in"]:
        current_time = time.time()
        time_elapsed = current_time - st.session_state.get("last_activity", current_time)
        
        if time_elapsed > SESSION_TIMEOUT_SECONDS:
            from auth.session_manager import logout_user
            logout_user()
            st.session_state["session_expired"] = True
            st.rerun()
            
        # Update last activity timestamp on every interaction
        st.session_state["last_activity"] = current_time
        
    # Route based on login status
    if not st.session_state["logged_in"]:
        if st.session_state.get("session_expired"):
            st.warning("Your session has expired due to 5 minutes of inactivity. Please log in again.")
            st.session_state["session_expired"] = False
            
        render_login_view()
    else:
        role = st.session_state["user"].get("role", "student").lower()
        if role == "admin":
            render_admin_view()
        elif role == "staff":
            render_staff_view()
        else:
            render_student_view()

if __name__ == "__main__":
    main()
