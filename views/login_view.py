import streamlit as st
from auth.session_manager import login_user
from utils.image_utils import get_base64_of_bin_file

def render_login_view():
    try:
        logo_base64 = get_base64_of_bin_file("logo.png")
        img_src = f"data:image/png;base64,{logo_base64}"
    except FileNotFoundError:
        img_src = "https://img.icons8.com/3d-fluency/94/graduation-cap.png"

    # Header mimicking an elegant portal
    st.markdown(f"""
        <div style='background-color: #FFFFFF; padding: 15px; border-radius: 8px; border-left: 5px solid #D97757; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <img src='{img_src}' style='height: 50px; object-fit: contain;' />
                <h2 style='color: #1F1D1A; margin: 0; font-weight: 700; font-family: serif;'>
                    StudyMate AI
                </h2>
            </div>
        </div>
        <div style='background: #F2EFE9; padding: 12px; border-radius: 6px; margin-bottom: 40px; text-align: center; border: 1px solid #E5E0D8;'>
            <h4 style='color: #6C665F; margin: 0; font-weight: 500;'>Welcome to the AI-Powered Learning Portal</h4>
        </div>
    """, unsafe_allow_html=True)
    
    col_menu, col_form = st.columns([1, 2.5])
    
    with col_menu:
        st.markdown("<h4 style='color: #6C665F; margin-bottom: 15px; font-weight: 500;'>Select Role</h4>", unsafe_allow_html=True)
        role = st.radio(
            "Role",
            ["Student", "Staff", "Admin"],
            label_visibility="collapsed"
        )
        
    with col_form:
        # The form will automatically get the glassmorphism styling from style.py
        with st.form("login_form"):
            st.markdown(f"<h3 style='text-align: center; color: #1F1D1A; margin-bottom: 25px; font-family: serif;'>{role} Login</h3>", unsafe_allow_html=True)
            
            # Form fields based on role
            if role == "Admin":
                admin_id = st.text_input("Admin ID")
                password = st.text_input("Password", type="password")
            elif role == "Staff":
                login_id = st.text_input("Staff ID")
                password = st.text_input("Password", type="password")
            else: # Student
                username = st.text_input("Rollno")
                password = st.text_input("Password", type="password")
            
            st.write("") # Spacer
            
            # Center the submit button
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
            with btn_col2:
                submit_button = st.form_submit_button("Login", use_container_width=True)
            
            st.markdown("<div style='text-align: center; margin-top: 15px;'><a href='#' style='color: #D97757; font-weight: 500; text-decoration: underline; font-size: 14px;'>Forgot Password?</a></div>", unsafe_allow_html=True)
            
            if submit_button:
                # Determine which ID to use based on role
                user_identifier = ""
                if role == "Admin":
                    user_identifier = admin_id
                elif role == "Staff":
                    user_identifier = login_id
                else:
                    user_identifier = username

                if user_identifier and password:
                    success, message = login_user(user_identifier, password=password, role=role)
                    from services.audit_service import log_login
                    if success:
                        log_login(user_identifier, role, "success")
                        st.success(f"Logging in as {role}...")
                        st.rerun()
                    else:
                        log_login(user_identifier, role, "failed")
                        st.error(message)
                else:
                    st.error("Please enter both ID and Password.")

    # Footer
    st.markdown("""
        <div style='background-color: #FFFFFF; padding: 15px; border-radius: 8px; margin-top: 60px; text-align: center; border: 1px solid #E5E0D8;'>
            <p style='color: #6C665F; margin: 0; font-size: 13px;'>Copyright © 2026 Powered by StudyMate</p>
        </div>
    """, unsafe_allow_html=True)
