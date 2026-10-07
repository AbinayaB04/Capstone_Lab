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
    
    from auth.session_manager import init_session_state, check_idle_timeout
    
    # Initialize session state variables
    init_session_state()
    
    if st.session_state["logged_in"]:
        if not check_idle_timeout(timeout_minutes=15):
            st.rerun()
        
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
