import streamlit as st
import pandas as pd
import datetime
import pyotp
from streamlit_option_menu import option_menu
from bson.objectid import ObjectId

from auth.session_manager import logout_user, is_password_strong
from auth.rbac_manager import RBACManager
from utils.image_utils import get_base64_of_bin_file
from services.audit_service import log_system_event, get_audit_logs_df
from database.mongo_manager import (
    users_col,
    add_user,
    get_all_users,
    delete_user,
    get_departments,
    get_branches_by_department,
    add_department,
    add_branch,
    add_course,
    delete_course,
    get_all_courses_with_details,
    verify_login,
    update_password,
    get_user_2fa_secret,
    enable_user_2fa,
    disable_user_2fa,
    promote_student_semester,
    toggle_promotion_hold,
    toggle_user_status,
    calculate_current_semester
)
from database.redis_manager import revoke_user_sessions

def render_admin_view():
    user = st.session_state.get("user", {})
    if not RBACManager.has_permission(user.get("role"), "manage_users"):
        st.error("Access Denied: You do not have permission to view this page.")
        if st.button("Logout"):
            logout_user()
            st.rerun()
        st.stop()
    
    # --- Top Right Logout Bar ---
    top_col1, top_col2 = st.columns([9, 1])
    with top_col2:
        if st.button("Logout", use_container_width=True, type="secondary"):
            logout_user()
            st.rerun()

    # --- Custom Mini Sidebar Logic ---
    if "mini_menu" not in st.session_state:
        st.session_state.mini_menu = False

    def toggle_sidebar():
        st.session_state.mini_menu = not st.session_state.mini_menu

    try:
        logo_base64 = get_base64_of_bin_file("logo.png")
        img_src = f"data:image/png;base64,{logo_base64}"
    except Exception:
        img_src = "https://img.icons8.com/3d-fluency/94/graduation-cap.png"

    if st.session_state.mini_menu:
        # MINI MODE
        st.markdown("""
            <style>
                [data-testid="stSidebar"] { min-width: 82px !important; max-width: 82px !important; }
            </style>
        """, unsafe_allow_html=True)
        
        st.sidebar.button("☰", on_click=toggle_sidebar, key="toggle_btn_mini", use_container_width=True)
        
        st.sidebar.markdown(f"""
            <div style='display: flex; justify-content: center; margin-bottom: 20px; margin-top: 5px;'>
                <img src='{img_src}' style='height: 30px; width: 30px; object-fit: contain;' />
            </div>
        """, unsafe_allow_html=True)
        
        menu_styles = {
            "container": {"padding": "0!important", "background-color": "transparent!important", "border": "none"},
            "icon": {"color": "#0F0F0F", "font-size": "24px", "margin": "0 0 4px 0"},
            "nav-link": {
                "font-size": "10px", 
                "text-align": "center",
                "margin": "0 0 10px 0",
                "padding": "10px 0",
                "color": "#0F0F0F",
                "--hover-color": "#F2F2F2",
                "border-radius": "10px",
                "display": "flex",
                "flex-direction": "column",
                "align-items": "center",
                "justify-content": "center",
                "line-height": "1.2"
            },
            "nav-link-selected": {"background-color": "transparent", "font-weight": "bold", "color": "#0F0F0F"},
        }
    else:
        # FULL MODE
        st.markdown("""
            <style>
                [data-testid="stSidebar"] { min-width: 240px !important; max-width: 240px !important; }
                [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] { align-items: center; }
            </style>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.sidebar.columns([1, 3])
        with col1:
            st.button("☰", on_click=toggle_sidebar, key="toggle_btn_full")
            
        with col2:
            st.markdown(f"""
                <div style='display: flex; align-items: center; justify-content: flex-start; gap: 10px; margin-top: 2px;'>
                    <img src='{img_src}' style='height: 28px; width: 28px; object-fit: contain;' />
                    <h2 style='margin: 0; color: #0F0F0F; font-weight: 700; font-family: sans-serif; font-size: 20px; letter-spacing: -0.5px;'>StudyMate</h2>
                </div>
            """, unsafe_allow_html=True)
        
        st.sidebar.markdown(f"<div style='margin-bottom: 10px; margin-top: 15px; padding-left: 10px; color: #6C665F; font-size: 13px;'><strong>🛡️ Admin:</strong> {user.get('username')}</div>", unsafe_allow_html=True)
        
        menu_styles = {
            "container": {"padding": "0!important", "background-color": "transparent!important", "border": "none"},
            "icon": {"color": "#0F0F0F", "font-size": "20px"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left",
                "margin": "2px 10px",
                "padding": "10px 15px",
                "color": "#0F0F0F",
                "--hover-color": "#F2F2F2",
                "border-radius": "10px",
                "display": "flex",
                "flex-direction": "row",
                "align-items": "center"
            },
            "nav-link-selected": {"background-color": "#F2F2F2", "font-weight": "bold", "color": "#0F0F0F"},
        }

    st.sidebar.divider()
    
    # Navigation Menu
    with st.sidebar:
        nav_selection = option_menu(
            menu_title=None,
            options=["Register User", "View/Manage Users", "Manage Curriculum", "Analytics", "Settings"],
            icons=["person-plus", "database", "book", "graph-up", "gear"], 
            default_index=0,
            styles=menu_styles
        )

    # --- Main Area Content ---
    if nav_selection == "Register User":
        st.title("Admin Dashboard")
        st.markdown("Register new students and staff into the system.")
        
        role = st.radio("Select Role to Register", ["Student", "Staff"], horizontal=True)
        
        st.subheader(f"{role} Details")
        
        departments = get_departments()
        dept_options = {str(d["_id"]): d["dept_name"] for d in departments}
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name")
            user_id = st.text_input("Roll Number" if role == "Student" else "Staff ID")
            st.markdown("<p style='font-size: 14px; margin-bottom: 5px; color: #31333F;'>Date of Birth</p>", unsafe_allow_html=True)
            d_col1, d_col2, d_col3 = st.columns([1.2, 1.5, 1.5])
            with d_col1:
                dob_day = st.selectbox("Day", list(range(1, 32)), label_visibility="collapsed")
            with d_col2:
                dob_month = st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], label_visibility="collapsed")
            with d_col3:
                current_year = datetime.date.today().year
                dob_year = st.selectbox("Year", list(range(current_year, 1899, -1)), index=current_year - 2004, label_visibility="collapsed")
        with col2:
            selected_dept_id = st.selectbox(
                "Department", 
                options=list(dept_options.keys()), 
                format_func=lambda x: dept_options[x]
            )
            
            selected_branch_id = None
            selected_semester = None
            if role == "Student" and selected_dept_id:
                branches = get_branches_by_department(ObjectId(selected_dept_id))
                branch_options = {str(b["_id"]): b["branch_name"] for b in branches}
                selected_branch_id = st.selectbox(
                    "Branch",
                    options=list(branch_options.keys()),
                    format_func=lambda x: branch_options[x]
                )
            
        st.write("")
        submit_btn = st.button(f"Register {role}", type="primary")
        
        if submit_btn:
            if name and user_id:
                try:
                    month_map = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
                    dob = datetime.date(dob_year, month_map[dob_month], dob_day)
                    
                    # Generate strong password: 01/01/2004 -> 01Jan2004@
                    auto_password = dob.strftime("%d%b%Y") + "@"
                    
                    is_strong, strength_msg = is_password_strong(auto_password)
                    
                    if not is_strong:
                        st.error(f"Generated password is too weak: {strength_msg}")
                    else:
                        success, msg = add_user(
                            name=name, 
                            user_id=user_id, 
                            role=role, 
                            dob_str=dob.strftime("%d/%m/%Y"), 
                            department_id=ObjectId(selected_dept_id) if selected_dept_id else None, 
                            branch_id=ObjectId(selected_branch_id) if selected_branch_id else None, 
                            semester=selected_semester, 
                            password=auto_password
                        )
                    
                        if success:
                            st.success(f"Successfully registered {role}: {name} ({user_id})")
                            st.info("Password generated successfully.")
                        else:
                            st.error(f"Failed to register user: {msg}")
                except ValueError:
                    st.error("Invalid Date! Please ensure the selected day is valid for the month.")
            else:
                st.error("Please fill in all required fields (Name, ID, and DOB).")

    elif nav_selection == "View/Manage Users":
        st.title("User Database")
        st.markdown("View all registered users and manage their accounts.")
        
        users = get_all_users()
        if not users:
            st.info("No users registered yet.")
        else:
            # Display as a dataframe
            df = pd.DataFrame(users)
            # Check if required columns exist before ordering (in case some docs miss fields)
            cols = ["_id", "role", "name", "username", "department_name", "branch_name", "semester", "status", "promotion_hold"]
            for c in cols:
                if c not in df.columns:
                    df[c] = ""
            df = df[cols]
            df.columns = ["Mongo ID", "Role", "Name", "User ID", "Department", "Branch", "Semester", "Status", "Hold"]
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("Manage Accounts (IAM Lifecycle)")
            iam_action = st.selectbox(
                "Select Action", 
                [
                    "Select Action", 
                    "Promote Semester (Mover Phase)", 
                    "Toggle Academic Hold (Mover Phase)",
                    "Suspend / Reactivate User (Leaver Phase)",
                    "Unlock Account", 
                    "Force Password Reset", 
                    "Delete User"
                ]
            )
            
            if iam_action != "Select Action":
                user_ids = df["User ID"].tolist()
                selected_uid = st.selectbox("Select User ID", [""] + user_ids)
                target_doc = users_col.find_one({"username": selected_uid}) if selected_uid else None
                
                if iam_action == "Promote Semester (Mover Phase)":
                    if target_doc:
                        curr_sem = target_doc.get("semester", 1)
                        enrollment = target_doc.get("enrollment_date")
                        calc_sem = calculate_current_semester(enrollment)
                        st.info(f"🎓 **Student:** {selected_uid} | **Current Sem:** {curr_sem} | **Time-Based Calculated Sem:** {calc_sem}")
                        new_sem_input = st.selectbox("Select Target Semester", [1, 2, 3, 4, 5, 6, 7, 8], index=min(7, curr_sem if curr_sem < 8 else 7))
                        if st.button("Promote Student Semester", type="primary"):
                            if promote_student_semester(selected_uid, new_sem_input):
                                st.success(f"Successfully promoted {selected_uid} to Semester {new_sem_input}!")
                                st.rerun()
                            else:
                                st.error("Failed to update semester.")
                                
                elif iam_action == "Toggle Academic Hold (Mover Phase)":
                    if target_doc:
                        current_hold = target_doc.get("promotion_hold", False)
                        st.info(f"Current Academic Hold Status: **{'ACTIVE (Promotion Frozen)' if current_hold else 'NO HOLD (Auto-Promotion Active)'}**")
                        btn_label = "Remove Academic Hold" if current_hold else "Place on Academic Hold"
                        if st.button(btn_label, type="primary"):
                            toggle_promotion_hold(selected_uid, not current_hold)
                            st.success(f"Academic hold updated for {selected_uid}.")
                            st.rerun()
                            
                elif iam_action == "Suspend / Reactivate User (Leaver Phase)":
                    if target_doc:
                        is_active = target_doc.get("is_active", True)
                        st.info(f"Current Account State: **{'ACTIVE' if is_active else 'SUSPENDED / DEACTIVATED'}**")
                        if is_active:
                            st.warning("Suspending this user will immediately revoke all active JWT sessions in Redis and block logins.")
                            if st.button("Suspend Account & Kill Sessions", type="primary"):
                                toggle_user_status(selected_uid, False)
                                revoke_user_sessions(selected_uid)
                                st.success(f"User {selected_uid} has been suspended and active sessions revoked.")
                                st.rerun()
                        else:
                            st.success("Reactivating will restore normal login capabilities.")
                            if st.button("Reactivate Account", type="primary"):
                                toggle_user_status(selected_uid, True)
                                st.success(f"User {selected_uid} has been reactivated.")
                                st.rerun()

                elif iam_action == "Unlock Account":
                    st.info("Unlocking an account will reset their failed login attempts.")
                    if st.button("Unlock Account", type="primary") and selected_uid:
                        users_col.update_one({"username": selected_uid}, {"$set": {"locked_out": False, "failed_attempts": 0}})
                        st.success(f"Successfully unlocked account: {selected_uid}")
                        st.rerun()
                        
                elif iam_action == "Force Password Reset":
                    st.info("Ensure the new password meets security requirements (A-Z, a-z, 0-9, and special character).")
                    new_pwd = st.text_input("New Password", type="password")
                    if st.button("Reset Password", type="primary") and selected_uid and new_pwd:
                        is_strong, msg = is_password_strong(new_pwd)
                        if not is_strong:
                            st.error(f"Weak Password: {msg}")
                        else:
                            if update_password(selected_uid, new_pwd):
                                st.success(f"Successfully reset password for: {selected_uid}")
                                st.rerun()
                            else:
                                st.error("Failed to reset password.")
                                
                elif iam_action == "Delete User":
                    st.error("Warning: This action is permanent and cannot be undone.")
                    if st.button("Delete User", type="primary") and selected_uid:
                        if delete_user(selected_uid):
                            st.success(f"Deleted user: {selected_uid}")
                            st.rerun()

    elif nav_selection == "Analytics":
        st.title("System Analytics")
        st.markdown("Track system usage and auditing events.")
        
        df = get_audit_logs_df()
        
        if df.empty:
            st.info("No audit logs found.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                logins = df[df['event_type'] == 'LOGIN'].shape[0]
                st.metric("Total Logins", logins)
            with col2:
                docs = df[df['event_type'] == 'DOCUMENT'].shape[0]
                st.metric("Document Accesses", docs)
            with col3:
                system_events = df[df['event_type'] == 'SYSTEM'].shape[0]
                st.metric("System Events", system_events)
                
            st.subheader("Event Timeline")
            # Convert timestamp to date
            df['date'] = df['timestamp'].dt.date
            daily_events = df.groupby('date').size().reset_index(name='counts')
            if not daily_events.empty:
                st.bar_chart(daily_events.set_index('date'))
                
            st.subheader("Raw Audit Logs")
            st.dataframe(df.sort_values(by="timestamp", ascending=False), use_container_width=True)

    elif nav_selection == "Manage Curriculum":
        st.title("Curriculum & Course Management")
        st.markdown("Add and manage departments, academic branches, and semester courses.")
        
        curr_tab1, curr_tab2, curr_tab3 = st.tabs(["📚 Courses", "🌿 Branches", "🏛️ Departments"])
        
        # 1. Courses Tab
        with curr_tab1:
            st.subheader("Existing Courses")
            all_courses = get_all_courses_with_details()
            if all_courses:
                df_courses = pd.DataFrame(all_courses)
                display_cols = ["course_code", "course_name", "semester_number", "branch_name", "department_name"]
                for col in display_cols:
                    if col not in df_courses.columns:
                        df_courses[col] = ""
                df_courses = df_courses[display_cols]
                df_courses.columns = ["Code", "Course Name", "Semester", "Branch", "Department"]
                st.dataframe(df_courses, use_container_width=True, hide_index=True)
                
                st.write("")
                with st.expander("🗑️ Delete a Course"):
                    course_map = {c["_id"]: f"{c.get('course_code')} - {c.get('course_name')}" for c in all_courses}
                    selected_c_id = st.selectbox("Select Course to Remove", options=list(course_map.keys()), format_func=lambda x: course_map[x])
                    if st.button("Delete Course", type="secondary") and selected_c_id:
                        if delete_course(selected_c_id):
                            st.success("Course deleted successfully.")
                            st.rerun()
                        else:
                            st.error("Failed to delete course.")
            else:
                st.info("No courses created yet.")
                
            st.divider()
            st.subheader("Add New Course")
            departments = get_departments()
            dept_opts = {str(d["_id"]): d["dept_name"] for d in departments}
            
            c_dept = st.selectbox("Department", options=list(dept_opts.keys()), format_func=lambda x: dept_opts[x], key="c_add_dept")
            c_branches = get_branches_by_department(ObjectId(c_dept)) if c_dept else []
            branch_opts = {str(b["_id"]): b["branch_name"] for b in c_branches}
            
            if not branch_opts:
                st.warning("No branches found in this department. Please create a branch first in the 'Branches' tab.")
            else:
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    c_branch = st.selectbox("Branch", options=list(branch_opts.keys()), format_func=lambda x: branch_opts[x], key="c_add_branch")
                    c_sem = st.selectbox("Semester", options=list(range(1, 9)), key="c_add_sem")
                with col_c2:
                    c_code = st.text_input("Course Code (e.g. CS601)", key="c_add_code")
                    c_name = st.text_input("Course Name (e.g. Cloud Computing)", key="c_add_name")
                    
                if st.button("Add Course", type="primary"):
                    if c_branch and c_sem and c_code and c_name:
                        success, msg = add_course(c_code, c_name, c_branch, c_sem)
                        if success:
                            st.success(f"Successfully added course: {c_code.upper()} - {c_name}")
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")
                    else:
                        st.error("Please fill in all course fields.")

        # 2. Branches Tab
        with curr_tab2:
            st.subheader("Add New Branch")
            departments = get_departments()
            dept_opts = {str(d["_id"]): d["dept_name"] for d in departments}
            
            if not dept_opts:
                st.warning("Please create a department first.")
            else:
                b_dept = st.selectbox("Select Department for Branch", options=list(dept_opts.keys()), format_func=lambda x: dept_opts[x], key="b_add_dept")
                b_name = st.text_input("Branch Name (e.g. B.Tech Artificial Intelligence)", key="b_add_name")
                
                if st.button("Add Branch", type="primary"):
                    if b_name and b_dept:
                        success, msg = add_branch(b_name, b_dept)
                        if success:
                            st.success(f"Branch '{b_name}' created successfully!")
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")
                    else:
                        st.error("Please enter a branch name.")
                        
            st.divider()
            st.subheader("Current Branches")
            if dept_opts:
                for d_id, d_name in dept_opts.items():
                    branches = get_branches_by_department(ObjectId(d_id))
                    st.markdown(f"**{d_name}:**")
                    if branches:
                        for b in branches:
                            st.write(f"- {b['branch_name']}")
                    else:
                        st.caption("No branches in this department yet.")

        # 3. Departments Tab
        with curr_tab3:
            st.subheader("Add New Department")
            d_name = st.text_input("Department Name (e.g. School of Electrical Sciences)", key="d_add_name")
            if st.button("Add Department", type="primary"):
                if d_name:
                    success, msg = add_department(d_name)
                    if success:
                        st.success(f"Department '{d_name}' created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")
                else:
                    st.error("Please enter a department name.")
                    
            st.divider()
            st.subheader("Current Departments")
            departments = get_departments()
            for d in departments:
                st.write(f"🏛️ **{d.get('dept_name')}**")

    elif nav_selection == "Settings":
        st.title("Admin Account Settings")
        user = st.session_state.get("user", {})
        
        st.markdown("### Change Password")
        with st.form("admin_password_form"):
            old_p = st.text_input("Current Password", type="password")
            new_p = st.text_input("New Password", type="password")
            conf_p = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("Update Password", type="primary"):
                if not old_p or not new_p or not conf_p:
                    st.error("All fields are required.")
                elif new_p != conf_p:
                    st.error("Passwords do not match.")
                else:
                    is_s, s_msg = is_password_strong(new_p)
                    if not is_s:
                        st.error(f"Weak Password: {s_msg}")
                    else:
                        ok, _ = verify_login(user["username"], old_p)
                        if not ok:
                            st.error("Current password incorrect.")
                        else:
                            if update_password(user["username"], new_p):
                                log_system_event(user["username"], user["role"], "password_change", "Admin changed password")
                                st.success("Password updated successfully!")
                            else:
                                st.error("Failed to update password.")

        st.divider()
        st.markdown("### 🔐 Two-Factor Authentication (2FA / TOTP)")
        
        current_secret = get_user_2fa_secret(user.get("username"))
        if current_secret:
            st.success("✅ Two-Factor Authentication is currently **ACTIVE** on your Administrator account.")
            if st.button("Disable 2FA", type="secondary"):
                disable_user_2fa(user.get("username"))
                log_system_event(user.get("username"), user.get("role"), "2fa_disabled", "Admin disabled 2FA")
                st.info("2FA disabled successfully.")
                st.rerun()
        else:
            st.info("Protect your Administrator account with Google Authenticator or Microsoft Authenticator.")
            if "temp_2fa_secret" not in st.session_state:
                if st.button("Setup Two-Factor Authentication"):
                    st.session_state["temp_2fa_secret"] = pyotp.random_base32()
                    st.rerun()
            else:
                secret = st.session_state["temp_2fa_secret"]
                st.markdown(f"**Step 1:** Enter this key into your Authenticator app:")
                st.code(secret, language="text")
                st.caption(f"Account: {user.get('username')} | Issuer: StudyMate")
                
                with st.form("admin_verify_2fa_form"):
                    st.markdown("**Step 2:** Enter the 6-digit code shown in your app to activate:")
                    test_code = st.text_input("6-digit TOTP Code", max_chars=6)
                    c_sub, c_can = st.columns(2)
                    with c_sub:
                        act_btn = st.form_submit_button("Activate 2FA", type="primary")
                    with c_can:
                        can_btn = st.form_submit_button("Cancel")
                        
                    if can_btn:
                        del st.session_state["temp_2fa_secret"]
                        st.rerun()
                        
                    if act_btn:
                        totp = pyotp.TOTP(secret)
                        if totp.verify(test_code.strip(), valid_window=1):
                            enable_user_2fa(user.get("username"), secret)
                            del st.session_state["temp_2fa_secret"]
                            log_system_event(user.get("username"), user.get("role"), "2fa_enabled", "Admin enabled 2FA")
                            st.success("Two-Factor Authentication successfully activated!")
                            st.rerun()
                        else:
                            st.error("Invalid verification code. Please ensure your device clock is accurate.")

