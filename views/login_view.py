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
            if st.session_state.get("show_forgot_password", False):
                st.markdown("<h3 style='text-align: center; color: #1F1D1A; margin-bottom: 25px; font-family: serif;'>Forgot Password</h3>", unsafe_allow_html=True)
                
                if not st.session_state.get("dob_verified", False):
                    fp_username = st.text_input("Username / Rollno")
                    fp_dob = st.text_input("Date of Birth (DD/MM/YYYY)")
                    
                    btn_col1, btn_col2 = st.columns([1, 1])
                    with btn_col1:
                        cancel_btn = st.form_submit_button("Cancel", use_container_width=True)
                    with btn_col2:
                        verify_btn = st.form_submit_button("Verify DOB", use_container_width=True)
                        
                    if cancel_btn:
                        st.session_state["show_forgot_password"] = False
                        st.session_state["dob_verified"] = False
                        st.rerun()
                        
                    if verify_btn:
                        import requests
                        from auth.session_manager import API_BASE_URL
                        if fp_username and fp_dob:
                            try:
                                res = requests.post(f"{API_BASE_URL}/auth/forgot-password/verify-dob", json={"username": fp_username, "dob": fp_dob})
                                if res.status_code == 200:
                                    st.session_state["dob_verified"] = True
                                    st.session_state["fp_username"] = fp_username
                                    st.session_state["fp_dob"] = fp_dob
                                    st.success("DOB verified. You can now reset your password.")
                                    st.rerun()
                                else:
                                    st.error(res.json().get("detail", "Verification failed."))
                            except requests.exceptions.RequestException:
                                st.error("Server unavailable.")
                        else:
                            st.error("Please fill in both fields.")
                else:
                    new_pass = st.text_input("New Password", type="password")
                    confirm_pass = st.text_input("Confirm New Password", type="password")
                    
                    btn_col1, btn_col2 = st.columns([1, 1])
                    with btn_col1:
                        cancel_reset_btn = st.form_submit_button("Cancel", use_container_width=True)
                    with btn_col2:
                        reset_btn = st.form_submit_button("Reset Password", use_container_width=True)
                        
                    if cancel_reset_btn:
                        st.session_state["show_forgot_password"] = False
                        st.session_state["dob_verified"] = False
                        st.rerun()
                        
                    if reset_btn:
                        if new_pass != confirm_pass:
                            st.error("Passwords do not match.")
                        else:
                            from auth.session_manager import is_password_strong, API_BASE_URL
                            is_strong, msg = is_password_strong(new_pass)
                            if not is_strong:
                                st.error(msg)
                            else:
                                import requests
                                try:
                                    res = requests.post(f"{API_BASE_URL}/auth/forgot-password/reset", json={
                                        "username": st.session_state["fp_username"],
                                        "dob": st.session_state["fp_dob"],
                                        "new_password": new_pass
                                    })
                                    if res.status_code == 200:
                                        st.success("Password reset successfully. You can now log in.")
                                        st.session_state["show_forgot_password"] = False
                                        st.session_state["dob_verified"] = False
                                        import time
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error(res.json().get("detail", "Reset failed."))
                                except requests.exceptions.RequestException:
                                    st.error("Server unavailable.")
                                    
            else:
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
            
            
            if not st.session_state.get("show_forgot_password", False):
                st.write("") # Spacer
                
                # Center the submit button
                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
                with btn_col2:
                    submit_button = st.form_submit_button("Login", use_container_width=True)
                
                if st.form_submit_button("Forgot Password?", use_container_width=True, type="secondary"):
                    st.session_state["show_forgot_password"] = True
                    st.rerun()
            
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
