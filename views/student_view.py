import streamlit as st
import os
import requests
from streamlit_lottie import st_lottie
from streamlit_option_menu import option_menu
from auth.session_manager import logout_user
from utils.image_utils import get_base64_of_bin_file
from services.llm_service import AIEngine
from database.mongo_manager import get_branches_by_department, get_courses_by_branch_and_sem, get_documents_by_course, get_file_from_gridfs
from bson.objectid import ObjectId

def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

def render_student_view():
    user = st.session_state.get("user", {})
    
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
        
        st.sidebar.markdown(f"<div style='margin-bottom: 10px; margin-top: 15px; padding-left: 10px; color: #6C665F; font-size: 13px;'><strong>👤 Student:</strong> {user.get('username')}</div>", unsafe_allow_html=True)
        
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
            options=["Home", "My Courses", "Practice Exams", "Settings"],
            icons=["house", "book", "journal-check", "gear"], 
            default_index=0,
            styles=menu_styles
        )
        
        if not st.session_state.mini_menu and nav_selection == "Home":
            st.divider()
            
            if st.button("➕ New Chat", use_container_width=True, type="primary"):
                st.session_state["active_session_id"] = None
                st.session_state["messages"] = []
                st.rerun()
                
            st.markdown("### 💬 Recent Chats")
            from database.mongo_manager import get_chat_sessions_by_user
            sessions = get_chat_sessions_by_user(user.get("username"))
            
            for session in sessions:
                title = session.get("title", "New Chat")
                session_id_str = str(session["_id"])
                
                if st.session_state.get(f"edit_{session_id_str}"):
                    new_title = st.text_input("Rename", value=title, key=f"input_{session_id_str}", label_visibility="collapsed")
                    c_save, c_cancel = st.columns(2)
                    with c_save:
                        if st.button("Save", key=f"save_{session_id_str}", use_container_width=True):
                            import requests
                            API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
                            requests.put(f"{API_BASE_URL}/chat/sessions/{session_id_str}", json={"title": new_title})
                            st.session_state[f"edit_{session_id_str}"] = False
                            st.rerun()
                    with c_cancel:
                        if st.button("Cancel", key=f"cancel_{session_id_str}", use_container_width=True):
                            st.session_state[f"edit_{session_id_str}"] = False
                            st.rerun()
                else:
                    btn_type = "primary" if st.session_state.get("active_session_id") == session_id_str else "secondary"
                    sc1, sc2, sc3 = st.columns([5, 2, 2])
                    with sc1:
                        if st.button(title, key=f"sess_{session_id_str}", use_container_width=True, type=btn_type):
                            st.session_state["active_session_id"] = session_id_str
                            st.session_state["messages"] = session.get("messages", [])
                            st.rerun()
                    with sc2:
                        if st.button("Edit", key=f"edit_btn_{session_id_str}", use_container_width=True, help="Rename Chat"):
                            st.session_state[f"edit_{session_id_str}"] = True
                            st.rerun()
                    with sc3:
                        if st.button("Del", key=f"del_btn_{session_id_str}", use_container_width=True, help="Delete Chat"):
                            import requests
                            API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
                            requests.delete(f"{API_BASE_URL}/chat/sessions/{session_id_str}")
                            if st.session_state.get("active_session_id") == session_id_str:
                                st.session_state["active_session_id"] = None
                                st.session_state["messages"] = []
                            st.rerun()

    # --- Main Area Content ---
    if nav_selection == "Home":
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title("Student Portal")
            st.markdown("Welcome to the AI Exam Preparation Engine.")
        with col2:
            lottie_ai = load_lottieurl("https://assets8.lottiefiles.com/packages/lf20_ujdjtzqt.json")
            if lottie_ai:
                st_lottie(lottie_ai, height=100, key="ai_anim")
        
        st.divider()
        
        user_profile = st.session_state.get("user", {})
        user_dept_id = user_profile.get("department_id")
        user_branch_id = user_profile.get("branch_id")
        user_semester = user_profile.get("semester")
        
        st.subheader("Course Selection")
        col1, col2, col3 = st.columns(3)
        
        # 1. Branch Dropdown
        with col1:
            branches = []
            if user_dept_id:
                try:
                    branches = get_branches_by_department(ObjectId(user_dept_id))
                except:
                    pass
            branch_options = {str(b["_id"]): b["branch_name"] for b in branches}
            
            default_branch_index = 0
            if user_branch_id and str(user_branch_id) in branch_options:
                default_branch_index = list(branch_options.keys()).index(str(user_branch_id))
            
            selected_branch_id = st.selectbox(
                "Select Branch", 
                options=list(branch_options.keys()), 
                format_func=lambda x: branch_options[x],
                index=default_branch_index if branch_options else 0,
                key="student_branch_select"
            )
            
        # 2. Semester Dropdown
        with col2:
            semesters = [1, 2, 3, 4, 5, 6, 7, 8]
            default_sem_index = semesters.index(user_semester) if user_semester in semesters else 0
            
            selected_semester = st.selectbox(
                "Select Semester",
                options=semesters,
                index=default_sem_index,
                key="student_sem_select"
            )
            
        # 3. Course Dropdown
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
                key="student_course_select"
            )
            
        st.divider()
        
        # Execution Gate
        if not (selected_branch_id and selected_semester and selected_course_code):
            st.warning("Please select a Branch, Semester, and Course to access the AI Engine.")
            return # Halt rendering
            
        # Store active context
        st.session_state["active_course_context"] = selected_course_code
        
        st.subheader("AI Query Engine")
        st.markdown(f"Ask anything related to **{course_options.get(selected_course_code, '')}**.")
        
        # Initialize the AI Engine in session state
        if "ai_engine" not in st.session_state:
            st.session_state.ai_engine = AIEngine()
            
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        # React to user input
        if prompt := st.chat_input("What do you want to learn today?"):
            from database.mongo_manager import create_chat_session, add_message_to_session
            
            # If no active session, create one
            if not st.session_state.get("active_session_id"):
                title = prompt[:30] + "..." if len(prompt) > 30 else prompt
                new_session_id = create_chat_session(
                    username=user.get("username"),
                    course_code=str(selected_course_code),
                    branch_id=str(selected_branch_id),
                    semester=int(selected_semester),
                    title=title
                )
                st.session_state["active_session_id"] = new_session_id
                
            add_message_to_session(st.session_state["active_session_id"], "user", prompt)
            
            # Display user message in chat message container
            st.chat_message("user").markdown(prompt)
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})

            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # Generate response
                    from services.audit_service import log_document_access
                    log_document_access(st.session_state.get("user", {}).get("username", "unknown"), st.session_state.get("user", {}).get("role", "student"), selected_course_code, "ai_query")
                    # Pass history excluding the newly added prompt
                    import requests
                    API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
                    payload = {
                        "query": prompt,
                        "department_id": str(user["department_id"]),
                        "branch_id": str(selected_branch_id),
                        "course_code": str(selected_course_code),
                        "chat_history": st.session_state.messages[:-1],
                        "session_id": st.session_state.get("active_session_id"),
                        "username": user.get("username")
                    }
                    try:
                        res = requests.post(f"{API_BASE_URL}/chat/query", json=payload)
                        if res.status_code == 200:
                            response = res.json().get("response", "Error generating response.")
                        else:
                            response = f"API Error: {res.text}"
                    except Exception as e:
                        response = f"API Connection Error: {e}"
                        
                    st.markdown(response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})
                
    elif nav_selection == "My Courses":
        st.title("My Courses")
        st.markdown("Download course materials and lecture notes uploaded by your staff.")
        
        user_profile = st.session_state.get("user", {})
        user_dept_id = user_profile.get("department_id")
        user_branch_id = user_profile.get("branch_id")
        user_semester = user_profile.get("semester")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            branches = []
            if user_dept_id:
                try:
                    branches = get_branches_by_department(ObjectId(user_dept_id))
                except:
                    pass
            branch_options = {str(b["_id"]): b["branch_name"] for b in branches}
            default_branch_index = 0
            if user_branch_id and str(user_branch_id) in branch_options:
                default_branch_index = list(branch_options.keys()).index(str(user_branch_id))
            
            selected_branch_id = st.selectbox(
                "Select Branch", 
                options=list(branch_options.keys()), 
                format_func=lambda x: branch_options[x], 
                index=default_branch_index if branch_options else 0, 
                key="mc_branch_select"
            )
            
        with col2:
            semesters = [1, 2, 3, 4, 5, 6, 7, 8]
            default_sem_index = semesters.index(user_semester) if user_semester in semesters else 0
            selected_semester = st.selectbox(
                "Select Semester", 
                options=semesters, 
                index=default_sem_index, 
                key="mc_sem_select"
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
                key="mc_course_select"
            )
            
        st.divider()
        
        if selected_course_code:
            docs = get_documents_by_course(selected_course_code)
            if not docs:
                st.info("No documents have been uploaded for this course yet.")
            else:
                for doc in docs:
                    with st.container():
                        col_doc1, col_doc2 = st.columns([4, 1])
                        with col_doc1:
                            st.markdown(f"📄 **{doc['filename']}**")
                            upload_date = doc.get('upload_date')
                            date_str = upload_date.strftime("%Y-%m-%d %H:%M") if upload_date else "Unknown"
                            st.caption(f"Uploaded by: {doc.get('uploader_username', 'Staff')} | Date: {date_str}")
                        with col_doc2:
                            file_data = get_file_from_gridfs(doc['gridfs_id'])
                            if file_data:
                                st.download_button(
                                    label="Download",
                                    data=file_data,
                                    file_name=doc['filename'],
                                    mime="application/octet-stream",
                                    key=f"dl_{doc['_id']}"
                                )
                        st.markdown("---")
        
    elif nav_selection == "Practice Exams":
        st.title("AI Practice Exams")
        st.markdown("Test your knowledge with an AI-generated quiz based on your course syllabus.")
        
        user_profile = st.session_state.get("user", {})
        user_dept_id = user_profile.get("department_id")
        user_branch_id = user_profile.get("branch_id")
        user_semester = user_profile.get("semester")
        
        courses = []
        if user_branch_id and user_semester:
            try:
                courses = get_courses_by_branch_and_sem(ObjectId(user_branch_id), int(user_semester))
            except:
                pass
        course_options = {c["course_code"]: c["course_name"] for c in courses}
        
        if not course_options:
            st.warning("No courses found for your branch and semester.")
            st.stop()
            
        selected_course = st.selectbox(
            "Select Course to generate quiz:",
            options=list(course_options.keys()),
            format_func=lambda x: course_options[x]
        )

        
        if st.button("Generate Quiz", type="primary"):
            with st.spinner("Analyzing course materials and generating questions..."):
                import requests
                API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
                try:
                    payload = {
                        "course_code": selected_course,
                        "department_id": str(user_dept_id),
                        "branch_id": str(user_branch_id)
                    }
                    res = requests.post(f"{API_BASE_URL}/chat/generate-exam", json=payload)
                    if res.status_code == 200:
                        quiz_data = res.json().get("exam")
                    else:
                        quiz_data = None
                except:
                    quiz_data = None
                
                if quiz_data:
                    st.session_state["current_quiz"] = quiz_data
                    st.session_state["quiz_course"] = selected_course
                    st.session_state["quiz_submitted"] = False
                    st.rerun()
                else:
                    st.error("Failed to generate quiz. Please ensure documents are uploaded for this course.")
                    
        if st.session_state.get("current_quiz") and st.session_state.get("quiz_course") == selected_course:
            st.divider()
            quiz = st.session_state["current_quiz"]
            
            with st.form("quiz_form"):
                user_answers = {}
                for i, q in enumerate(quiz):
                    st.markdown(f"**Q{i+1}: {q['question']}**")
                    # Use index=None to ensure no default option is selected
                    user_answers[i] = st.radio(f"Options for Q{i+1}", q.get('options', []), key=f"q_{i}", index=None, label_visibility="collapsed")
                    st.write("")
                    
                submitted = st.form_submit_button("Submit Exam", type="primary")
                
                if submitted:
                    st.session_state["quiz_submitted"] = True
                    score = 0
                    for i, q in enumerate(quiz):
                        if user_answers[i] == q.get('answer'):
                            score += 1
                    st.session_state["quiz_score"] = score
                    st.session_state["user_answers"] = user_answers
                    st.rerun()
                    
            if st.session_state.get("quiz_submitted"):
                st.success(f"### Your Score: {st.session_state['quiz_score']} / {len(quiz)}")
                for i, q in enumerate(quiz):
                    st.markdown(f"**Q{i+1}: {q['question']}**")
                    user_ans = st.session_state["user_answers"].get(i)
                    correct_ans = q.get('answer')
                    
                    if user_ans == correct_ans:
                        st.write(f"✅ **You answered:** {user_ans}")
                    else:
                        st.write(f"❌ **You answered:** {user_ans if user_ans else '(Skipped)'}")
                        st.write(f"👉 **Correct answer:** {correct_ans}")
                    st.write("---")
        
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
