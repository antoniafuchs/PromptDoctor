import streamlit as st
import streamlit_survey as ss
from tracking.logging import log_chat_interaction
from utils.model_handler import ModelHandler

def show_login_survey():
    if "user_id" not in st.session_state or st.session_state.user_id is None:
        st.switch_page("pages/Login")
        return
        
    st.set_page_config(page_title="PromptDoctor")
    st.header("Survey")

    # Initialize model handler if not done
    if "model_handler" not in st.session_state:
        st.session_state.model_handler = ModelHandler()
        st.session_state.model_handler.initialize_model(
            st.session_state.selected_model_type,
            st.session_state.selected_model_name
        )

    # Initialize the survey with multiple pages
    survey = ss.StreamlitSurvey("Survey")
    pages = survey.pages(4, on_submit=lambda: None)
    
    st.progress((pages.current + 1) / 4, text=f"Page {pages.current + 1} of 4")

    # Initialize session state for survey responses if not exists
    if "survey_responses" not in st.session_state:
        st.session_state.survey_responses = {}
        
    # Demographics page
    if pages.current == 0:
        st.subheader("Demographics")
        st.write("Optional demographic questions:")
        
        st.session_state.survey_responses['age'] = survey.text_input(
            "Age (optional)",
            value=st.session_state.survey_responses.get('age', ''),
            max_chars=3
        )

        st.session_state.survey_responses['gender'] = survey.radio(
            "Gender (optional)",
            options=[
                "Male",
                "Female",
                "Non-binary",
                "Prefer not to say"
            ],
            index=3,
            horizontal=True
        )

    # Medical Experience page
    elif pages.current == 1:
        st.subheader("Medical & Clinical Experience")
        
        q1_training = survey.radio(
            "What is your current level of medical training?",
            options=[
                "Medical Student (Pre-clinical)",
                "Medical Student (Clinical years)",
                "Resident",
                "Specialist",
                "Other"
            ],
            index=0,
            horizontal=False
        )

        if q1_training == "Other" or q1_training == "Specialist":
            q1_other = survey.text_input("Please specify:")

        q2_records = survey.radio(
            "Do you have experience working with real patient records?",
            options=["Yes", "No"],
            index=0,
            horizontal=False
        )

        q3_training = survey.radio(
            "Have you received formal training in clinical reasoning or diagnostic thinking?",
            options=["Yes", "No"],
            index=0,
            horizontal=False
        )

        q4_confidence = survey.radio(
            "How confident are you in interpreting clinical notes?",
            options=["1 - Not at all confident", "2 - Slightly confident", "3 - Moderately confident", "4 - Very confident", "5 - Extremely confident"],
            index=2,
            horizontal=True
        ).split(" - ")[0]

        st.session_state.survey_responses['q1_training'] = q1_training
        if q1_training == "Other" or q1_training == "Specialist":
            st.session_state.survey_responses['q1_other'] = q1_other

        st.session_state.survey_responses['q2_records'] = q2_records
        st.session_state.survey_responses['q3_training'] = q3_training
        st.session_state.survey_responses['q4_confidence'] = q4_confidence

    # AI Familiarity page
    elif pages.current == 2:
        st.subheader("Familiarity with AI and Prompting")
        
        st.write("How familiar are you with:")
        q5a_gen_ai = survey.radio(
            "a. Generative AI tools (e.g., ChatGPT)",
            options=["1 - Not at all", "2 - Slightly familiar", "3 - Moderately familiar", "4 - Very familiar", "5 - Expert"],
            index=2,
            horizontal=True
        ).split(" - ")[0]

        q5b_prompt = survey.radio(
            "b. Prompt engineering",
            options=["1 - Not at all", "2 - Slightly familiar", "3 - Moderately familiar", "4 - Very familiar", "5 - Expert"],
            index=2,
            horizontal=True
        ).split(" - ")[0]

        q5c_cds = survey.radio(
            "c. Clinical decision support tools",
            options=["1 - Not at all", "2 - Slightly familiar", "3 - Moderately familiar", "4 - Very familiar", "5 - Expert"],
            index=2,
            horizontal=True
        ).split(" - ")[0]

        q6_tools = survey.multiselect(
            "Have you used any of the following tools before?",
            options=[
                "ChatGPT",
                "Google Bard / Gemini",
                "Med-PaLM",
                "UpToDate",
                "Other"
            ]
        )

        if "Other" in q6_tools:
            q6_other = survey.text_input("Please specify other tools:")

        q7_frequency = survey.radio(
            "How frequently do you use LLMs (e.g., ChatGPT)?",
            options=[
                "Never",
                "Rarely",
                "Occasionally",
                "Weekly",
                "Daily"
            ],
            index=0,
            horizontal=False
        )

        st.session_state.survey_responses['q5a_gen_ai'] = q5a_gen_ai
        st.session_state.survey_responses['q5b_prompt'] = q5b_prompt
        st.session_state.survey_responses['q5c_cds'] = q5c_cds
        st.session_state.survey_responses['q6_tools'] = q6_tools
        if "Other" in q6_tools:
            st.session_state.survey_responses['q6_other'] = q6_other
        st.session_state.survey_responses['q7_frequency'] = q7_frequency

    # Final page with expectations
    else:
        st.subheader("LLM Usage & Expectations")
        
        q8_uses = survey.multiselect(
            "What do you usually use LLMs for? (Select all that apply)",
            options=[
                "Study help",
                "Medical knowledge lookup",
                "Writing / documentation",
                "Clinical summarization",
                "Other"
            ]
        )

        if "Other" in q8_uses:
            q8_other = survey.text_input("Please specify other LLM uses:")

        q9_trust = survey.radio(
            "How much do you currently trust AI-generated answers for medical topics?",
            options=["1 - Not at all", "2 - Slightly", "3 - Moderately", "4 - Very much", "5 - Completely"],
            index=2,
            horizontal=True
        ).split(" - ")[0]

        q10_expectations = survey.text_area(
            "What are your expectations from tools like these?"
        )

        st.session_state.survey_responses['q8_uses'] = q8_uses
        if "Other" in q8_uses:
            st.session_state.survey_responses['q8_other'] = q8_other
        st.session_state.survey_responses['q9_trust'] = q9_trust
        st.session_state.survey_responses['q10_expectations'] = q10_expectations

    # Add navigation buttons at bottom of each page
    st.write("")  # Add spacing
    col1, col2 = st.columns(2)
    with col1:
        if pages.current > 0:
            if st.button("← Previous", use_container_width=True):
                pages.previous()
                st.rerun()
    with col2:
        if pages.current < 3:  # Not last page
            if st.button("Next →", type="primary", use_container_width=True):
                pages.next()
                st.rerun()
        else:  # Last page
            if st.button("Continue to App", type="primary", use_container_width=True):
                # Prepare survey data
                survey_data = {
                    "demographics": {
                        "age": st.session_state.survey_responses.get('age') if st.session_state.survey_responses.get('age') != "" else None,
                        "gender": st.session_state.survey_responses.get('gender') if st.session_state.survey_responses.get('gender') != "Prefer not to say" else None
                    },
                    "medical_background": {
                        "training_level": st.session_state.survey_responses.get('q1_training'),
                        "specialization": st.session_state.survey_responses.get('q1_other') if st.session_state.survey_responses.get('q1_training') in ["Other", "Specialist"] else None,
                        "patient_records_exp": st.session_state.survey_responses.get('q2_records'),
                        "clinical_reasoning_training": st.session_state.survey_responses.get('q3_training'),
                        "clinical_notes_confidence": st.session_state.survey_responses.get('q4_confidence')
                    },
                    "ai_experience": {
                        "gen_ai_familiarity": st.session_state.survey_responses.get('q5a_gen_ai'),
                        "prompt_eng_familiarity": st.session_state.survey_responses.get('q5b_prompt'),
                        "cds_familiarity": st.session_state.survey_responses.get('q5c_cds'),
                        "tools_used": st.session_state.survey_responses.get('q6_tools'),
                        "other_tools": st.session_state.survey_responses.get('q6_other') if "Other" in st.session_state.survey_responses.get('q6_tools', []) else None,
                        "llm_usage_frequency": st.session_state.survey_responses.get('q7_frequency')
                    },
                    "usage_patterns": {
                        "use_cases": st.session_state.survey_responses.get('q8_uses'),
                        "other_use_cases": st.session_state.survey_responses.get('q8_other') if "Other" in st.session_state.survey_responses.get('q8_uses', []) else None,
                        "trust_level": st.session_state.survey_responses.get('q9_trust'),
                        "expectations": st.session_state.survey_responses.get('q10_expectations')
                    },
                    "metadata": {
                        "group": st.session_state.get('group', 'unknown')
                    }
                }

                # Log survey responses
                log_chat_interaction(
                    st.session_state.user_id,
                    "SURVEY_COMPLETE",
                    additional_data=survey_data
                )
            
                # Route to appropriate chat page based on group
                if st.session_state.group == "A":
                    st.switch_page("pages/3_Chat_base.py")
                else:
                    st.switch_page("pages/3_Chat.py")

show_login_survey()