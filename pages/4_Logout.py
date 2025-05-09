import streamlit as st
import streamlit_survey as ss
from tracking.logging import log_chat_interaction
from streamlit_extras.switch_page_button import switch_page
import pyperclip
import time
from utils.survey_storage import SurveyStorage
import datetime
from utils.data_merger import DataMerger
from utils.session_manager import SessionManager

def show_logout_survey():
    if not SessionManager.get_session_id():
        st.switch_page("pages/1_Login.py")
        return

    st.set_page_config(
        page_title="PromptDoctor",
        initial_sidebar_state="collapsed"  # Start with sidebar collapsed
    )

    # Hide sidebar and center content
    st.markdown("""
        <style>
            [data-testid="collapsedControl"] {display: none;}
            section[data-testid="stSidebar"] {display: none;}
            .main > div {
                max-width: 48rem;
                margin: auto;
                padding: 2rem;
            }
        </style>
    """, unsafe_allow_html=True)

    if "logged_out" not in st.session_state:
        st.session_state.logged_out = False

    st.header("Thanks for Completing All Tasks!")

    # Show only goodbye messages if logged out
    if st.session_state.logged_out:
        st.success("Thank you for your feedback! You can now close this window.")
        st.info("Your responses have been saved. You can close this window.")
        return

    # Show survey if not logged out
    st.subheader("Please share your feedback before leaving")
    survey_link = "https://forms.gle/your-survey-link"

    col1, col2 = st.columns([3, 1])
    with col1:
        st.text_input("External survey link", value=survey_link, disabled=True)
    with col2:
        if st.button("Copy Link"):
            st.write("Link copied! 📋")
            pyperclip.copy(survey_link)

    satisfaction = st.slider(
        "Overall satisfaction with the system",
        min_value=1,
        max_value=5,
        value=3,
        help="1 = Not satisfied at all, 5 = Very satisfied"
    )

    feedback = st.text_area(
        "Additional feedback",
        placeholder="Please share your thoughts about the system...",
    )

    if st.button("Submit & Logout", type="primary"):
        # Save all data first
        login_time = datetime.datetime.fromisoformat(st.session_state.login_time)
        logout_time = datetime.datetime.now()
        survey_duration = (logout_time - login_time).total_seconds()
        
        survey_data = {
            "satisfaction": satisfaction,
            "feedback": feedback,
            "tasks_completed": len([t for t in st.session_state.task_states if t.completed]),
            "survey_duration_seconds": survey_duration,
            "login_time": st.session_state.login_time,
            "logout_time": logout_time.isoformat(),
            "group": st.session_state.get('group', 'unknown')
        }
        
        # Save all the data
        survey_storage = SurveyStorage()
        survey_storage.save_logout_survey(st.session_state.user_id, survey_data)
        
        data_merger = DataMerger()
        merged_file = data_merger.merge_all_data()
        
        if merged_file:
            stats = data_merger.generate_summary_stats(merged_file)
            print(f"[INFO] Data merged successfully. Stats: {stats}")

        log_chat_interaction(
            st.session_state.user_id,
            "FINAL_SURVEY",
            additional_data=survey_data
        )
        
        # Set logged_out state and clear session
        st.session_state.logged_out = True
        st.rerun()
        SessionManager.clear_session()
        

show_logout_survey()