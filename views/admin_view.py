import streamlit as st
from streamlit_option_menu import option_menu
from auth.session_manager import logout_user
from utils.image_utils import get_base64_of_bin_file
from database.mongo_manager import add_user, get_all_users, delete_user, get_departments, get_branches_by_department
from bson.objectid import ObjectId
import pandas as pd

def render_admin_view():
    user = st.session_state.get("user", {})
    from auth.rbac_manager import RBACManager
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
            options=["Register User", "View/Manage Users", "Analytics"],
            icons=["person-plus", "database", "graph-up"], 
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
        
        import datetime
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
                    
                    from auth.session_manager import is_password_strong
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
            cols = ["_id", "role", "name", "username", "department_name", "branch_name", "semester"]
            for c in cols:
                if c not in df.columns:
                    df[c] = ""
            df = df[cols]
            df.columns = ["Mongo ID", "Role", "Name", "User ID", "Department", "Branch", "Semester"]
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("Manage Accounts (IAM)")
            iam_action = st.selectbox("Select Action", ["Select Action", "Unlock Account", "Force Password Reset", "Delete User"])
            
            if iam_action != "Select Action":
                user_ids = df["User ID"].tolist()
                selected_uid = st.selectbox("Select User ID", [""] + user_ids)
                
                if iam_action == "Unlock Account":
                    st.info("Unlocking an account will reset their failed login attempts.")
                    if st.button("Unlock Account", type="primary") and selected_uid:
                        from database.mongo_manager import users_col
                        users_col.update_one({"username": selected_uid}, {"$set": {"locked_out": False, "failed_attempts": 0}})
                        st.success(f"Successfully unlocked account: {selected_uid}")
                        st.rerun()
                        
                elif iam_action == "Force Password Reset":
                    st.info("Ensure the new password meets security requirements (A-Z, a-z, 0-9, and special character).")
                    new_pwd = st.text_input("New Password", type="password")
                    if st.button("Reset Password", type="primary") and selected_uid and new_pwd:
                        from auth.session_manager import is_password_strong
                        is_strong, msg = is_password_strong(new_pwd)
                        if not is_strong:
                            st.error(f"Weak Password: {msg}")
                        else:
                            from database.mongo_manager import update_password
                            if update_password(selected_uid, new_pwd):
                                st.success(f"Successfully reset password for: {selected_uid}")
                                st.rerun()
                            else:
                                st.error("Failed to reset password.")
                                
                elif iam_action == "Delete User":
                    st.error("Warning: This action is permanent and cannot be undone.")
                    if st.button("Delete User", type="primary") and selected_uid:
                        from database.mongo_manager import delete_user
                        if delete_user(selected_uid):
                            st.success(f"Deleted user: {selected_uid}")
                            st.rerun()

    elif nav_selection == "Analytics":
        st.title("System Analytics")
        st.markdown("Track system usage and auditing events.")
        
        from services.audit_service import get_audit_logs_df
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
