from dataclasses import dataclass
from typing import Dict, List, Optional
import streamlit as st
import streamlit_survey as ss
from datetime import datetime
from utils.data_storage import DataStorage  # Remove SurveyStorage import
from utils.id_manager import get_or_create_unique_id
from tracking.prompt_metrics import PromptMetrics
from tracking.highlight_metrics import HighlightMetrics

# Update custom CSS to include black text color
st.markdown("""
    <style>
        /* Task container text styling */
        div[data-testid="stMarkdownContainer"] p {
            font-size: 18px !important;
        }
            
    </style>
""", unsafe_allow_html=True)

@dataclass
class TaskState:
    task_number: int
    completed: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    survey_data: Optional[Dict] = None
    description: str = ""

class TaskManager:
    TASK_TITLES = {
        1: "Symptom Diagnosis",
        2: "Treatment Recommendation", 
        3: "Clinical Note Analysis"
    }

    TASK_DESCRIPTIONS = {
        1: """
Based on the clinical note, use PromptDoctor to determine the most likely diagnosis for the patient. Mark the task as completed as soon as you are content with the output of the tool.

**Clinical Note**: \n
The patient, a 45-year-old male, presents with chief complaints of right-sided chest pain and shortness of breath. He describes the pain as sharp and intermittent, exacerbated by movement or deep inspiration. The patient also reports experiencing fatigue for two weeks but denies fever, cough, or any recent travel.""",

        2: """
Based on the clinical note, use PromptDoctor to obtain adequate treatment options for the patient. Mark the task as completed as soon as you are content with the output of the tool.

**Clinical Note**:\n
The patient, an 82-year-old male, presents with community-acquired pneumonia (CAP) complicated by a history of chronic obstructive pulmonary disease (COPD). He reports moderate dyspnea, no fever, and no recent upper respiratory tract infections. The patient has previously been hospitalized for CAP and is on long-term oxygen therapy.""",

        3: {
            "A": """
Use PromptDoctor to analyze the following Clinical Note to obtain a concise summary of key findings and recommendations for future management. Mark the task as completed as soon as you are content with the output of the tool.

**Clinical Note**:\n
The patient, a 50-year-old female, has been followed in the cardiology clinic for symptomatic hypertrophic obstructive cardiomyopathy (HOCM) for three years. Her history includes controlled hypertension and hyperlipidemia. She now presents with new onset of palpitations and shortness of breath.""",
            
            "B": (
                # Introduction - keep as regular text
                """Use PromptDoctor to analyze the following Clinical Note to obtain a concise summary of key findings and recommendations for future management. Mark the task as completed as soon as you are content with the output of the tool.""",
                
                # Clinical note - wrap in styled div with highlighted terms
                f"""
                <div class="clinical-note">
                    <strong>Clinical Note:</strong><br><br>
                    <div style="line-height: 1.6;">
                        The patient, a 50-year-old <span class="highlight-red" title="Impact: +0.125">female,</span> 
                        has been followed <span class="highlight-blue" title="Impact: -0.076">in</span> 
                        the cardiology <span class="highlight-blue" title="Impact: -0.034">clinic</span> 
                        for symptomatic hypertrophic obstructive cardiomyopathy (HOCM) for three 
                        <span class="highlight-blue" title="Impact: -0.152">years.</span> 
                        Her history <span class="highlight-red" title="Impact: +0.102">includes</span> 
                        controlled hypertension and <span class="highlight-red" title="Impact: +0.119">hyperlipidemia.</span> 
                        <span class="highlight-blue" title="Impact: -0.152">She</span> now presents with new onset of 
                        <span class="highlight-red" title="Impact: +0.163">palpitations</span> and 
                        <span class="highlight-red" title="Impact: +0.178">shortness</span> of 
                        <span class="highlight-red" title="Impact: +0.106">breath.</span>
                    </div>
                </div>""",
                
                # Explanation legend - wrap in styled div
                """
                <div class="highlight-explanation">
                    <span class="highlight-legend-red">Red highlights</span> show the words with the highest impact on the model's answer. They boost its confidence the most.<br>
                    <span class="highlight-legend-blue">Blue highlights</span> show the words with the lowest impact. They lower its confidence the most.
                </div>
                """
            )
        }

    }
    
    def __init__(self, total_tasks: int):
        self.highlight_metrics = HighlightMetrics()
        if 'task_states' not in st.session_state:
            st.session_state.task_states = [
                TaskState(i, description=self.TASK_DESCRIPTIONS[i]) 
                for i in range(1, total_tasks + 1)
            ]
            st.session_state.current_task = 1
            st.session_state.show_task_intro = True
            st.session_state.show_feedback = False
            st.session_state.task_complete_clicked = False
            # Initialize prompt tracking
            st.session_state.task_prompts = {i: [] for i in range(1, total_tasks + 1)}
            
        # Add global styles once during initialization
        st.markdown("""
            <style>
                /* Existing styles */
                .clinical-note {
                    line-height: 1.8;
                    font-size: 16px;
                    margin: 15px 0;
                    padding: 15px;
                    background-color: white;
                    border-radius: 8px;
                    border: 1px solid #eee;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                
                /* Add highlight styles */
                .highlight-red {
                    display: inline-block;
                    padding: 2px 4px;
                    margin: 0 2px;
                    border-radius: 3px;
                    background-color: rgba(220, 53, 69, 0.37);
                    color: black;
                    font-weight: 500;
                }
                .highlight-blue {
                    display: inline-block;
                    padding: 2px 4px;
                    margin: 0 2px;
                    border-radius: 3px;
                    background-color: rgba(0, 123, 255, 0.22);
                    color: black;
                    font-weight: 500;
                }
                .highlight-legend-red {
                    color: rgb(220, 53, 69);
                    font-weight: 600;
                }
                .highlight-legend-blue {
                    color: rgb(0, 123, 255);
                    font-weight: 600;
                }
                .highlight-explanation {
                    margin-top: 15px;
                    line-height: 1.6;
                    font-size: 16px;
                }
            </style>
        """, unsafe_allow_html=True)

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
        
        # Get final prompt from task prompts
        prompts = st.session_state.task_prompts.get(task_number, [])
        if prompts:
            final_prompt = prompts[-1]
            
            # Calculate and store prompt metrics
            metrics = PromptMetrics().analyze_prompts(prompts)
            storage = DataStorage()
            storage.save_prompt_metrics(
                st.session_state.user_id,
                task_number,
                st.session_state.get('group', 'A'),
                {
                    'prompt_count': metrics.prompt_count,
                    'first_prompt': metrics.first_prompt,
                    'last_prompt': metrics.last_prompt,
                    'levenshtein_distance': metrics.levenshtein_distance,
                    'word_count': metrics.word_count,
                    'timestamp': metrics.timestamp.isoformat()
                }
            )
            
            # Calculate and store highlight coverage metrics
            highlight_coverage = self.highlight_metrics.calculate_coverage(task_number, final_prompt)
            if highlight_coverage:
                storage.save_highlight_metrics(
                    st.session_state.user_id,
                    task_number,
                    st.session_state.get('group', 'A'),
                    highlight_coverage
                )
        
        # Move to next task if not the last one
        if task_number < len(st.session_state.task_states):
            st.session_state.current_task = task_number + 1
            # Reset states for next task
            st.session_state.stage = "user"  # Add this line
            st.session_state.messages = []
            st.session_state.message_feedback = {}
            st.session_state.show_task_intro = True
            st.session_state.show_feedback = False
            st.session_state.feedback_submitted = {}  # Add this line
            if "task_complete_clicked" in st.session_state:
                del st.session_state.task_complete_clicked
            if "task_ready_for_completion" not in st.session_state:
                st.session_state.task_ready_for_completion = True
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
        
        progress = (len([t for t in st.session_state.task_states if t.completed]) / 
                   len(st.session_state.task_states))
        st.sidebar.progress(progress, text=f"Progress: {int(progress * 100)}%")
        
        current_task = st.session_state.task_states[st.session_state.current_task - 1]
        task_title = self.TASK_TITLES[current_task.task_number]
        
        # Show task description with title only after task started
        if not st.session_state.get('show_task_intro', True):
            # Show title and task number in blue container
            st.sidebar.markdown(f"""
            <div style="
                padding: 1rem;
                border-radius: 0.5rem;
                background-color: rgb(231, 245, 255);
                margin-bottom: 1rem;
            ">
                <strong>Task {current_task.task_number}: {task_title}</strong><br>
                ({current_task.task_number} of {len(st.session_state.task_states)})
                
                {self._get_formatted_description(current_task)}
            </div>
            """, unsafe_allow_html=True)
            
            # Add hint box for group B (any task)
            if st.session_state.get('group', 'A') == 'B':
                st.sidebar.markdown("""
                <div style="
                    padding: 0.8rem;
                    border-radius: 0.5rem;
                    background-color: rgb(231, 245, 255);
                    border: 1px solid rgba(0, 123, 255, 0.2);
                    margin-bottom: 1rem;
                    font-size: 18px;
                ">
                     <strong>Hint:</strong> Terms highlighted in <span style="color: rgb(255, 75, 75);">red</span> could strongly influence the model's output.
                </div>
                """, unsafe_allow_html=True)
            
            # Add checkbox for task completion if messages exist and task is ready
            if len(st.session_state.get('messages', [])) >= 1:
                if st.sidebar.checkbox(
                    "✓ Mark task as complete",
                    key="task_complete_clicked",
                    help="Check this box when you are satisfied with the model output"
                ):
                    st.session_state.task_ready_for_completion = True

    def _get_formatted_description(self, task):
        """Helper to format task description based on task number and group"""
        if task.task_number == 3:
            group = st.session_state.get('group', 'A')
            if group == 'B':
                intro, clinical_note, explanation = self.TASK_DESCRIPTIONS[3]['B']
                is_sidebar = len(st.session_state.get('messages', [])) > 0
                
                if is_sidebar:
                    return (
                        f"{intro}\n\n"
                        f"{clinical_note}\n\n"
                        f"{explanation}"
                    )
                else:
                    # Full version with proper HTML structure and consistent styling
                    return f"""
                        <div class="task-wrapper">
                            <div class="task-intro">
                                {intro.strip()}
                            </div>
                            <div class="clinical-note">
                                {clinical_note.strip()}
                            </div>
                            <div class="highlight-explanation">
                                {explanation.strip()}
                            </div>
                        </div>
                    """
            return self.TASK_DESCRIPTIONS[3]['A']
        return self.TASK_DESCRIPTIONS[task.task_number]
    
    def render_task_controls(self):
        """Render task intro in chat UI"""
        current_task = st.session_state.task_states[st.session_state.current_task - 1]
        task_title = self.TASK_TITLES[current_task.task_number]
        
        # Show initial task intro only before task starts
        if st.session_state.get('show_task_intro', False):
            if current_task.task_number == 3:
                group = st.session_state.get('group', 'A')
                description = self._get_formatted_description(current_task)
            else:
                description = self.TASK_DESCRIPTIONS[current_task.task_number]
            
            st.markdown(
                f"""
                <div style="
                    padding: 1rem;
                    border-radius: 0.5rem;
                    background-color: rgb(231, 245, 255);
                    margin-bottom: 1rem;
                ">
                    <h3>Task {current_task.task_number}: {task_title}</h3>
                    {description}
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            if st.button("Start Task", key=f"start_task_{current_task.task_number}"):
                st.session_state.show_task_intro = False
                st.rerun()

    def show_task_survey(self, task_number: int) -> Optional[Dict]:
        """Check if survey should be shown and return data if submitted"""
        if "user_id" not in st.session_state:
            print("[ERROR] No user ID in session state")
            return None
            
        task = st.session_state.task_states[task_number - 1]
        if (task.completed or 
            len(st.session_state.messages) < 2 or 
            not st.session_state.get('task_complete_clicked', False) or
            not st.session_state.get('task_ready_for_completion', False)):
            return None

        # Initialize survey page state if not exists
        survey_key = f"survey_task_{task_number}"
        if survey_key not in st.session_state:
            st.session_state[survey_key] = ss.StreamlitSurvey(f"TaskSurvey_{task_number}")
        
        # Get or create survey instance
        survey = st.session_state[survey_key]
        pages = survey.pages(3, on_submit=lambda: None)

        st.write(f"### Task {task_number} Feedback")
        st.progress((pages.current + 1) / 3, text=f"Page {pages.current + 1} of 3")

        survey_data = {}

        # Handle each page content
        # Page 1: Task Experience
        if pages.current == 0:
            st.write("#### Section A: Task Experience")
            
            q1a_difficulty = st.radio(
                "How difficult was it to write your prompt to get a clinically appropriate output?",
                options=["1 - Very Easy", "2 - Somewhat Easy", "3 - Moderate", 
                        "4 - Somewhat Difficult", "5 - Very Difficult"],
                index=2,
                horizontal=False
            ).split(" - ")[0]
            
            q1b_mental = st.radio(
                "Mental Demand: How mentally demanding was the task?",
                options=["1 - Very Low", "2 - Low", "3 - Moderate", 
                        "4 - High", "5 - Very High"],
                index=2,
                horizontal=False
            ).split(" - ")[0]
            
            q1c_frustration = st.radio(
                "Frustration: How insecure, discouraged, stressed or annoyed were you?",
                options=["1 - Very Low", "2 - Low", "3 - Moderate", 
                        "4 - High", "5 - Very High"],
                index=2,
                horizontal=False
            ).split(" - ")[0]

            survey_data = {
                "timestamp": datetime.now().isoformat(),
                "user_id": st.session_state.user_id,
                "task_number": task_number,
                "difficulty": int(q1a_difficulty),
                "mental_demand": int(q1b_mental),
                "frustration": int(q1c_frustration)
            }

        # Page 2: Clinical Accuracy
        elif pages.current == 1:
            st.write("#### Section B: Clinical Accuracy")
            
            q2a_accuracy = st.radio(
                "How accurate or clinically appropriate was the model's final answer for this task?",
                options=["1 - Not at all accurate", "2 - Slightly accurate", 
                        "3 - Moderately accurate", "4 - Very accurate", "5 - Extremely accurate"],
                index=2,
                horizontal=False
            ).split(" - ")[0]
            
            q2b_task = st.radio(
                "The model's answer helped me accomplish the task.",
                options=["1 - Strongly disagree", "2 - Somewhat disagree", 
                        "3 - Neither agree nor disagree", "4 - Somewhat agree", "5 - Strongly agree"],
                index=2,
                horizontal=False
            ).split(" - ")[0]
            
            q2c_expectation = st.radio(
                "The model's answer matched what I expected.",
                options=["1 - Strongly disagree", "2 - Somewhat disagree",
                        "3 - Neither agree nor disagree", "4 - Somewhat agree", "5 - Strongly agree"],
                index=2,
                horizontal=False
            ).split(" - ")[0]

            survey_data.update({
                "accuracy": int(q2a_accuracy),
                "task_accomplishment": int(q2b_task),
                "expectation_match": int(q2c_expectation)
            })

        # Page 3: Clinical Utility
        else:
            st.write("#### Section C: Clinical Utility")
            
            q3a_usefulness = st.radio(
                "Would you consider the model's response useful in a real clinical scenario?",
                options=["1 - Not at all useful", "2 - Slightly useful", 
                        "3 - Moderately useful", "4 - Very useful", "5 - Extremely useful"],
                index=2,
                horizontal=False
            ).split(" - ")[0]
            
            q3b_inaccuracies = st.text_area(
                "Please describe any medically inaccurate or concerning aspects of the output:",
                placeholder="Optional: List specific medical inaccuracies, inconsistencies, or concerns..."
            )

            survey_data.update({
                "clinical_usefulness": int(q3a_usefulness),
                "medical_inaccuracies": q3b_inaccuracies or ""  # Ensure empty string if None
            })

        # Navigation buttons at bottom with equal width
        st.write("")  # Add spacing
        col1, col2 = st.columns(2)
        with col1:
            if pages.current > 0:
                if st.button("← Previous", key=f"prev_btn_{task_number}_{pages.current}", use_container_width=True):
                    pages.previous()
                    st.rerun()
        with col2:
            if pages.current < 2:  # Not last page
                if st.button("Next →", key=f"next_btn_{task_number}_{pages.current}", type="primary", use_container_width=True):
                    pages.next()
                    st.rerun()
            else:  # Last page
                if st.button("Submit & Continue", key=f"submit_btn_{task_number}", type="primary", use_container_width=True):
                    survey_data["timestamp"] = datetime.now().isoformat()
                    storage = DataStorage()
                    storage.save_task_survey(
                        st.session_state.user_id,
                        task_number,
                        survey_data
                    )
                    return survey_data

        return None

    def complete_task(self, task_number: int, survey_data: Dict) -> None:
        """Complete task and handle state transition"""
        task = st.session_state.task_states[task_number - 1]
        task.completed = True 
        task.completed_at = datetime.now()
        task.survey_data = survey_data
        
        # Get final prompt from task prompts
        prompts = st.session_state.task_prompts.get(task_number, [])
        if prompts:
            final_prompt = prompts[-1]
            
            # Calculate and store prompt metrics
            metrics = PromptMetrics().analyze_prompts(prompts)
            storage = DataStorage()
            storage.save_prompt_metrics(
                st.session_state.user_id,
                task_number,
                st.session_state.get('group', 'A'),
                {
                    'prompt_count': metrics.prompt_count,
                    'first_prompt': metrics.first_prompt,
                    'last_prompt': metrics.last_prompt,
                    'levenshtein_distance': metrics.levenshtein_distance,
                    'word_count': metrics.word_count,
                    'timestamp': metrics.timestamp.isoformat()
                }
            )
            
            # Calculate and store highlight coverage metrics
            highlight_coverage = self.highlight_metrics.calculate_coverage(task_number, final_prompt)
            if highlight_coverage:
                storage.save_highlight_metrics(
                    st.session_state.user_id,
                    task_number,
                    st.session_state.get('group', 'A'),
                    highlight_coverage
                )
        
        # Move to next task if not the last one
        if task_number < len(st.session_state.task_states):
            st.session_state.current_task = task_number + 1
            # Reset states for next task
            st.session_state.stage = "user"  # Add this line
            st.session_state.messages = []
            st.session_state.message_feedback = {}
            st.session_state.show_task_intro = True
            st.session_state.show_feedback = False
            st.session_state.feedback_submitted = {}  # Add this line
            if "task_complete_clicked" in st.session_state:
                del st.session_state.task_complete_clicked
            if "task_ready_for_completion" not in st.session_state:
                st.session_state.task_ready_for_completion = True
        else:
            st.switch_page("pages/4_Logout.py")
        
    def render_progress_sidebar(self):
        """Render progress tracking and task completion in sidebar"""
        st.sidebar.markdown("### Task Progress")
        
        progress = (len([t for t in st.session_state.task_states if t.completed]) / 
                   len(st.session_state.task_states))
        st.sidebar.progress(progress, text=f"Progress: {int(progress * 100)}%")
        
        current_task = st.session_state.task_states[st.session_state.current_task - 1]
        task_title = self.TASK_TITLES[current_task.task_number]
        
        # Show task description with title only after task started
        if not st.session_state.get('show_task_intro', True):
            # Show title and task number in blue container
            st.sidebar.markdown(f"""
            <div style="
                padding: 1rem;
                border-radius: 0.5rem;
                background-color: rgb(231, 245, 255);
                margin-bottom: 1rem;
            ">
                <strong>Task {current_task.task_number}: {task_title}</strong><br>
                ({current_task.task_number} of {len(st.session_state.task_states)})
                
                {self._get_formatted_description(current_task)}
            </div>
            """, unsafe_allow_html=True)
            
            # Add hint box for group B (any task)
            if st.session_state.get('group', 'A') == 'B':
                st.sidebar.markdown("""
                <div style="
                    padding: 0.8rem;
                    border-radius: 0.5rem;
                    background-color: rgb(231, 245, 255);
                    border: 1px solid rgba(0, 123, 255, 0.2);
                    margin-bottom: 1rem;
                    font-size: 18px;
                ">
                     <strong>Hint:</strong> Terms highlighted in <span style="color: rgb(255, 75, 75);">red</span> could strongly influence the model's output.
                </div>
                """, unsafe_allow_html=True)
            
            # Add checkbox for task completion if messages exist and task is ready
            if len(st.session_state.get('messages', [])) >= 1:
                if st.sidebar.checkbox(
                    "✓ Mark task as complete",
                    key="task_complete_clicked",
                    help="Check this box when you are satisfied with the model output"
                ):
                    st.session_state.task_ready_for_completion = True

    def _get_formatted_description(self, task):
        """Helper to format task description based on task number and group"""
        if task.task_number == 3:
            group = st.session_state.get('group', 'A')
            if group == 'B':
                intro, clinical_note, explanation = self.TASK_DESCRIPTIONS[3]['B']
                is_sidebar = len(st.session_state.get('messages', [])) > 0
                
                if is_sidebar:
                    return (
                        f"{intro}\n\n"
                        f"{clinical_note}\n\n"
                        f"{explanation}"
                    )
                else:
                    # Full version with proper HTML structure and consistent styling
                    return f"""
                        <div class="task-wrapper">
                            <div class="task-intro">
                                {intro.strip()}
                            </div>
                            <div class="clinical-note">
                                {clinical_note.strip()}
                            </div>
                            <div class="highlight-explanation">
                                {explanation.strip()}
                            </div>
                        </div>
                    """
            return self.TASK_DESCRIPTIONS[3]['A']
        return self.TASK_DESCRIPTIONS[task.task_number]
    
    def render_task_controls(self):
        """Render task intro in chat UI"""
        current_task = st.session_state.task_states[st.session_state.current_task - 1]
        task_title = self.TASK_TITLES[current_task.task_number]
        
        # Show initial task intro only before task starts
        if st.session_state.get('show_task_intro', False):
            if current_task.task_number == 3:
                group = st.session_state.get('group', 'A')
                description = self._get_formatted_description(current_task)
            else:
                description = self.TASK_DESCRIPTIONS[current_task.task_number]
            
            st.markdown(
                f"""
                <div style="
                    padding: 1rem;
                    border-radius: 0.5rem;
                    background-color: rgb(231, 245, 255);
                    margin-bottom: 1rem;
                ">
                    <h3>Task {current_task.task_number}: {task_title}</h3>
                    {description}
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            if st.button("Start Task", key=f"start_task_{current_task.task_number}"):
                st.session_state.show_task_intro = False
                st.rerun()
