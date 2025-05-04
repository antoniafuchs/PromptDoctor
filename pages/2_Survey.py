import streamlit as st
import streamlit_survey as ss
from tracking.logging import log_chat_interaction
from utils.model_handler import ModelHandler

def show_login_survey():
    if "user_id" not in st.session_state or st.session_state.user_id is None:
        st.switch_page("pages/Login")
        return
        
    st.set_page_config(page_title="PromptDoctor - Survey", page_icon="📋")
    st.header("Quick Survey")

    # Initialize model handler if not done
    if "model_handler" not in st.session_state:
        st.session_state.model_handler = ModelHandler()
        st.session_state.model_handler.initialize_model(
            st.session_state.selected_model_type,
            st.session_state.selected_model_name
        )

    # Initialize the survey
    survey = ss.StreamlitSurvey("Survey")

    survey.radio("Thumbs up/down:", options=["NA", "👍", "👎"], horizontal=True)

    if st.button("Continue to App"):
        
            
        if st.session_state.selected_model_type == "HuggingFace":
            st.warning("Note: First response may take a while as the model is being loaded.")
        
        st.switch_page("pages/3_Chat.py")

show_login_survey()