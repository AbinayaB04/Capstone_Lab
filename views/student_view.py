import streamlit as st
import os
import requests
from streamlit_lottie import st_lottie
from streamlit_option_menu import option_menu
from auth.session_manager import logout_user, get_auth_headers
from utils.image_utils import get_base64_of_bin_file
from services.llm_service import AIEngine
from database.mongo_manager import get_branches_by_department, get_courses_by_branch_and_sem, get_documents_by_course, get_file_from_gridfs, branches_col, users_col
from bson.objectid import ObjectId

def load_lottieurl(url: str):
    return None

def generate_svg_diagram_card(diagram_text: str, title: str = "Reference Architecture & Schema") -> str:
    """
    Renders ASCII, schema tables, or text diagrams into a high-contrast SVG image card.
    """
    import html
    lines = diagram_text.strip().split("\n")
    max_len = max((len(line) for line in lines), default=40)
    card_width = max(520, min(800, max_len * 9 + 60))
    card_height = max(180, len(lines) * 21 + 75)
    
    escaped_lines = [html.escape(line) for line in lines]
    text_spans = "".join([
        f'<tspan x="24" dy="20">{line}</tspan>' if idx > 0 else f'<tspan x="24" y="65">{line}</tspan>'
        for idx, line in enumerate(escaped_lines)
    ])
    
    grad_id = f"cardGrad_{abs(hash(diagram_text)) % 100000}"
    svg = f"""<svg width="{card_width}" height="{card_height}" viewBox="0 0 {card_width} {card_height}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="{grad_id}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#090d16" />
          <stop offset="100%" stop-color="#111827" />
        </linearGradient>
      </defs>
      <!-- Background Card -->
      <rect width="{card_width}" height="{card_height}" rx="10" fill="url(#{grad_id})" stroke="#2563eb" stroke-width="1.5"/>
      <!-- Window Title Bar -->
      <rect width="{card_width}" height="32" rx="10" fill="#1e293b"/>
      <rect y="22" width="{card_width}" height="10" fill="#1e293b"/>
      <!-- Mac-style status dots -->
      <circle cx="18" cy="16" r="4.5" fill="#ef4444"/>
      <circle cx="34" cy="16" r="4.5" fill="#f59e0b"/>
      <circle cx="50" cy="16" r="4.5" fill="#10b981"/>
      <text x="{card_width // 2}" y="20" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="11" font-weight="600" text-anchor="middle" letter-spacing="0.5">{html.escape(title)}</text>
      <!-- Diagram Content -->
      <text font-family="Courier New, Consolas, Monaco, monospace" font-size="13" font-weight="500" fill="#38bdf8">
        {text_spans}
      </text>
    </svg>"""
    return svg

def render_question_media(q: dict, index: int):
    """
    Renders question visual figures/images using SVG vector graphics,
    valid image URLs, or styled dynamic SVG diagram cards.
    """
    # 1. Direct SVG Vector Graphic
    svg_val = q.get("image_svg")
    if svg_val and isinstance(svg_val, str) and "<svg" in svg_val:
        clean_svg = svg_val[svg_val.find("<svg"):svg_val.rfind("</svg>") + 6]
        st.markdown(
            f"""
            <div style="background:#0b1120; padding:16px; border-radius:10px; border:1.5px solid #2563eb; margin:10px 0; text-align:center; box-shadow:0 4px 12px rgba(0,0,0,0.25);">
                <div style="color:#60a5fa; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;">
                    📐 Figure {index+1}: Reference Architecture / Schema Diagram
                </div>
                <div style="max-width:100%; overflow-x:auto; display:flex; justify-content:center;">
                    {clean_svg}
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        return

    # 2. Web Image URL
    img_val = q.get("image_url")
    if img_val and isinstance(img_val, str) and img_val.startswith(("http://", "https://", "data:image")):
        try:
            st.image(img_val, caption=f"Figure {index+1}: Reference Schematic", use_container_width=True)
            return
        except Exception:
            pass

    # 3. Dynamic SVG Diagram Card from ASCII/Text Diagram
    diagram_val = q.get("diagram")
    if diagram_val and str(diagram_val).strip() and str(diagram_val).lower() != "null":
        svg_card = generate_svg_diagram_card(str(diagram_val).strip(), title=f"Figure {index+1}: Schematic Diagram")
        st.markdown(
            f"""
            <div style="margin:10px 0; display:flex; justify-content:center; max-width:100%; overflow-x:auto;">
                {svg_card}
            </div>
            """,
            unsafe_allow_html=True
        )

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
                            API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8002")
                            requests.put(f"{API_BASE_URL}/chat/sessions/{session_id_str}", json={"title": new_title}, headers=get_auth_headers())
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
                            API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8002")
                            requests.delete(f"{API_BASE_URL}/chat/sessions/{session_id_str}", headers=get_auth_headers())
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
            st.markdown("<div style='font-size: 44px; text-align: right; line-height: 1;'>📘</div>", unsafe_allow_html=True)
        
        st.divider()
        
        user_profile = st.session_state.get("user", {})
        user_dept_id = user_profile.get("department_id")
        user_branch_id = user_profile.get("branch_id")
        user_semester = user_profile.get("semester")
        
        st.subheader("Course Selection")
        col1, col2, col3 = st.columns(3)
        
        is_student = str(user.get("role", "")).lower() == "student"

        # 1. Branch Dropdown
        with col1:
            branches = []
            if user_dept_id:
                try:
                    branches = get_branches_by_department(ObjectId(user_dept_id))
                except:
                    pass
            branch_options = {str(b["_id"]): b["branch_name"] for b in branches}
            
            if is_student and user_branch_id and str(user_branch_id) in branch_options:
                selected_branch_id = st.selectbox(
                    "Branch (🔒 Enrolled)", 
                    options=[str(user_branch_id)], 
                    format_func=lambda x: branch_options.get(x, "Enrolled Branch"),
                    index=0,
                    disabled=True,
                    help="Students are isolated to their registered branch curriculum.",
                    key="student_branch_select"
                )
            else:
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
            
        # 2. Semester (Locked strictly to enrolled semester)
        with col2:
            if is_student:
                enrolled_sem = int(user_semester) if user_semester else 1
                selected_semester = st.selectbox(
                    "Semester (🔒 Enrolled)",
                    options=[enrolled_sem],
                    index=0,
                    disabled=True,
                    help="Students are strictly isolated to their enrolled academic semester.",
                    key="student_sem_select"
                )
            else:
                semesters = list(range(1, 11))
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
        
        # Execution Gate & Tenant Boundary Enforcement
        if not (selected_branch_id and selected_semester and selected_course_code):
            if not course_options:
                st.info(f"ℹ️ **No courses registered for {branch_options.get(str(selected_branch_id), 'this branch')} in Semester {selected_semester}.** If you wish to switch your academic semester for testing, you can update it in **Settings**.")
            else:
                st.warning("Please select a Course to access the AI Engine.")
            return # Halt rendering
            
        if is_student and user_semester and int(selected_semester) != int(user_semester):
            st.error(f"🛑 **Cross-Semester Access Blocked:** You are registered for Semester {user_semester}. Accessing or querying courses from Semester {selected_semester} is strictly forbidden.")
            return

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
                if message.get("sources"):
                    is_web = message.get("source_type") == "internet" or any(s.get("url") for s in message["sources"])
                    exp_title = "🌐 Verified Internet / External Sources" if is_web else "📚 Verified Course Syllabus References"
                    with st.expander(exp_title, expanded=False):
                        for s in message["sources"]:
                            st.markdown(f"**Source:** `{s.get('source', 'Lecture Note')}`")
                            if s.get("url"):
                                st.markdown(f"🔗 [Visit Reference URL]({s['url']})")
                            st.caption(f"{s.get('content', '')}")
                
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
                    API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8002")
                    clean_history = [
                        {"role": m.get("role", "user"), "content": m.get("content", "")}
                        for m in st.session_state.messages[:-1]
                        if isinstance(m, dict) and "content" in m
                    ]
                    payload = {
                        "query": prompt,
                        "department_id": str(user["department_id"]),
                        "branch_id": str(selected_branch_id),
                        "course_code": str(selected_course_code),
                        "semester": int(selected_semester),
                        "chat_history": clean_history,
                        "session_id": st.session_state.get("active_session_id"),
                        "username": user.get("username")
                    }
                    sources = []
                    source_type = "course_material"
                    try:
                        res = requests.post(
                            f"{API_BASE_URL}/chat/query", 
                            json=payload, 
                            headers=get_auth_headers()
                        )
                        if res.status_code == 200:
                            data = res.json()
                            response = data.get("response", "Error generating response.")
                            sources = data.get("sources", [])
                            source_type = data.get("source_type", "course_material")
                        elif res.status_code == 403:
                            try:
                                err_msg = res.json().get("detail", res.text)
                            except Exception:
                                err_msg = res.text
                            response = f"🛑 **Access Forbidden (Semester / Tenant Boundary Violation):**\n\n{err_msg}"
                        else:
                            response = f"API Error: {res.text}"
                    except Exception as e:
                        response = f"API Connection Error: {e}"
                        
                    st.markdown(response)
                    if sources:
                        exp_title = "🌐 Verified Internet / External Sources" if source_type == "internet" or any(s.get("url") for s in sources) else "📚 Verified Course Syllabus References"
                        with st.expander(exp_title, expanded=False):
                            for s in sources:
                                st.markdown(f"**Source:** `{s.get('source', 'Lecture Note')}`")
                                if s.get("url"):
                                    st.markdown(f"🔗 [Visit Reference URL]({s['url']})")
                                st.caption(f"{s.get('content', '')}")
            
            # Add assistant response to chat history
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response, 
                "sources": sources,
                "source_type": source_type
            })
                
    elif nav_selection == "My Courses":
        st.title("My Courses")
        st.markdown("Download course materials and lecture notes uploaded by your staff.")
        
        user_profile = st.session_state.get("user", {})
        user_dept_id = user_profile.get("department_id")
        user_branch_id = user_profile.get("branch_id")
        user_semester = user_profile.get("semester")
        
        is_student = str(user.get("role", "")).lower() == "student"

        col1, col2, col3 = st.columns(3)
        
        with col1:
            branches = []
            if user_dept_id:
                try:
                    branches = get_branches_by_department(ObjectId(user_dept_id))
                except:
                    pass
            branch_options = {str(b["_id"]): b["branch_name"] for b in branches}
            
            if is_student and user_branch_id and str(user_branch_id) in branch_options:
                selected_branch_id = st.selectbox(
                    "Branch (🔒 Enrolled)", 
                    options=[str(user_branch_id)], 
                    format_func=lambda x: branch_options.get(x, "Enrolled Branch"), 
                    index=0, 
                    disabled=True,
                    help="Students are isolated to their registered branch curriculum.",
                    key="mc_branch_select"
                )
            else:
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
            if is_student:
                enrolled_sem = int(user_semester) if user_semester else 1
                selected_semester = st.selectbox(
                    "Semester (🔒 Enrolled)", 
                    options=[enrolled_sem], 
                    index=0, 
                    disabled=True,
                    help="Students are strictly isolated to their enrolled academic semester.",
                    key="mc_sem_select"
                )
            else:
                semesters = list(range(1, 11))
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

        if is_student and user_semester and int(selected_semester) != int(user_semester):
            st.error(f"🛑 **Cross-Semester Access Blocked:** You are registered for Semester {user_semester}. Access to Semester {selected_semester} course materials is forbidden.")
            st.stop()
        
        if selected_course_code:
            course_obj = get_course_by_code(selected_course_code)
            if course_obj and course_obj.get("semester_number") and int(course_obj["semester_number"]) != selected_semester:
                st.error("⛔ Access Forbidden: You cannot access documents outside your enrolled semester.")
            else:
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
        
        is_student = str(user.get("role", "")).lower() == "student"
        
        col1, col2 = st.columns(2)
        
        with col1:
            branches = []
            if user_dept_id:
                try:
                    branches = get_branches_by_department(ObjectId(user_dept_id))
                except:
                    pass
            branch_options = {str(b["_id"]): b["branch_name"] for b in branches}
            
            if is_student and user_branch_id and str(user_branch_id) in branch_options:
                selected_branch_id = st.selectbox(
                    "Branch (🔒 Enrolled)", 
                    options=[str(user_branch_id)], 
                    format_func=lambda x: branch_options.get(x, "Enrolled Branch"), 
                    index=0, 
                    disabled=True,
                    help="Students are isolated to their registered branch curriculum.",
                    key="pe_branch_select"
                )
            else:
                default_branch_index = 0
                if user_branch_id and str(user_branch_id) in branch_options:
                    default_branch_index = list(branch_options.keys()).index(str(user_branch_id))
                selected_branch_id = st.selectbox(
                    "Select Branch", 
                    options=list(branch_options.keys()), 
                    format_func=lambda x: branch_options[x], 
                    index=default_branch_index if branch_options else 0, 
                    key="pe_branch_select"
                )
            
        with col2:
            if is_student:
                enrolled_sem = int(user_semester) if user_semester else 1
                selected_semester = st.selectbox(
                    "Semester (🔒 Enrolled)", 
                    options=[enrolled_sem], 
                    index=0, 
                    disabled=True,
                    help="Students are strictly isolated to their enrolled academic semester.",
                    key="pe_sem_select"
                )
            else:
                semesters = list(range(1, 11))
                default_sem_index = semesters.index(int(user_semester)) if user_semester and int(user_semester) in semesters else 0
                selected_semester = st.selectbox(
                    "Select Semester", 
                    options=semesters, 
                    index=default_sem_index, 
                    key="pe_sem_select"
                )
            
        if is_student and user_semester and int(selected_semester) != int(user_semester):
            st.error(f"🛑 **Cross-Semester Access Blocked:** You are registered for Semester {user_semester}. Access to Semester {selected_semester} practice exams is forbidden.")
            st.stop()

        courses = []
        if selected_branch_id and selected_semester:
            try:
                courses = get_courses_by_branch_and_sem(ObjectId(selected_branch_id), int(selected_semester))
            except:
                pass
        course_options = {c["course_code"]: c["course_name"] for c in courses}
        
        if not course_options:
            st.warning("No courses found for your branch and semester.")
            st.stop()
            
        selected_course = st.selectbox(
            "Select Course to generate quiz:",
            options=list(course_options.keys()),
            format_func=lambda x: f"{x}: {course_options[x]}"
        )

        course_obj = get_course_by_code(selected_course)
        if course_obj and course_obj.get("semester_number") and int(course_obj["semester_number"]) != selected_semester:
            st.error("⛔ Access Forbidden: You cannot generate quizzes for courses outside your enrolled semester.")
            st.stop()

        
        c_opt1, c_opt2 = st.columns(2)
        with c_opt1:
            selected_difficulty = st.selectbox("Exam Difficulty", ["Medium", "Easy", "Hard"], index=0, key="pe_diff_select")
        with c_opt2:
            selected_num_questions = st.selectbox("Number of Questions", [5, 3, 10], index=0, key="pe_num_select")
        
        if st.button("Generate Quiz", type="primary"):
            with st.spinner("Analyzing course materials and generating questions..."):
                import requests
                API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8002")
                try:
                    payload = {
                        "course_code": selected_course,
                        "department_id": str(user_dept_id),
                        "branch_id": str(selected_branch_id),
                        "semester": int(selected_semester),
                        "num_questions": int(selected_num_questions),
                        "difficulty": selected_difficulty.lower()
                    }
                    res = requests.post(
                        f"{API_BASE_URL}/chat/generate-exam", 
                        json=payload, 
                        headers=get_auth_headers(), 
                        timeout=45
                    )
                    if res.status_code == 200:
                        quiz_data = res.json().get("exam")
                    elif res.status_code == 403:
                        quiz_data = None
                        try:
                            err_detail = res.json().get("detail", res.text)
                        except Exception:
                            err_detail = res.text
                        st.error(f"🛑 Access Forbidden: {err_detail}")
                    else:
                        quiz_data = None
                        st.error(f"Failed to generate quiz: {res.text}")
                except Exception as err:
                    quiz_data = None
                    st.error(f"Connection error while contacting server: {err}")

                
                if quiz_data:
                    st.session_state["current_quiz"] = quiz_data
                    st.session_state["quiz_course"] = selected_course
                    st.session_state["quiz_difficulty"] = selected_difficulty
                    st.session_state["quiz_submitted"] = False
                    st.rerun()
                elif res.status_code != 403:
                    st.error("Failed to generate quiz. Please ensure documents are uploaded for this course.")
                    
        if st.session_state.get("current_quiz") and st.session_state.get("quiz_course") == selected_course:
            st.divider()
            quiz = st.session_state["current_quiz"]
            
            with st.form("quiz_form"):
                user_answers = {}
                for i, q in enumerate(quiz):
                    st.markdown(f"**Q{i+1}: {q['question']}**")
                    
                    # Render reference image, SVG graphic, or diagram if provided
                    render_question_media(q, i)
                        
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
                    
                    # Persist attempt to MongoDB
                    from database.mongo_manager import record_quiz_attempt
                    try:
                        record_quiz_attempt(
                            username=user.get("username"),
                            course_code=selected_course,
                            branch_id=selected_branch_id,
                            semester=selected_semester,
                            score=score,
                            total_questions=len(quiz),
                            difficulty=st.session_state.get("quiz_difficulty", "Medium").lower(),
                            user_answers={str(k): v for k, v in user_answers.items()},
                            quiz_details=quiz
                        )
                    except Exception as pe:
                        print(f"Error saving quiz attempt: {pe}")
                    st.rerun()
                    
            if st.session_state.get("quiz_submitted"):
                score = st.session_state['quiz_score']
                total = len(quiz)
                pct = round((score / total) * 100, 1) if total > 0 else 0
                if pct >= 80:
                    st.balloons()
                    st.success(f"### 🎉 Outstanding! Your Score: {score} / {total} ({pct}%)")
                elif pct >= 50:
                    st.info(f"### 👍 Good Effort! Your Score: {score} / {total} ({pct}%)")
                else:
                    st.warning(f"### 📚 Review Suggested: Your Score: {score} / {total} ({pct}%)")
                    
                for i, q in enumerate(quiz):
                    st.markdown(f"**Q{i+1}: {q['question']}**")
                    
                    # Render reference image, SVG graphic, or diagram if provided
                    render_question_media(q, i)
                        
                    user_ans = st.session_state["user_answers"].get(i)
                    correct_ans = q.get('answer')
                    
                    if user_ans == correct_ans:
                        st.write(f"✅ **Your Answer:** {user_ans}")
                    else:
                        st.write(f"❌ **Your Answer:** {user_ans if user_ans else '(Skipped)'}")
                        st.write(f"👉 **Correct Answer:** {correct_ans}")
                    
                    if q.get("explanation"):
                        st.info(f"💡 **Explanation & Concept:** {q['explanation']}")
                    st.write("---")
        
        # --- Past Attempts History Section ---
        st.divider()
        with st.expander("📊 View Past Quiz Attempts & Score Analytics", expanded=False):
            from database.mongo_manager import get_quiz_attempts_by_user
            attempts = get_quiz_attempts_by_user(user.get("username"), selected_course)
            if not attempts:
                st.caption("No previous attempts recorded for this course yet.")
            else:
                import pandas as pd
                hist_data = []
                for att in attempts:
                    t = att.get("timestamp")
                    t_str = t.strftime("%Y-%m-%d %H:%M") if t else "Recent"
                    hist_data.append({
                        "Date": t_str,
                        "Score": f"{att.get('score', 0)}/{att.get('total_questions', 0)}",
                        "Percentage (%)": att.get("percentage", 0),
                        "Difficulty": str(att.get("difficulty", "medium")).capitalize()
                    })
                df_hist = pd.DataFrame(hist_data)
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
                if len(df_hist) > 1:
                    st.caption("Performance Trend:")
                    st.line_chart(df_hist.set_index("Date")["Percentage (%)"])

    elif nav_selection == "Settings":
        st.title("User Settings")
        
        # Academic Profile & Semester Override for Viva / Demonstration
        st.markdown("### 🎓 Academic Profile & Term Management")
        branch_record = branches_col.find_one({"_id": user.get("branch_id")}) if user.get("branch_id") else None
        b_name = branch_record.get("branch_name", "Assigned Branch") if branch_record else "MSc Cyber security"
        current_sem = user.get("semester") or 1

        st.info(
            f"**Roll Number / User ID:** `{user.get('username')}`  \n"
            f"**Student Name:** `{user.get('name')}`  \n"
            f"**Registered Branch:** `{b_name}`  \n"
            f"**Current Registered Semester:** **Semester {current_sem}**  \n\n"
            "🔒 *Curriculum Policy:* Institutional IAM tenant boundary rules strictly restrict access to courses matching your enrolled academic semester."
        )

        with st.expander("🔄 Switch Registered Semester (Viva Demonstration / Evaluation Testing)", expanded=False):
            st.caption("Administrators and examiners can switch the registered semester to test cross-semester isolation enforcement or evaluate specific course syllabi (e.g. Semester 3 Database Design 20XC34 vs. Semester 8 Cloud Security 20XC81).")
            new_test_sem = st.selectbox("Select Target Academic Semester", list(range(1, 11)), index=(current_sem - 1) if current_sem in list(range(1, 11)) else 0, key="switch_sem_select")
            if st.button("Apply Academic Semester", type="primary"):
                from auth.session_manager import create_jwt
                users_col.update_one({"username": user["username"]}, {"$set": {"semester": int(new_test_sem)}})
                st.session_state["user"]["semester"] = int(new_test_sem)
                st.session_state["token"] = create_jwt(st.session_state["user"])
                st.success(f"Academic semester updated to Semester {new_test_sem}! Reloading curriculum...")
                st.rerun()

        st.divider()
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

        st.divider()
        st.markdown("### 🔐 Two-Factor Authentication (2FA / TOTP)")
        from database.mongo_manager import get_user_2fa_secret, enable_user_2fa, disable_user_2fa
        import pyotp
        
        current_secret = get_user_2fa_secret(user.get("username"))
        if current_secret:
            st.success("✅ Two-Factor Authentication is currently **ACTIVE** on your account.")
            if st.button("Disable 2FA", type="secondary"):
                disable_user_2fa(user.get("username"))
                from services.audit_service import log_system_event
                log_system_event(user.get("username"), user.get("role"), "2fa_disabled", "User disabled 2FA")
                st.info("2FA disabled successfully.")
                st.rerun()
        else:
            st.info("Protect your account with Google Authenticator or Microsoft Authenticator.")
            if "temp_2fa_secret" not in st.session_state:
                if st.button("Setup Two-Factor Authentication"):
                    st.session_state["temp_2fa_secret"] = pyotp.random_base32()
                    st.rerun()
            else:
                secret = st.session_state["temp_2fa_secret"]
                st.markdown(f"**Step 1:** Enter this key into your Authenticator app:")
                st.code(secret, language="text")
                st.caption(f"Account: {user.get('username')} | Issuer: StudyMate")
                
                with st.form("verify_2fa_setup_form"):
                    st.markdown("**Step 2:** Enter the 6-digit code shown in your app to activate:")
                    test_code = st.text_input("6-digit TOTP Code", max_chars=6)
                    c_submit, c_cancel = st.columns(2)
                    with c_submit:
                        activate_btn = st.form_submit_button("Activate 2FA", type="primary")
                    with c_cancel:
                        cancel_setup = st.form_submit_button("Cancel")
                        
                    if cancel_setup:
                        del st.session_state["temp_2fa_secret"]
                        st.rerun()
                        
                    if activate_btn:
                        totp = pyotp.TOTP(secret)
                        if totp.verify(test_code.strip(), valid_window=1):
                            enable_user_2fa(user.get("username"), secret)
                            del st.session_state["temp_2fa_secret"]
                            from services.audit_service import log_system_event
                            log_system_event(user.get("username"), user.get("role"), "2fa_enabled", "User enabled 2FA")
                            st.success("Two-Factor Authentication successfully activated!")
                            st.rerun()
                        else:
                            st.error("Invalid verification code. Please make sure your device clock is accurate.")

