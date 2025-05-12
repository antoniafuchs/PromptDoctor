from dataclasses import dataclass
from typing import Dict, List, Optional
import streamlit as st
import streamlit_survey as ss
from datetime import datetime
from utils.survey_storage import SurveyStorage
from utils.id_manager import get_or_create_unique_id

@dataclass
class TaskState:
    task_number: int
    completed: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    survey_data: Optional[Dict] = None
    description: str = ""

class TaskManager:
    TASK_DESCRIPTIONS = {
        1: """Task 1: Symptom Diagnosis

Based on the clinical note, use PromptDoctor to determine the most likely diagnosis for the patient. Mark the task as completed as soon as you are content with the output of the tool.

Clinical Note:
The Patient, a 45-year-old male, presents with chief complaints of right-sided chest pain and shortness of breath. He describes the pain as sharp and intermittent, exacerbated by movement or deep inspiration. The patient also reports experiencing fatigue for two weeks but denies fever, cough, or any recent travel.""",

        2: """Task 2: Treatment Recommendation

Based on the clinical note, use PromptDoctor to obtain adequate treatment options for the patient. Mark the task as completed as soon as you are content with the output of the tool.

Clinical Note:
The Patient, an 82-year-old male, presents with community-acquired pneumonia (CAP) complicated by a history of chronic obstructive pulmonary disease (COPD). He reports moderate dyspnea, no fever, and no recent upper respiratory tract infections. The patient has previously been hospitalized for CAP and is on long-term oxygen therapy.""",

        3: """Task 3: Clinical Record Analysis

Use PromptDoctor to analyze the following clinical record to obtain a concise summary of key findings and recommendations for future management. Mark the task as completed as soon as you are content with the output of the tool.

Clinical Note:
The patient, a 50-year-old female, has been followed in the cardiology clinic for symptomatic hypertrophic obstructive cardiomyopathy (HOCM) for three years. Her history includes controlled hypertension and hyperlipidemia. She now presents with new onset of palpitations and shortness of breath."""
    }

    def __init__(self, total_tasks: int):
        if 'task_states' not in st.session_state:
            st.session_state.task_states = [
                TaskState(i, description=self.TASK_DESCRIPTIONS[i]) 
                for i in range(1, total_tasks + 1)
            ]
            st.session_state.current_task = 1
            st.session_state.show_task_intro = True
            st.session_state.show_feedback = False
            st.session_state.task_complete_clicked = False
    
    def start_task(self, task_number: int) -> None:
        task = st.session_state.task_states[task_number - 1]
        if not task.started_at:
            task.started_at = datetime.now()
        st.session_state.current_task = task_number
        # Reset survey page for new task
        st.session_state[f"task_{task_number}_survey_page"] = 0
    
    def complete_task(self, task_number: int, survey_data: Dict) -> None:
        """Complete task and handle state transition"""
        task = st.session_state.task_states[task_number - 1]
        task.completed = True 
        task.completed_at = datetime.now()
        task.survey_data = survey_data
        
        # Move to next task if not the last one
        if task_number < len(st.session_state.task_states):
            st.session_state.current_task = task_number + 1
            # Reset states for next task
            st.session_state.messages = []
            st.session_state.message_feedback = {}
            st.session_state.show_task_intro = True
            st.session_state.show_feedback = False
            st.session_state.task_complete_clicked = False
            st.session_state.stage = "user"
            st.session_state.pending_prompt = None
        else:
            st.switch_page("pages/4_Logout.py")
    
    def can_proceed_to_next(self) -> bool:
        """Check if user can proceed to next task"""
        return len(st.session_state.messages) >= 2  # At least one exchange

    def proceed_to_next_task(self) -> bool:
        """Attempt to proceed to next task. Returns True if successful."""
        if not self.can_proceed_to_next():
            return False
            
        current_task = st.session_state.task_states[st.session_state.current_task - 1]
        if st.session_state.current_task < len(st.session_state.task_states):
            st.session_state[f"show_survey_{st.session_state.current_task}"] = True
            current_task.completed = True
            current_task.completed_at = datetime.now()
            st.session_state.current_task += 1
            return True
        return False

    def render_progress_sidebar(self):
        """Render progress tracking and task completion in sidebar"""
        st.sidebar.markdown("### Task Progress")
        
        # Show progress bar
        progress = (len([t for t in st.session_state.task_states if t.completed]) / 
                   len(st.session_state.task_states))
        st.sidebar.progress(progress, text=f"Progress: {int(progress * 100)}%")
        
        current_task = st.session_state.task_states[st.session_state.current_task - 1]
        
        # Show task description
        st.sidebar.info(f"""
        **Task {current_task.task_number} of {len(st.session_state.task_states)}**
        
        {current_task.description}
        """)
        
        # Show completion checkbox after chat interaction
        if len(st.session_state.messages) >= 2 and not current_task.completed:
            task_completed = st.sidebar.checkbox(
                "✓ Mark task as completed",
                key=f"complete_task_{current_task.task_number}",
                help="Check this box when you've completed the current task"
            )
            
            if task_completed and not st.session_state.get('show_feedback', False):
                st.session_state.show_feedback = True
                st.session_state.task_complete_clicked = True
                st.rerun()

    def render_task_controls(self):
        """Render task intro in chat UI"""
        current_task = st.session_state.task_states[st.session_state.current_task - 1]
        
        # Show initial task intro
        if st.session_state.get('show_task_intro', False):
            st.info(f"""
            ### Welcome to Task {current_task.task_number}!
            
            {current_task.description}
            """)
            if st.button("Start Task", key=f"start_task_{current_task.task_number}"):
                st.session_state.show_task_intro = False
                st.rerun()

    def show_task_survey(self, task_number: int) -> Optional[Dict]:
        if "user_id" not in st.session_state:
            print("[ERROR] No user ID in session state")
            return None
            
        task = st.session_state.task_states[task_number - 1]
        if task.completed or len(st.session_state.messages) < 2 or not st.session_state.get('task_complete_clicked', False):
            return None

        # Initialize survey page state if not exists
        if f"task_{task_number}_survey_page" not in st.session_state:
            st.session_state[f"task_{task_number}_survey_page"] = 0

        # Initialize survey with correct starting page
        survey = ss.StreamlitSurvey("TaskSurvey")
        pages = survey.pages(3, on_submit=lambda: None, current_page=st.session_state[f"task_{task_number}_survey_page"])
        
        # Update the page state when navigation occurs
        st.session_state[f"task_{task_number}_survey_page"] = pages.current

        st.write(f"### Task {task_number} Feedback")
        st.progress((pages.current + 1) / 3, text=f"Page {pages.current + 1} of 3")
        
        survey_data = {}

        # Handle each page content
        # Page 1: Prompting Experience
        if pages.current == 0:
            st.write("#### Section A: Prompting Experience")
            
            q1a_difficulty = st.radio(
                "How difficult was it to write or refine your prompt to get an satisfying output?",
                options=["1 - Very easy", "2 - Somewhat easy", "3 - Moderate", "4 - Somewhat difficult", "5 - Very difficult"],
                horizontal=True
            ).split(" - ")[0]
            
            q1b_satisfaction = st.radio(
                "How satisfied are you with the AI's final output?",
                options=["1 - Not at all satisfied", "2 - Slightly satisfied", "3 - Moderately satisfied", "4 - Very satisfied", "5 - Extremely satisfied"],
                horizontal=True
            ).split(" - ")[0]
            
            q1c_understanding = st.radio(
                "How confident are you that the AI understood your request?",
                options=["1 - Not at all confident", "2 - Slightly confident", "3 - Moderately confident", "4 - Very confident", "5 - Extremely confident"],
                horizontal=True
            ).split(" - ")[0]

            survey_data.update({
                "q1a_difficulty": int(q1a_difficulty),
                "q1b_satisfaction": int(q1b_satisfaction),
                "q1c_understanding": int(q1c_understanding)
            })

        # Page 2: Cognitive Load
        elif pages.current == 1:
            st.write("#### Section B: Cognitive Load")
            st.write("Please rate the following aspects of your task experience:")
            
            q2a_mental = st.slider(
                "Mental Demand – How mentally demanding was the task?",
                min_value=1, max_value=7, value=4,
                help="1 = Very Low Mental Demand, 4 = Moderate, 7 = Very High Mental Demand"
            )
            
            q2b_temporal = st.slider(
                "Temporal Demand – How hurried or rushed did you feel?",
                min_value=1, max_value=7, value=4,
                help="1 = Very Relaxed Pace, 4 = Moderate Pace, 7 = Very Rushed"
            )
            
            q2c_effort = st.slider(
                "Effort – How hard did you have to work?",
                min_value=1, max_value=7, value=4,
                help="1 = Very Little Effort, 4 = Moderate Effort, 7 = Maximum Effort"
            )
            
            q2d_performance = st.slider(
                "Performance – How successful were you in completing the task?",
                min_value=1, max_value=7, value=4,
                help="1 = Poor Performance, 4 = Average Performance, 7 = Perfect Performance"
            )
            
            q2e_frustration = st.slider(
                "Frustration Level – How insecure, discouraged, stressed or annoyed were you?",
                min_value=1, max_value=7, value=4,
                help="1 = Very Low Frustration, 4 = Moderate Frustration, 7 = Very High Frustration"
            )

            survey_data.update({
                "q2a_mental": q2a_mental,
                "q2b_temporal": q2b_temporal,
                "q2c_effort": q2c_effort,
                "q2d_performance": q2d_performance,
                "q2e_frustration": q2e_frustration
            })

        # Page 3: Perceived Medical Quality
        else:
            st.write("#### Section C: Perceived Medical Quality")
            st.write("Please rate your agreement with the following statements:")
            
            q3a_accuracy = st.radio(
                "The model's output was medically accurate.",
                options=["1 - Strongly Disagree", "2 - Somewhat Disagree", "3 - Neutral", "4 - Somewhat Agree", "5 - Strongly Agree"],
                horizontal=True
            ).split(" - ")[0]
            
            q3b_professional = st.radio(
                "The model's output resembled advice from a medical professional.",
                options=["1 - Strongly Disagree", "2 - Somewhat Disagree", "3 - Neutral", "4 - Somewhat Agree", "5 - Strongly Agree"],
                horizontal=True
            ).split(" - ")[0]
            
            q3c_usefulness = st.radio(
                "The model's response was clinically useful.",
                options=["1 - Strongly Disagree", "2 - Somewhat Disagree", "3 - Neutral", "4 - Somewhat Agree", "5 - Strongly Agree"],
                horizontal=True
            ).split(" - ")[0]
            
            q3d_inaccuracies = st.text_area(
                "If any, what parts of the output were medically inaccurate?",
                placeholder="Optional: Describe any medical inaccuracies you noticed..."
            )

            survey_data.update({
                "q3a_accuracy": int(q3a_accuracy),
                "q3b_professional": int(q3b_professional),
                "q3c_usefulness": int(q3c_usefulness),
                "q3d_inaccuracies": q3d_inaccuracies
            })

        # Navigation buttons at bottom with equal width
        st.write("")  # Add spacing
        col1, col2 = st.columns(2)
        with col1:
            if pages.current > 0:
                if st.button("← Previous", use_container_width=True):
                    pages.previous()
                    st.rerun()
        with col2:
            if pages.current < 2:  # Not last page
                if st.button("Next →", type="primary", use_container_width=True):
                    pages.next()
                    st.rerun()
            else:  # Last page
                if st.button("Submit & Continue", type="primary", use_container_width=True):
                    survey_data["timestamp"] = datetime.now().isoformat()
                    survey_storage = SurveyStorage()
                    survey_storage.save_task_survey(
                        st.session_state.user_id,
                        task_number,
                        survey_data
                    )
                    return survey_data

        return None
