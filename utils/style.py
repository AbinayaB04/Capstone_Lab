import streamlit as st

def inject_custom_css():
    """Injects custom CSS for a dark, vibrant glassmorphic UI."""
    css = """
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

        /* Global Font and Background */
        html, body, [class*="css"]  {
            font-family: 'Inter', sans-serif !important;
        }
        
        .stApp {
            background-color: #F9F8F6 !important;
            color: #1F1D1A;
        }

        /* Top Header (Hide Streamlit default) */
        header {visibility: hidden;}
        
        /* Main Container styling */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }

        /* General Text & Labels */
        label, p, .stMarkdown {
            color: #1F1D1A !important;
        }

        /* Custom Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #1F1D1A !important;
            font-weight: 700 !important;
            letter-spacing: -0.5px;
        }
        
        /* Main Accent Headings */
        h1 {
            color: #1F1D1A !important;
        }

        /* Clean Editorial Containers (replaces glassmorphism) */
        [data-testid="stForm"], .glass-container {
            background: #FFFFFF !important;
            border: 1px solid #E5E0D8 !important;
            border-radius: 12px !important;
            padding: 2rem !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03) !important;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background: #F2EFE9 !important;
            border-right: 1px solid #E5E0D8 !important;
        }

        /* Input Fields */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea {
            background: #FFFFFF !important;
            color: #1F1D1A !important;
            border: 1px solid #D1CDC7 !important;
            border-radius: 8px !important;
            transition: all 0.2s ease;
        }
        
        .stTextInput input:focus, .stSelectbox div[data-baseweb="select"] > div:focus, .stTextArea textarea:focus {
            border-color: #D97757 !important;
            box-shadow: 0 0 0 2px rgba(217, 119, 87, 0.15) !important;
        }

        /* Primary Button */
        [data-testid="baseButton-primary"] {
            background: #D97757 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 500 !important;
            transition: background-color 0.2s ease, transform 0.1s ease !important;
        }
        
        [data-testid="baseButton-primary"]:hover {
            background: #C2674A !important;
            transform: translateY(-1px) !important;
            color: #FFFFFF !important;
        }

        /* Secondary Button */
        button[kind="secondary"], [data-testid="baseButton-secondary"] {
            background: #FFFFFF !important;
            color: #1F1D1A !important;
            border: 1px solid #D1CDC7 !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }
        
        button[kind="secondary"]:hover, [data-testid="baseButton-secondary"]:hover {
            background: #F9F8F6 !important;
            border-color: #D97757 !important;
            color: #D97757 !important;
            transform: translateY(-1px) !important;
        }
        
        /* Divider Styling */
        hr {
            border-top: 1px solid #E5E0D8 !important;
        }

        /* --- CUSTOM SIDEBAR BEHAVIOR --- */
        /* Hide Streamlit's native collapse button so we can use our custom toggle */
        [data-testid="collapsedControl"] { display: none !important; }
        [data-testid="stSidebarCollapseButton"] { display: none !important; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
