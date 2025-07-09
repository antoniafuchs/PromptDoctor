import streamlit as st
from utils.style_loader import load_styles
import streamlit_survey as ss
from datetime import datetime
from tracking.logging import log_chat_interaction
from core.db_utils import DBManager  


import uuid
import argparse
import sys
import os

# Force light mode
st.set_page_config(
    page_title="PromptDoctor",
    layout="centered",
    initial_sidebar_state="auto"
)


# Add custom CSS for larger body text
st.markdown("""
<style>
    [data-testid="collapsedControl"] {display: none;}
            section[data-testid="stSidebar"] {display: none;}
            .main > div {
                max-width: 48rem;
                margin: auto;
                padding: 2rem;
            }
    /* Make body text larger */
    div[data-testid="stMarkdownContainer"] p {
        font-size: 20px !important;
        line-height: 1.6 !important;
    }
    
    /* Make survey questions and checkbox labels larger */
    .stCheckbox label p, .stRadio label, div.stText p {
        font-size: 20px !important;
    }
    
    /* Make subheaders larger */
    div[data-testid="stMarkdownContainer"] h3 {
        font-size: 28px !important;
        margin-top: 24px !important;
        margin-bottom: 16px !important;
    }
    
    /* Make list items larger, including those with HTML markup */
    div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stMarkdownContainer"] li strong,
    div[data-testid="stMarkdownContainer"] li p {
        font-size: 20px !important;
        line-height: 1.6 !important;
    }
    
    /* Add a bit more spacing between list items */
    div[data-testid="stMarkdownContainer"] li {
        margin-bottom: 8px !important;
    }
</style>
""", unsafe_allow_html=True)



# Add argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--study', action='store_true')
args = parser.parse_known_args()[0]

# Store study mode in session state
if "study_mode" not in st.session_state:
    st.session_state.study_mode = args.study

# Redirect to Home if in study mode and coming from another page
if st.session_state.study_mode and 'login_complete' in st.session_state and not st.session_state.get('navigating_from_home', False):
    # Set flag to prevent infinite redirect
    st.session_state.navigating_from_home = True
    # Reset the flag when actually navigating away
    if 'current_page' in st.session_state and st.session_state.current_page == 'Home.py':
        st.session_state.navigating_from_home = False

# Load shared styles
load_styles()

# Initialize the survey with multiple pages - change to 3 pages
survey = ss.StreamlitSurvey("Welcome")
pages = survey.pages(3, on_submit=lambda: None)

st.title("Welcome to PromptDoctor")
st.progress((pages.current + 1) / 3, text=f"Page {pages.current + 1} of 3")

# Introduction page
if pages.current == 0:
    st.markdown("""
    ### Thank you for participating in this study!
                
    As part of my master thesis, I am investigating how interactive visual tools can help medical professionals like you in clinical tasks such as diagnosis and treatment suggestions.

    Your responses will help to understand how to improve the design and usability of AI tools in medical contexts.
    """)

# What Will You Be Doing page
elif pages.current == 1:
    st.markdown("""
    ### What will you be doing?
    This study will take approximately 25 minutes involving:

    - **Pre-Use Questionnaire**: A few questions about your background and experience.            
    - **Clinical Case Tasks**: You will see patient cases and be asked to use the developed tool to solve three tasks (e.g. diagnosis, treatment suggestions based on synthetic clincal notes).
    - **Post-Task Feedback Questionnaire**: A few questions about your experience with each task.
    - **Final Feedback Questionnaire**: A few questions about your overall experience with the developed tool.
                
    ### Important
    :red-background[**This is not a test of your medical knowledge**] — I am interested in how you interact with the tool, not whether your diagnosis is "correct".
                
    In the user interface you will have the option to rate the answers of the tool for clinical accuracy using:
    """)
    
    feedback_col1, feedback_col2 = st.columns([1, 8])
    with feedback_col1:
        st.button("👍", key="preview_thumbsup", disabled=True)
        
    with feedback_col2:
        st.button("👎", key="preview_thumbsdown", disabled=True)
    
    # Better formatting for mobile device section
    st.markdown("""
    ### Mobile Device Users
    If you're using a mobile device, you may need to click the ">" icon at the top-left corner to open the sidebar first.
    """)

    st.markdown("""
    When you completed a task you will need to check this box in the sidebar to continue with the next task.
    """)
    
    # Display checkbox image with better formatting
    st.image("assets/checkbox.png", width=270)

# Last page (page 2) with consent
elif pages.current == 2:
    st.markdown("""
    ### Consent and Data Use
                
    By checking the box below you confirm that:
    - You voluntarily agree to participate in this study.
    - You understand that your interactions with the tool, chat history and survey answers will be recorded for research purposes (the results could be published in a scientific paper).
    - All data is anonymized and stored securely. No identifying personal data will be collected.
    - You may stop at any time without giving a reason.
    
    ### Contact Information
    If you have any questions about this study or how your data will be used, you can contact me at:
    
    Antonia Fuchs  
    Chair for Fundamentals of Natural Language Processing, University of Bamberg  
    antonia-frederieke.fuchs@stud.uni-bamberg.de
    
                
    This study complies with GDPR. You can request deletion of your data at any time.
    """)
    
    consent_given = st.checkbox("I have read and agree to the above terms")
    
    if consent_given:
        if "user_id" not in st.session_state:
            st.session_state.user_id = str(uuid.uuid4())
            st.session_state.login_time = datetime.now().isoformat()

        if "consent_logged" not in st.session_state:
            st.session_state.consent_logged = False
            
        if not st.session_state.consent_logged:
            # Log the consent action
            log_chat_interaction(
                user_id=st.session_state.user_id,  # Now using the created user_id
                action_type="CONSENT_GIVEN",
                timestamp=datetime.now().isoformat()
            )
            st.session_state.consent_logged = True
            
        if st.button("Start", type="primary"):
            if "group" not in st.session_state:
                db_manager = DBManager()
                st.session_state.group = db_manager.assign_group_to_user(st.session_state.user_id)
                
            if st.session_state.study_mode:
                # Set default model settings for study mode to use Together AI
                st.session_state.selected_model_type = "Together"
                st.session_state.selected_model_name = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
                
                # Set Together API key and environment variable
                st.session_state.together_api_key = "tgp_v1_qMVnwAdRKPrsy0ASdwt2bMowEWAkz6q5X4XmUbGdRr8"
                os.environ["TOGETHER_API_KEY"] = "tgp_v1_qMVnwAdRKPrsy0ASdwt2bMowEWAkz6q5X4XmUbGdRr8"
                
                st.session_state.login_complete = True                
                # Add model configuration for controlling token generation
                st.session_state.model_config = {
                    "max_new_tokens": 350,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
                # Mark that we're navigating from home to avoid redirect loops
                st.session_state.navigating_from_home = True
                st.session_state.current_page = 'Survey.py'
                st.switch_page("pages/2_Survey.py")
            else:
                st.session_state.current_page = 'Login.py'
                st.switch_page("pages/1_Login.py")
    else:
        st.info("Please read and accept the terms to continue")

# Add navigation buttons at bottom
st.write("")  # Add spacing
col1, col2 = st.columns(2)
with col1:
    if pages.current > 0:
        if st.button("← Previous", use_container_width=True):
            pages.previous()
            st.rerun()
with col2:
    if pages.current < 2:  # Update last page check to 2
        if st.button("Next →", type="primary", use_container_width=True):
            pages.next()
            st.rerun()

# Store current page for navigation tracking
st.session_state.current_page = 'Home.py'
