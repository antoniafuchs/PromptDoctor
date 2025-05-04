import streamlit as st
import streamlit_survey as ss
from tracking.logging import log_chat_interaction
from utils.model_handler import ModelHandler
from streamlit_extras.switch_page_button import switch_page

def show_login_survey():
    if "user_id" not in st.session_state or st.session_state.user_id is None:
        switch_page("Login")
        return
        
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
        if experience and role:  # Check if both fields are filled
            # Log survey responses
            log_chat_interaction(
                st.session_state.user_id,
                "SURVEY_COMPLETE",
                additional_data={"experience": experience, "role": role}
            )
            
            if st.session_state.selected_model_type == "HuggingFace":
                st.warning("Note: First response may take a while as the model is being loaded.")
            
            switch_page("Chatbot")
            
        else:
            st.error("Please complete all fields before continuing.")

show_login_survey()
