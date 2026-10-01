import streamlit as st
import os
from streamlit_option_menu import option_menu
from auth.session_manager import logout_user
from utils.image_utils import get_base64_of_bin_file
import threading
import uuid

# Define a global dictionary across sessions (since streamlit session state is per-user)
# In a real app, you'd use a database or Redis, but this works for demonstration.
if "ingestion_tasks" not in st.session_state:
    st.session_state.ingestion_tasks = {}

def _process_upload_in_background(task_id, file_bytes, filename, user_dept_id, selected_branch_id, selected_semester, selected_course_code, uploader_username, role):
    try:
        from database.mongo_manager import fs, add_document_record
        from services.audit_service import log_document_access
        from utils.pdf_utils import extract_and_chunk_pdf
        from database.vector_manager import insert_document_chunk
        
        file_id = fs.put(
            file_bytes, 
            filename=filename, 
            department_id=str(user_dept_id), 
            branch_id=str(selected_branch_id), 
            semester=int(selected_semester), 
            course_code=str(selected_course_code)
        )
        
        add_document_record(
            filename=filename,
            gridfs_id=file_id,
            course_code=str(selected_course_code),
            uploader_username=uploader_username,
            department_id=str(user_dept_id),
            branch_id=str(selected_branch_id),
            semester=int(selected_semester)
        )
        
        log_document_access(uploader_username, role, filename, "upload")
        
        chunks = extract_and_chunk_pdf(file_bytes, filename=filename)
        for i, (chunk, source) in enumerate(chunks):
            chunk_id = f"{file_id}_chunk_{i}"
            metadata = {
                "department_id": str(user_dept_id),
                "branch_id": str(selected_branch_id),
                "semester": int(selected_semester),
                "course_code": str(selected_course_code),
                "source": source,
                "file_id": str(file_id)
            }
            insert_document_chunk(chunk_id, chunk, metadata)
            
        st.session_state.ingestion_tasks[task_id] = "Completed"
    except Exception as e:
        print(f"Background upload error: {e}")
        st.session_state.ingestion_tasks[task_id] = f"Failed: {str(e)}"
from services.llm_service import AIEngine
from database.mongo_manager import fs, get_branches_by_department, get_courses_by_branch_and_sem, add_document_record
from database.vector_manager import insert_document_chunk
from utils.pdf_utils import extract_and_chunk_pdf
from bson.objectid import ObjectId
import uuid

def render_staff_view():
    user = st.session_state.get("user", {})
    from auth.rbac_manager import RBACManager
    if not RBACManager.has_permission(user.get("role"), "upload_materials"):
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
        
        st.sidebar.markdown(f"<div style='margin-bottom: 10px; margin-top: 15px; padding-left: 10px; color: #6C665F; font-size: 13px;'><strong>👨‍🏫 Staff:</strong> {user.get('username')}</div>", unsafe_allow_html=True)
        
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
            options=["Upload Materials", "Search Engine", "Settings"],
            icons=["cloud-upload", "search", "gear"], 
            default_index=0,
            styles=menu_styles
        )

    # --- Main Area Content ---
    user_profile = st.session_state.get("user", {})
    user_dept_id = user_profile.get("department_id")
    
    st.subheader("Target Context Selection")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        branches = []
        if user_dept_id:
            try:
                branches = get_branches_by_department(ObjectId(user_dept_id))
            except:
                pass
        branch_options = {str(b["_id"]): b["branch_name"] for b in branches}
        
        selected_branch_id = st.selectbox(
            "Select Branch", 
            options=list(branch_options.keys()), 
            format_func=lambda x: branch_options[x],
            key="staff_branch_select"
        )
        
    with col2:
        selected_semester = st.selectbox(
            "Select Semester",
            options=[1, 2, 3, 4, 5, 6, 7, 8],
            key="staff_sem_select"
        )
        
    with col3:
        courses = []
        if selected_branch_id and selected_semester:
            try:
                courses = get_courses_by_branch_and_sem(ObjectId(selected_branch_id), int(selected_semester))
            except:
                courses = []
                
        course_options = {c["course_code"]: c["course_name"] for c in courses}
        
        selected_course_code = st.selectbox(
            "Select Course",
            options=list(course_options.keys()),
            format_func=lambda x: f"{x}: {course_options[x]}",
            key="staff_course_select"
        )
        
    st.divider()
    
    if not (selected_branch_id and selected_semester and selected_course_code):
        st.warning("Please select a Branch, Semester, and Course before proceeding.")
        return # Execution Gate
    
    if nav_selection == "Upload Materials":
        st.title("Upload Course Materials")
        st.markdown(f"Upload syllabi, lecture notes, and study guides for **{course_options.get(selected_course_code, '')}**. These documents will be processed and added to the AI's knowledge base for your students.")
        
        uploaded_files = st.file_uploader("Upload PDF Documents", type=["pdf"], accept_multiple_files=True)
        
        if st.button("Upload to Knowledge Base", type="primary"):
            if uploaded_files:
                    import requests
                    API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
                    
                    files_to_upload = [('files', (f.name, f.getvalue(), 'application/pdf')) for f in uploaded_files]
                    data = {
                        "user_dept_id": str(user_dept_id),
                        "selected_branch_id": str(selected_branch_id),
                        "selected_semester": str(selected_semester),
                        "selected_course_code": str(selected_course_code),
                        "uploader_username": user_profile.get("username", "unknown"),
                        "role": user_profile.get("role", "staff")
                    }
                    try:
                        res = requests.post(f"{API_BASE_URL}/documents/upload", files=files_to_upload, data=data)
                        if res.status_code == 200:
                            st.success(f"Queued {len(uploaded_files)} document(s) for background processing!")
                        else:
                            st.error(f"Failed to upload: {res.text}")
                    except Exception as e:
                        st.error(f"API Connection Error: {e}")
            else:
                st.warning("Please upload at least one file.")
                
        # Display background tasks status
        st.divider()
        st.subheader("Background Tasks")
        if not st.session_state.ingestion_tasks:
            st.info("No active or recent background tasks.")
        else:
            for tid, status in st.session_state.ingestion_tasks.items():
                if status == "Completed":
                    st.success(f"Task {tid[:8]}: {status}")
                elif status.startswith("Failed"):
                    st.error(f"Task {tid[:8]}: {status}")
                else:
                    st.info(f"Task {tid[:8]}: {status} 🔄")
                    
        # Document Management
        st.divider()
        st.subheader("Manage Existing Documents")
        import requests
        API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
        docs = []
        try:
            res = requests.get(f"{API_BASE_URL}/documents/course/{selected_course_code}")
            if res.status_code == 200:
                docs = res.json().get("documents", [])
        except:
            pass
            
        if not docs:
            st.info("No documents uploaded for this course yet.")
        else:
            for doc in docs:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"📄 **{doc['filename']}** (Uploaded: {doc.get('upload_date', 'Unknown')})")
                with col2:
                    if st.button("Delete", key=f"del_{doc['_id']}"):
                        try:
                            del_res = requests.delete(f"{API_BASE_URL}/documents/{doc['_id']}")
                            if del_res.status_code == 200:
                                st.success(f"Deleted {doc['filename']}")
                                st.rerun()
                            else:
                                st.error("Failed to delete document.")
                        except Exception as e:
                            st.error(f"API Error: {e}")
                
    elif nav_selection == "Search Engine":
        st.title("AI Query Engine (Staff Preview)")
        st.markdown("Test the AI Query Engine to see how it responds to student questions based on your materials.")
        
        # Initialize the AI Engine in session state
        if "ai_engine" not in st.session_state:
            st.session_state.ai_engine = AIEngine()
            
        # Initialize chat history for staff
        if "staff_messages" not in st.session_state:
            st.session_state.staff_messages = []
            
        # Display chat messages from history
        for message in st.session_state.staff_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        # React to user input
        if prompt := st.chat_input("Test a student query here..."):
            st.chat_message("user").markdown(prompt)
            st.session_state.staff_messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = st.session_state.ai_engine.generate_response(
                        prompt, 
                        chat_history=st.session_state.staff_messages[:-1],
                        branch_id=str(selected_branch_id),
                        course_code=str(selected_course_code)
                    )
                    st.markdown(response)
            
            st.session_state.staff_messages.append({"role": "assistant", "content": response})

    elif nav_selection == "Settings":
        st.title("User Settings")
        
        st.markdown("### Change Password")
        with st.form("change_password_form"):
            old_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            submit = st.form_submit_button("Update Password", type="primary")
            if submit:
                if not old_password or not new_password or not confirm_password:
                    st.error("All fields are required.")
                elif new_password != confirm_password:
                    st.error("New passwords do not match.")
                else:
                    from auth.session_manager import is_password_strong
                    is_strong, msg = is_password_strong(new_password)
                    if not is_strong:
                        st.error(f"Weak Password: {msg}")
                    else:
                        from database.mongo_manager import verify_login, update_password
                        success, _ = verify_login(user["username"], old_password)
                        if not success:
                            st.error("Current password is incorrect.")
                        else:
                            if update_password(user["username"], new_password):
                                from services.audit_service import log_system_event
                                log_system_event(user["username"], user["role"], "password_change", "User updated password")
                                st.success("Password updated successfully!")
                            else:
                                st.error("An error occurred while updating the password.")
