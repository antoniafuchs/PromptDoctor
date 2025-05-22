import streamlit as st
import streamlit_survey as ss
from tracking.logging import log_chat_interaction
from streamlit_extras.switch_page_button import switch_page
import pyperclip
import time
import datetime
from utils.data_merger import DataMerger
from utils.session_manager import SessionManager
from utils.data_storage import DataStorage  # Update import
from utils.style_loader import load_styles


def show_logout_survey():
    if not SessionManager.get_session_id():
        st.switch_page("Home.py")
        return

    st.set_page_config(
        page_title="PromptDoctor",
        initial_sidebar_state="collapsed"  # Start with sidebar collapsed
    )

    # Load shared styles
    load_styles()

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

    # Initialize logout survey data if not exists
    if "logout_survey_data" not in st.session_state:
        st.session_state.logout_survey_data = {}

    st.header("Thanks for Completing All Tasks!")

    # Show only goodbye messages if logged out
    if st.session_state.logged_out:
        st.success("Thank you for your participation! You can now close this window.")
        return

    # Initialize survey with multiple pages
    survey = ss.StreamlitSurvey("LogoutSurvey")
    total_pages = 3 if st.session_state.get('group') != 'B' else 5  # Update total pages for group B
    pages = survey.pages(total_pages)
    
    st.progress((pages.current + 1) / total_pages, 
                text=f"Page {pages.current + 1} of {total_pages}")

    # Survey content for each page
    if pages.current == 0:
        st.write("#### Section A: Overall Usability")
        
        st.session_state.logout_survey_data['q1a_ease'] = survey.radio(
            "The tool was easy to use.",
            options=["1 - Strongly Disagree", "2 - Somewhat Disagree", "3 - Neutral", "4 - Somewhat Agree", "5 - Strongly Agree"],
            index=2,
            horizontal=False
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q1b_clarity'] = survey.radio(
            "The task instructions were clear.",
            options=["1 - Strongly Disagree", "2 - Somewhat Disagree", "3 - Neutral", "4 - Somewhat Agree", "5 - Strongly Agree"],
            index=2,
            horizontal=False
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q1c_reuse'] = survey.radio(
            "I would use this tool again for similar tasks.",
            options=["1 - Strongly Disagree", "2 - Somewhat Disagree", "3 - Neutral", "4 - Somewhat Agree", "5 - Strongly Agree"],
            index=2,
            horizontal=False
        ).split(" - ")[0]
        

    elif pages.current == 1:
        st.write("#### Section B: Trust and Understanding")
        st.write("Please consider how your trust and understanding evolved during the study.")
        
        st.session_state.logout_survey_data['q2a_trust'] = survey.radio(
            "I trust the final outputs from the model.",
            options=[
                "1 - Much less trust than before",
                "2 - Slightly less trust",
                "3 - No change in trust",
                "4 - Slightly more trust",
                "5 - Much more trust than before"
            ],
            index=2,
            horizontal=False
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q2b_understanding'] = survey.radio(
            "I understood why the model gave certain answers.",
            options=[
                "1 - Never understood",
                "2 - Rarely understood",
                "3 - Sometimes understood",
                "4 - Often understood",
                "5 - Always understood"
            ],
            index=2,
            horizontal=False
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q2c_trust_factors'] = survey.radio(
            "What most influenced your trust in the model?",
            options=[
                "Output accuracy",
                "Explanation clarity",
                "Consistency",
                "Medical terminology use",
                "Other"
            ],
            horizontal=False
        )
        
        if st.session_state.logout_survey_data['q2c_trust_factors'] == "Other":
            st.session_state.logout_survey_data['q2c_trust_other'] = survey.text_input(
                "Please specify what influenced your trust:"
            )
            
        st.session_state.logout_survey_data['q2e_trust'] = survey.radio(
            "How much do you currently trust AI-generated answers for medical topics?",
            options=[
                "1 - Not at all (Never trust without complete verification)",
                "2 - Slightly (Trust basic information after verification)", 
                "3 - Moderately (Trust general information with spot checks)",
                "4 - Very much (Trust most content with minimal verification)",
                "5 - Completely (Trust all output without verification)"
            ],
            index=2,
            horizontal=False
        ).split(" - ")[0]

        if st.session_state.get('group') == 'B':
            st.session_state.logout_survey_data['q2d_explanations'] = survey.radio(
                "The highlighted terms helped build trust in the model.",
                options=[
                    "1 - Strongly Disagree",
                    "2 - Somewhat Disagree",
                    "3 - Neutral",
                    "4 - Somewhat Agree",
                    "5 - Strongly Agree"
                ],
                index=2,
                horizontal=False
            ).split(" - ")[0]

    elif pages.current == 2 and st.session_state.get('group') == 'B':
        st.write("#### Section C: Explainability Features")
        st.write("##### 1. Term Highlighting")
       
        st.session_state.logout_survey_data['q1g_terms_useful'] = survey.radio(
            "Did the highlighted terms encourage you to refine or rethink your prompt?",
            options=["1 - Not at all", "2 - Slightly", "3 - Moderately", "4 - Very much", "5 - Extremely"],
            index=2,
            horizontal=False
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q1p_highlight_missed_terms'] = survey.text_area(
            "Were there any terms you expected to be highlighted but weren't?",
            height=100
        )
        
        st.write("##### 2. Prompt Editing Purpose and Perceived Usefulness")
       
        st.session_state.logout_survey_data['q1d_edit_helpful'] = survey.radio(
            "How helpful was the prompt editing step in improving the AI's response?",
            options=["1 - Not helpful at all", "2 - Slightly helpful", "3 - Moderately helpful", "4 - Very helpful", "5 - Extremely helpful"],
            index=2,
            horizontal=False
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q1e_edit_understanding'] = survey.radio(
            "Did editing the prompt help you better understand how the AI interprets your input?",
            options=["1 - Strongly disagree", "2 - Somewhat disagree", "3 - Neither agree nor disagree", "4 - Somewhat agree", "5 - Strongly agree"],
            index=2,
            horizontal=False
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q1i_edit_self_efficacy'] = survey.radio(
            "Did the editing step make you feel more in control of the AI's output?",
            options=["1 - Not at all", "2 - Slightly", "3 - Moderately", "4 - Very much", "5 - Completely"],
            index=2,
            horizontal=False
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q1k_edit_clarity'] = survey.radio(
            "The editing step made it clearer what the AI pays attention to in your input.",
            options=["1 - Strongly disagree", "2 - Somewhat disagree", "3 - Neither agree nor disagree", "4 - Somewhat agree", "5 - Strongly agree"],
            index=2,
            horizontal=False
        ).split(" - ")[0]

    elif pages.current == 3 and st.session_state.get('group') == 'B':
        st.write("#### Section C: Explainability Features")
        st.write("##### 3. Prompt Changes & Reuse Potential")
        st.session_state.logout_survey_data['q1m_edit_changed_prompt'] = survey.radio(
            "Did you change your original prompt based on the editing step?",
            options=["Yes", "No", "Not sure"],
            index=2,
            horizontal=False
        )
        
        if st.session_state.logout_survey_data['q1m_edit_changed_prompt'] == "Yes":
            st.session_state.logout_survey_data['q1n_edit_change_reason'] = survey.text_area(
                "If you changed your prompt, what motivated the change?",
                height=100
            )
        
        st.session_state.logout_survey_data['q1o_edit_reuse'] = survey.radio(
            "Would you want a similar editing feature in other AI tools you use?",
            options=[
                "1 - Not at all useful",
                "2 - Slightly useful",
                "3 - Moderately useful",
                "4 - Very useful", 
                "5 - Extremely useful"
            ],
            index=2,
            horizontal=False
        ).split(" - ")[0]

        st.session_state.logout_survey_data['q4a_helpful'] = survey.radio(
            "The explanation visualization in task 3 was helpful.",
            options=[
                "1 - Not at all helpful",
                "2 - Slightly helpful",
                "3 - Moderately helpful", 
                "4 - Very helpful",
                "5 - Extremely helpful"
            ],
            index=2,
            horizontal=False
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q4b_refinement'] = survey.radio(
            "It helped me refine my prompt.",
            options=[
                "1 - Not at all useful",
                "2 - Slightly useful",
                "3 - Moderately useful",
                "4 - Very useful",
                "5 - Extremely useful"
            ],
            index=2,
            horizontal=False
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q4c_understanding'] = survey.radio(
            "The explanations helped me understand the model's decision-making.",
            options=[
                "1 - Not at all helpful",
                "2 - Slightly helpful",
                "3 - Moderately helpful",
                "4 - Very helpful",
                "5 - Extremely helpful"
            ],
            index=2,
            horizontal=False
        ).split(" - ")[0]
        
        st.session_state.logout_survey_data['q4d_trust'] = survey.radio(
            "I trust the model more after seeing the highlighted terms.",
            options=[
                "1 - Strongly disagree",
                "2 - Somewhat disagree",
                "3 - Neither agree nor disagree",
                "4 - Somewhat agree",
                "5 - Strongly agree"
            ],
            index=2,
            horizontal=False
        ).split(" - ")[0]

        # Add safe_int helper earlier in the code
        def safe_int(value):
            if value is None or value == "":
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        explainability_data = {
            # Medical Term Highlighting
            "q1f_highlight_meaning": st.session_state.logout_survey_data.get('q1f_highlight_meaning'),
            "q1g_terms_useful": safe_int(st.session_state.logout_survey_data.get('q1g_terms_useful')),
            "q1p_highlight_missed_terms": st.session_state.logout_survey_data.get('q1p_highlight_missed_terms'),
            
            # Prompt Editing Purpose
            "q1c_edit_purpose": st.session_state.logout_survey_data.get('q1c_edit_purpose'),
            "q1d_edit_helpful": safe_int(st.session_state.logout_survey_data.get('q1d_edit_helpful')),
            "q1e_edit_understanding": safe_int(st.session_state.logout_survey_data.get('q1e_edit_understanding')),
            "q1i_edit_self_efficacy": safe_int(st.session_state.logout_survey_data.get('q1i_edit_self_efficacy')),
            "q1j_edit_valuable": safe_int(st.session_state.logout_survey_data.get('q1j_edit_valuable')),
            "q1k_edit_clarity": safe_int(st.session_state.logout_survey_data.get('q1k_edit_clarity')),
            "q1l_edit_learning": safe_int(st.session_state.logout_survey_data.get('q1l_edit_learning')),
            
            # Prompt Changes
            "q1m_edit_changed_prompt": st.session_state.logout_survey_data.get('q1m_edit_changed_prompt'),
            "q1n_edit_change_reason": st.session_state.logout_survey_data.get('q1n_edit_change_reason') if st.session_state.logout_survey_data.get('q1m_edit_changed_prompt') == "Yes" else None,
            "q1o_edit_reuse": safe_int(st.session_state.logout_survey_data.get('q1o_edit_reuse')),
            
            # Original explainability fields
            "q4a_helpful": safe_int(st.session_state.logout_survey_data.get('q4a_helpful')),
            "q4b_refinement": safe_int(st.session_state.logout_survey_data.get('q4b_refinement')),
            "q4c_comment": st.session_state.logout_survey_data.get('q4c_comment'),
            "q4d_understanding": safe_int(st.session_state.logout_survey_data.get('q4d_understanding')),
            "q4e_expectations": safe_int(st.session_state.logout_survey_data.get('q4e_expectations')),
            "q4f_trust": safe_int(st.session_state.logout_survey_data.get('q4f_trust'))
        }

    # Open Feedback is always the last section
    elif (pages.current == 2 and st.session_state.get('group') != 'B') or \
         (pages.current == 4 and st.session_state.get('group') == 'B'):
        st.write("#### Open Feedback")
        st.write("Please be as specific as possible in your responses, including concrete examples where relevant.")
        
        st.session_state.logout_survey_data['q3a_likes'] = survey.text_area(
            "What specific features or aspects did you find most helpful?",
            placeholder="Please describe specific examples and why they were valuable...",
            height=100
        )
        
        st.session_state.logout_survey_data['q3b_improvements'] = survey.text_area(
            "What concrete changes or improvements would enhance your experience?",
            placeholder="Please suggest specific modifications or additions...",
            height=100
        )
        
        st.session_state.logout_survey_data['q3c_clinical_yn'] = survey.radio(
            "Would you use such a tool in clinical practice?",
            options=["Yes", "No", "Unsure"],
            index=2,
            horizontal=True
        )
        
        st.session_state.logout_survey_data['q3c_clinical'] = survey.text_area(
            "Please explain why or why not:",
            placeholder="Consider specific use cases, benefits, and concerns...",
            height=100
        )
        
        st.session_state.logout_survey_data['q3d_other'] = survey.text_area(
            "Do you have any other specific feedback or suggestions?",
            placeholder="Any additional observations, concerns, or ideas...",
            height=100
        )

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
                # Safe integer conversion helper
                def safe_int(value):
                    if value is None or value == "":
                        return None
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return None

                # Prepare survey data from session state
                survey_data = {
                    'user_id': st.session_state.user_id,
                    'timestamp': datetime.datetime.now().isoformat(),
                    'group': st.session_state.get('group', 'unknown'),
                    'login_time': st.session_state.login_time,
                    'logout_time': datetime.datetime.now().isoformat(),
                    
                    # Use safe_int for numeric conversions
                    'US_ease': safe_int(st.session_state.logout_survey_data.get('q1a_ease')),
                    'US_clarity': safe_int(st.session_state.logout_survey_data.get('q1b_clarity')),
                    'US_reuse': safe_int(st.session_state.logout_survey_data.get('q1c_reuse')),
                    
                    'TR_model_trust': safe_int(st.session_state.logout_survey_data.get('q2a_trust')),
                    'TR_understanding': safe_int(st.session_state.logout_survey_data.get('q2b_understanding')),
                    'TR_current_trust': safe_int(st.session_state.logout_survey_data.get('q2e_trust')),
                    'TR_explanations': safe_int(st.session_state.logout_survey_data.get('q2d_explanations')) if st.session_state.get('group') == 'B' else None,
                    
                    'FB_likes': st.session_state.logout_survey_data.get('q3a_likes'),
                    'FB_improvements': st.session_state.logout_survey_data.get('q3b_improvements'),
                    'FB_clinical_yn': st.session_state.logout_survey_data.get('q3c_clinical_yn'),
                    'FB_clinical': st.session_state.logout_survey_data.get('q3c_clinical'),
                    'FB_other': st.session_state.logout_survey_data.get('q3d_other'),
                }

                # Add explainability data for group B with safe integer conversion
                if st.session_state.get('group') == 'B':
                    explainability_data = {
                        'EX_helpful': safe_int(st.session_state.logout_survey_data.get('q4a_helpful')),
                        'EX_refinement': safe_int(st.session_state.logout_survey_data.get('q4b_refinement')),
                        'EX_understanding': safe_int(st.session_state.logout_survey_data.get('q4c_understanding')),
                        'EX_trust': safe_int(st.session_state.logout_survey_data.get('q4d_trust')),
                        'EX_terms_useful': safe_int(st.session_state.logout_survey_data.get('q1g_terms_useful')),
                        'EX_edit_helpful': safe_int(st.session_state.logout_survey_data.get('q1d_edit_helpful')),
                        'EX_edit_understanding': safe_int(st.session_state.logout_survey_data.get('q1e_edit_understanding')),
                        'EX_self_efficacy': safe_int(st.session_state.logout_survey_data.get('q1i_edit_self_efficacy')),
                        'EX_clarity': safe_int(st.session_state.logout_survey_data.get('q1k_edit_clarity')),
                        'EX_edit_changed': st.session_state.logout_survey_data.get('q1m_edit_changed_prompt'),
                        'EX_edit_reason': st.session_state.logout_survey_data.get('q1n_edit_change_reason'),
                        'EX_reuse': safe_int(st.session_state.logout_survey_data.get('q1o_edit_reuse'))
                    }
                    survey_data.update(explainability_data)

                # Save survey data using only DataStorage
                data_storage = DataStorage()
                data_storage.log_survey(survey_data)
                
                # Merge data files
                data_merger = DataMerger()
                merged_file = data_merger.merge_all_data()
                
                if merged_file:
                    stats = data_merger.generate_summary_stats(merged_file)
                    print(f"[INFO] Data merged successfully. Stats: {stats}")
                
                st.session_state.logged_out = True
                st.rerun()
                SessionManager.clear_session()

show_logout_survey()