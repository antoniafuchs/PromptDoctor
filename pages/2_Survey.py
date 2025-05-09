import streamlit as st
import streamlit_survey as ss
from tracking.logging import log_chat_interaction
from utils.model_handler import ModelHandler

def show_login_survey():
    if "user_id" not in st.session_state or st.session_state.user_id is None:
        st.switch_page("pages/Login")
        return
        
    st.set_page_config(page_title="PromptDoctor")
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

    # Collect basic information
    experience = survey.radio(
        "How much experience do you have with medical AI tools?",
        options=["None", "Some", "Moderate", "Extensive"],
        index=0
    )

    role = survey.radio(
        "What is your primary role?",
        options=["Medical Student", "Resident", "Physician", "Specialist", "Other"],
        index=0
    )

    if st.button("Continue to App"):
        # Log survey responses
        log_chat_interaction(
            st.session_state.user_id,
            "SURVEY_COMPLETE",
            additional_data={
                "experience": experience,
                "role": role,
                "group": st.session_state.get('group', 'unknown')  # Add fallback
            }
        )
        
        # Route to appropriate chat page based on group
        if st.session_state.group == "A":
            st.switch_page("pages/3_Chat_base.py")
        else:
            st.switch_page("pages/3_Chat.py")

show_login_survey()