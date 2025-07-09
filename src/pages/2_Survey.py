import streamlit as st
import streamlit_survey as ss
from tracking.logging import log_chat_interaction
from src.models.model_handler import ModelHandler
from utils.style_loader import load_styles
from datetime import datetime
from src.core.data_storage import DataStorage  

# Initialize session state for form values if not exists
if "survey_form_values" not in st.session_state:
    st.session_state.survey_form_values = {}
if "form_value_cache" not in st.session_state:
    st.session_state.form_value_cache = {}

def cache_form_value(key, value):
    """Cache a form value in session state with validation"""
    # Store the value in both caches for redundancy
    st.session_state.survey_form_values[key] = value
    st.session_state.form_value_cache[key] = value
    # Force immediate persist to prevent loss
    st.session_state[f"cached_{key}"] = value

def get_cached_form_value(key, default=""):
    """Get a cached form value with fallbacks"""
    # Try multiple locations to ensure we get the value
    if key in st.session_state.form_value_cache:
        return st.session_state.form_value_cache[key]
    elif key in st.session_state.survey_form_values:
        return st.session_state.survey_form_values[key]
    elif f"cached_{key}" in st.session_state:
        return st.session_state[f"cached_{key}"]
    else:
        return default

def show_login_survey():
    if "user_id" not in st.session_state or st.session_state.user_id is None:
        st.switch_page("pages/Login")
        return
        
    st.set_page_config(
        page_title="PromptDoctor"
    )
    st.header("Survey")
    
    # Add custom CSS for larger survey text
    st.markdown("""
        <style>
            /* Control main container width */
            .stMainBlockContainer {
                max-width: 800px !important;
                padding-left: 5% !important;
                padding-right: 5% !important;
                margin: 0 auto !important;
            }

            /* Make survey questions extra large */
            div[data-testid="stMarkdownContainer"] p {
                font-size: 20px !important;
            }
            
            /* Style base elements */
            .stMarkdown, .stRadio, .stMultiSelect, .stTextArea, .stTextInput {
                font-size: 20px !important;
            }
            
            /* Radio options larger */
            .stRadio label {
                font-size: 20px !important;
            }
            
            /* Style multiselect options */
            .stMultiSelect div[role="listbox"] span {
                font-size: 20px !important;
            }
            
            /* Style text input and text areas */
            .stTextInput input, .stTextArea textarea {
                font-size: 20px !important;
            }
            
            /* Headers */
            .stMarkdown h3 {
                font-size: 32px !important;
                margin-top: 24px !important;
                margin-bottom: 16px !important;
            }
            .stMarkdown h4 {
                font-size: 28px !important;
                margin-top: 20px !important;
                margin-bottom: 12px !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Load shared styles
    load_styles()

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
        
        age_options = ["Prefer not to say"] + [str(i) for i in range(18, 101)]
        st.session_state.survey_responses['age'] = survey.selectbox(
            "Age",
            options=age_options,
            index=0
        )

        st.session_state.survey_responses['gender'] = survey.radio(
            "Gender",
            options=[
                "Male",
                "Female",
                "Non-binary",
                "Prefer not to say"
            ],
            index=None,  # No default selection
            horizontal=False
        )

        # Validate demographics before allowing next
        demographics_valid = (
            st.session_state.survey_responses.get('age') and 
            st.session_state.survey_responses.get('gender')
        )
        if not demographics_valid:
            st.warning("Please complete all fields before continuing.")

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

        # Only show the "Other" field if "Other" or "Specialist" is selected
        q1_other = ""
        if q1_training == "Other" or q1_training == "Specialist":
            q1_other = survey.text_input(
                "Please specify:",
                value=get_cached_form_value("q1_other"),
                key=f"input_q1_other_{q1_training}"  # Add parent selection to key for uniqueness
            )
            # Cache the value immediately
            cache_form_value("q1_other", q1_other)
        
        q2_records = survey.radio(
            "Do you have experience working with real patient records?",
            options=[
                "Yes",
                "No"
            ],
            index=1,
            horizontal=False
        )

        # Initialize with default value
        q2_records_years = 0
        if q2_records == "Yes":
            q2_records_years = survey.number_input(
                "How many years of experience do you have with patient records?",
                min_value=0,
                max_value=50,
                value=0,
                step=1,
                help="Enter 0 if less than 1 year"
            )

        q3_training = survey.radio(
            "Have you received formal training in clinical reasoning or diagnostic thinking?",
            options=[
                "Yes",
                "No"
            ],
            index=0,
            horizontal=False
        )

        # Initialize the q3_training_desc variable with an empty string
        q3_training_desc = ""
        # We'll only keep Yes/No without the additional text area

        q4_confidence = survey.selectbox(
            "How confident are you in interpreting clinical notes?",
            help="Clincal notes are structured records that you can create to document a patient's health history, treatments, and responses over time.",
            options=[
                "1 - Not at all confident",
                "2 - Slightly confident", 
                "3 - Moderately confident",
                "4 - Very confident",
                "5 - Extremely confident"
            ],
            index=2
        )
        q4_confidence_value = int(q4_confidence.split()[0])  # Store numeric value directly

        # Always store these values, even if empty
        st.session_state.survey_responses['q1_training'] = q1_training
        st.session_state.survey_responses['q1_other'] = q1_other  # Always store the value from session state
        st.session_state.survey_responses['q2_records'] = q2_records
        st.session_state.survey_responses['q2_records_years'] = q2_records_years
        st.session_state.survey_responses['q3_training'] = q3_training
        st.session_state.survey_responses['q3_training_desc'] = q3_training_desc  # Store empty string
        st.session_state.survey_responses['q4_confidence'] = q4_confidence_value

    # AI Familiarity page
    elif pages.current == 2:
        st.subheader("Familiarity with AI and Prompting")
        
        st.write("How familiar are you with:")
        q5a_gen_ai = survey.slider(
            "a. Generative AI tools (e.g. ChatGPT)",
            min_value=1,
            max_value=5,
            value=3,
            help="1: Not at all, 2: Slightly familiar, 3: Moderately familiar, 4: Very familiar, 5: Expert"
        )

        q5b_prompt = survey.slider(
            "b. Prompt engineering",
            min_value=1,
            max_value=5,
            value=3,
            help="1: Not at all, 2: Slightly familiar, 3: Moderately familiar, 4: Very familiar, 5: Expert"
        )

        q5c_cds = survey.slider(
            "c. Clinical decision support tools",
            min_value=1,
            max_value=5,
            value=3,
            help="1: Not at all, 2: Slightly familiar, 3: Moderately familiar, 4: Very familiar, 5: Expert"
        )


        q7_frequency = survey.radio(
            "How frequently do you use LLMs (e.g., ChatGPT)?",
            options=[
                "Never used",
                "Less than once a month",
                "1-3 times per month",
                "1-6 times per week",
                "Daily or more frequently"
            ],
            index=2,
            horizontal=False
        )

        st.session_state.survey_responses['q5a_gen_ai'] = q5a_gen_ai
        st.session_state.survey_responses['q5b_prompt'] = q5b_prompt
        st.session_state.survey_responses['q5c_cds'] = q5c_cds
        st.session_state.survey_responses['q7_frequency'] = q7_frequency

    # Final page with expectations
    else:
        st.subheader("LLM Usage & Expectations")
        
        # Replace multiselect with radio button for primary LLM use
        q8_primary_use = survey.radio(
            "What do you primarily use LLMs for?",
            help="Select your most common use case for LLM tools like ChatGPT",
            options=[
                "Study help",
                "Medical knowledge lookup",
                "Writing / documentation",
                "Clinical summarization",
                "Prompt design or refinement",
                "Other"
            ],
            index=0,
            horizontal=False
        )
        
        # Store as a list with a single item to maintain compatibility with existing code
        q8_uses = [q8_primary_use]

        # Initialize form values if not exist
        if "q8_other" not in st.session_state.survey_form_values:
            st.session_state.survey_form_values["q8_other"] = ""
        
        # Show the text input only if "Other" is selected
        q8_other = ""
        if q8_primary_use == "Other":
            q8_other = survey.text_input(
                "Please specify other LLM use:",
                value=get_cached_form_value("q8_other"),
                key=f"input_q8_other_{q8_primary_use}"  # Dynamic key based on selection
            )
            # Cache the value immediately
            cache_form_value("q8_other", q8_other)

        q9_trust = survey.radio(
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


        st.session_state.survey_responses['q8_uses'] = q8_uses
        st.session_state.survey_responses['q8_other'] = q8_other  # Store the value from session state
        st.session_state.survey_responses['q9_trust'] = int(q9_trust)


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
            if pages.current == 0:
                # Only enable Next button if demographics are valid
                next_disabled = not demographics_valid
                if st.button("Next →", type="primary", use_container_width=True, disabled=next_disabled):
                    pages.next()
                    st.rerun()
            else:
                if st.button("Next →", type="primary", use_container_width=True):
                    pages.next()
                    st.rerun()
        else:  # Last page
            if st.button("Submit & Continue", type="primary", use_container_width=True):
                # Prepare survey data - use cached values for reliability
                survey_data = {
                    'user_id': st.session_state.user_id,
                    'group': st.session_state.get('group', 'unknown'),
                    'login_time': datetime.now().isoformat(),
                    'age': st.session_state.survey_responses.get('age', 'Prefer not to say'),
                    'gender': st.session_state.survey_responses.get('gender', 'Prefer not to say'),
                    'training_level': st.session_state.survey_responses.get('q1_training', ''),
                    'specialization': get_cached_form_value('q1_other', ''),
                    'patient_records_exp': st.session_state.survey_responses.get('q2_records', 'No'),
                    'clinical_notes_confidence': st.session_state.survey_responses.get('q4_confidence', 3),
                    'gen_ai_familiarity': st.session_state.survey_responses.get('q5a_gen_ai', 3),
                    'prompt_eng_familiarity': st.session_state.survey_responses.get('q5b_prompt', 3),
                    'cds_familiarity': st.session_state.survey_responses.get('q5c_cds', 3),
                    'llm_usage_frequency': st.session_state.survey_responses.get('q7_frequency', ''),
                    'trust_level': st.session_state.survey_responses.get('q9_trust', 3),
                }
                
                # Print values for debugging
                print("Survey data being submitted:")
                for key in ['specialization']:
                    print(f"  {key}: '{survey_data.get(key, '')}'")

                # Ensure all fields are properly converted to strings
                for key, value in survey_data.items():
                    if value is None:
                        survey_data[key] = ''  # Convert None to empty string
                    elif not isinstance(value, str) and not isinstance(value, int) and not isinstance(value, float):
                        survey_data[key] = str(value)  # Convert other types to strings

                # Store using only DataStorage
                storage = DataStorage()
                storage.save_login_data(st.session_state.user_id, {
                    'model_type': st.session_state.selected_model_type,
                    'model_name': st.session_state.selected_model_name,
                    'group': st.session_state.group
                })
                storage.log_user(survey_data)

                # Log survey responses
                logger = EnhancedLogger()
                logger.log_interaction(
                    user_id=st.session_state.user_id,
                    action_type="SURVEY_COMPLETE",
                    task_id=0,
                    model_type=st.session_state.selected_model_type,
                    additional_data={'survey_data': survey_data}
                )
                
                # Route to appropriate chat page based on group
                if st.session_state.group == "A":
                    st.switch_page("pages/3_Chat_base.py")
                else:
                    st.switch_page("pages/3_Chat.py")

show_login_survey()