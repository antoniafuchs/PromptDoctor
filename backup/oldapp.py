import streamlit as st

# Page config must be first Streamlit command
st.set_page_config(page_title="PromptDoctor", layout="wide")

# Initialize session state variables
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"

# Import pages
from pages.login import show_login_page
from pages.login_survey import show_login_survey
from pages.chatbot import show_chatbot
from pages.logout_survey import show_logout_survey

# Route to correct page based on session state
if st.session_state.current_page == "login":
    show_login_page()
elif st.session_state.current_page == "login_survey":
    show_login_survey()
elif st.session_state.current_page == "chatbot":
    show_chatbot()
elif st.session_state.current_page == "logout_survey":
    show_logout_survey()
