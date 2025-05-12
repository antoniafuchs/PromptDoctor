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

    # Initialize survey with multiple pages
    survey = ss.StreamlitSurvey("LogoutSurvey")
    total_pages = 3 if st.session_state.get('group') != 'B' else 4
    pages = survey.pages(total_pages)
    
    st.progress((pages.current + 1) / total_pages, 
                text=f"Page {pages.current + 1} of {total_pages}")
    
    # Initialize session state for survey responses if not exists
    if "logout_survey_data" not in st.session_state:
        st.session_state.logout_survey_data = {}

    # Survey content for each page
    if pages.current == 0:
        st.write("#### Section A: Overall Usability")
        st.write("Scale: 1 = Strongly Disagree, 5 = Strongly Agree")
        
        st.session_state.logout_survey_data['q1a_ease'] = survey.radio(
            "The tool was easy to use.",
            options=["1 - Strongly Disagree", "2 - Somewhat Disagree", "3 - Neutral", "4 - Somewhat Agree", "5 - Strongly Agree"],
            horizontal=True
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q1b_clarity'] = survey.radio(
            "The instructions were clear.",
            options=["1 - Strongly Disagree", "2 - Somewhat Disagree", "3 - Neutral", "4 - Somewhat Agree", "5 - Strongly Agree"],
            horizontal=True
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q1c_reuse'] = survey.radio(
            "I would use this tool again for similar tasks.",
            options=["1 - Strongly Disagree", "2 - Somewhat Disagree", "3 - Neutral", "4 - Somewhat Agree", "5 - Strongly Agree"],
            horizontal=True
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q1d_prior_exp'] = survey.radio(
            "How much did your prior experience with AI or prompt engineering help you in using the tool?",
            options=["1 - Not helpful at all", "2 - Slightly helpful", "3 - Moderately helpful", "4 - Very helpful", "5 - Extremely helpful"],
            horizontal=True
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q1e_exp_affect'] = survey.radio(
            "Did your experience in prompt engineering affect prompt quality?",
            options=["Yes", "No"],
            horizontal=True
        )
        
        if st.session_state.logout_survey_data['q1e_exp_affect'] == "Yes":
            st.session_state.logout_survey_data['q1f_exp_how'] = survey.text_area(
                "In what way did your experience influence the prompts?",
                placeholder="Please explain..."
            )
        
        st.session_state.logout_survey_data['q1g_understanding'] = survey.radio(
            "How much did the tool improve your understanding of prompt engineering?",
            options=["1 - Not at all", "2 - Somewhat", "3 - Neutral", "4 - Significantly", "5 - Extremely"],
            horizontal=True
        ).split(" - ")[0]

    elif pages.current == 1:
        st.write("#### Section B: Trust and Understanding")
        st.write("Scale: 1 = Strongly Disagree, 5 = Strongly Agree")
        
        st.session_state.logout_survey_data['q2a_trust'] = survey.radio(
            "I trust the final outputs from the model.",
            options=["1 - Strongly Disagree", "2 - Somewhat Disagree", "3 - Neutral", "4 - Somewhat Agree", "5 - Strongly Agree"],
            horizontal=True
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q2b_understanding'] = survey.radio(
            "I understood why the model gave certain answers.",
            options=["1 - Strongly Disagree", "2 - Somewhat Disagree", "3 - Neutral", "4 - Somewhat Agree", "5 - Strongly Agree"],
            horizontal=True
        ).split(" - ")[0]
        
        if st.session_state.get('group') == 'B':
            st.session_state.logout_survey_data['q2c_explanations'] = survey.radio(
                "The explanations helped build trust in the model.",
                options=["1 - Strongly Disagree", "2 - Somewhat Disagree", "3 - Neutral", "4 - Somewhat Agree", "5 - Strongly Agree"],
                horizontal=True
            ).split(" - ")[0]

    elif pages.current == 2:
        st.write("#### Section C: Open Feedback")
        
        st.session_state.logout_survey_data['q3a_likes'] = survey.text_area(
            "What did you like most about the tool?",
            height=100
        )
        
        st.session_state.logout_survey_data['q3b_improvements'] = survey.text_area(
            "What would you change or improve?",
            height=100
        )
        
        st.session_state.logout_survey_data['q3c_clinical'] = survey.text_area(
            "Would you use such a tool in clinical practice? Why or why not?",
            height=100
        )
        
        st.session_state.logout_survey_data['q3d_other'] = survey.text_area(
            "Any other suggestions or thoughts?",
            height=100
        )

    elif pages.current == 3 and st.session_state.get('group') == 'B':
        st.write("#### Section D: Explainability Features")
        explainability_data = {}
        
        st.session_state.logout_survey_data['q4a_helpful'] = survey.radio(
            "The explanation was helpful.",
            options=["1 - Not at all helpful", "2 - Slightly helpful", "3 - Moderately helpful", "4 - Very helpful", "5 - Extremely helpful"],
            horizontal=True
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q4b_refinement'] = survey.radio(
            "It helped me refine my prompt.",
            options=["Yes", "No"],
            horizontal=True
        )
        
        st.session_state.logout_survey_data['q4c_comment'] = survey.text_area(
            "Optional comment about prompt refinement",
            placeholder="Share your thoughts about the refinement process..."
        )
        
        st.session_state.logout_survey_data['q4d_understanding'] = survey.radio(
            "I found it easy to guess what the model needed to perform better.",
            options=["1 - Very difficult", "2 - Somewhat difficult", "3 - Neutral", "4 - Somewhat easy", "5 - Very easy"],
            horizontal=True
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q4e_expectations'] = survey.radio(
            "The model's response matched what I expected after refining the prompt.",
            options=["1 - Not at all", "2 - A little", "3 - Moderately", "4 - Mostly", "5 - Completely"],
            horizontal=True
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q4f_trust'] = survey.radio(
            "I trust the model more after prompt refinement.",
            options=["1 - Much less trust", "2 - Slightly less trust", "3 - No change", "4 - Slightly more trust", "5 - Much more trust"],
            horizontal=True
        ).split(" - ")[0]
        
        explainability_data = {
            "q4a_helpful": st.session_state.logout_survey_data['q4a_helpful'],
            "q4b_refinement": st.session_state.logout_survey_data['q4b_refinement'],
            "q4c_comment": st.session_state.logout_survey_data['q4c_comment'],
            "q4d_understanding": st.session_state.logout_survey_data['q4d_understanding'],
            "q4e_expectations": st.session_state.logout_survey_data['q4e_expectations'],
            "q4f_trust": st.session_state.logout_survey_data['q4f_trust']
        }

    # Navigation buttons at bottom with equal width
    st.write("")  # Add spacing
    col1, col2 = st.columns(2)
    with col1:
        if pages.current > 0:
            if st.button("← Previous", use_container_width=True):
                pages.previous()
                st.rerun()
    with col2:
        if pages.current < total_pages - 1:  # Not last page
            if st.button("Next →", type="primary", use_container_width=True):
                pages.next()
                st.rerun()
        else:  # Last page
            if st.button("Submit & Logout", type="primary", use_container_width=True):
                # Prepare survey data from session state
                survey_data = {
                    "usability": {
                        "q1a_ease": int(st.session_state.logout_survey_data.get('q1a_ease')),
                        "q1b_clarity": int(st.session_state.logout_survey_data.get('q1b_clarity')),
                        "q1c_reuse": int(st.session_state.logout_survey_data.get('q1c_reuse')),
                        "q1d_prior_exp": int(st.session_state.logout_survey_data.get('q1d_prior_exp')),
                        "q1e_exp_affect": st.session_state.logout_survey_data.get('q1e_exp_affect'),
                        "q1f_exp_how": st.session_state.logout_survey_data.get('q1f_exp_how') if st.session_state.logout_survey_data.get('q1e_exp_affect') == "Yes" else None,
                        "q1g_understanding": int(st.session_state.logout_survey_data.get('q1g_understanding'))
                    },
                    "trust": {
                        "q2a_trust": int(st.session_state.logout_survey_data.get('q2a_trust')),
                        "q2b_understanding": int(st.session_state.logout_survey_data.get('q2b_understanding')),
                        "q2c_explanations": int(st.session_state.logout_survey_data.get('q2c_explanations')) if st.session_state.logout_survey_data.get('q2c_explanations') else None
                    },
                    "feedback": {
                        "q3a_likes": st.session_state.logout_survey_data.get('q3a_likes'),
                        "q3b_improvements": st.session_state.logout_survey_data.get('q3b_improvements'),
                        "q3c_clinical": st.session_state.logout_survey_data.get('q3c_clinical'),
                        "q3d_other": st.session_state.logout_survey_data.get('q3d_other')
                    },
                    "explainability": explainability_data if st.session_state.get('group') == 'B' else None,
                    "group": st.session_state.get('group', 'unknown'),
                    "login_time": st.session_state.login_time,
                    "logout_time": datetime.datetime.now().isoformat()
                }
                
                # Save data and handle logout
                survey_storage = SurveyStorage()
                survey_storage.save_logout_survey(st.session_state.user_id, survey_data)
                
                data_merger = DataMerger()
                merged_file = data_merger.merge_all_data()
                
                if merged_file:
                    stats = data_merger.generate_summary_stats(merged_file)
                    print(f"[INFO] Data merged successfully. Stats: {stats}")
                    
                st.session_state.logged_out = True
                st.rerun()
                SessionManager.clear_session()
        

show_logout_survey()