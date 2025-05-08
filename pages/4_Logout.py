import streamlit as st
import streamlit_survey as ss
from tracking.logging import log_chat_interaction
from streamlit_extras.switch_page_button import switch_page

def show_logout_survey():
    if "user_id" not in st.session_state or st.session_state.user_id is None:
        st.switch_page("pages/1_Login.py")
        return

    st.set_page_config(
        page_title="PromptDoctor - Logout",
        page_icon="👋"
    )

    st.header("Feedback Before You Go")

    # Initialize the survey
    survey = ss.StreamlitSurvey("Logout Survey")

    # Create a survey page
    with survey.pages(1)[0]:
        satisfaction = survey.slider(
            "How satisfied were you with the system?",
            min_value=1,
            max_value=5,
            value=3,
            help="1 = Not satisfied at all, 5 = Very satisfied"
        )

        feedback = survey.text_area(
            "Any additional feedback?",
            placeholder="Please share your thoughts about the system...",
            key="feedback"
        )

        if st.button("Complete Logout"):
            # Log logout survey
            log_chat_interaction(
                st.session_state.user_id,
                "LOGOUT_SURVEY",
                additional_data={
                    "satisfaction": satisfaction,
                    "feedback": feedback
                }
            )
            
            # Clear session state and switch to login
            st.session_state.clear()
            st.switch_page("pages/1_Login.py")

show_logout_survey()