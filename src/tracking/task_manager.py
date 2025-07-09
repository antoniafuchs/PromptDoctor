from dataclasses import dataclass
from typing import Dict, List, Optional
import streamlit as st
import streamlit_survey as ss
import inspect
from datetime import datetime
import logging
from src.core.data_storage import DataStorage
from src.core.id_manager import get_or_create_unique_id
from src.tracking.metrics.prompt_metrics import PromptMetrics
from src.tracking.metrics.highlight_metrics import HighlightMetrics
import os
import json

# Configure logging
logger = logging.getLogger(__name__)

# Update custom CSS to include black text color
st.markdown("""
    <style>
        /* Task container text styling */
        div[data-testid="stMarkdownContainer"] p {
            font-size: 18px !important;
        }
        
        /* Clinical note specific styling */
        .clinical-note p, .clinical-note div, .clinical-note span {
            font-size: 18px !important;
        }
            
        /* Survey question styling */
        div[data-testid="stMarkdownContainer"] label, 
        div[data-testid="stForm"] label,
        div[data-testid="stRadio"] label,
        div[data-testid="stRadio"] div {
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
Use PromptDoctor to analyze the following clinical note to obtain a concise summary of key findings and recommendations for future management. Mark the task as completed as soon as you are content with the output of the tool.

**Clinical Note**:\n
The patient, a 50-year-old female, has been followed in the cardiology clinic for symptomatic hypertrophic obstructive cardiomyopathy (HOCM) for three years. Her history includes controlled hypertension and hyperlipidemia. She now presents with new onset of palpitations and shortness of breath.""",
            
            "B": (
                # Introduction - keep as regular text
                """Use PromptDoctor to analyze the following Clinical Note to obtain a concise summary of key findings and recommendations for future management. Mark the task as completed as soon as you are content with the output of the tool.""",
                
                # Clinical note HTML (updated with consistent highlight styling)
                """
                <div class="clinical-note" style="line-height: 1.8; font-size: 18px; margin: 15px 0; padding: 15px; background-color: white; border-radius: 8px; border: 1px solid #eee; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <strong>Clinical Note:</strong><br><br>
                    <div style="line-height: 1.6;">
                        The patient, a 50-year-old <span class="highlight-red" style="display: inline-block; padding: 2px 4px; margin: 0 2px; border-radius: 3px; background-color: rgba(220, 53, 69, 0.37); color: black; font-weight: 500;" title="Impact: +0.125">female,</span> 
                        has been followed <span class="highlight-blue" style="display: inline-block; padding: 2px 4px; margin: 0 2px; border-radius: 3px; background-color: rgba(0, 123, 255, 0.23); color: black; font-weight: 500;" title="Impact: -0.076">in</span> 
                        the cardiology <span class="highlight-blue" style="display: inline-block; padding: 2px 4px; margin: 0 2px; border-radius: 3px; background-color: rgba(0, 123, 255, 0.10); color: black; font-weight: 500;" title="Impact: -0.034">clinic</span> 
                        for symptomatic hypertrophic obstructive cardiomyopathy (HOCM) for three 
                        <span class="highlight-blue" style="display: inline-block; padding: 2px 4px; margin: 0 2px; border-radius: 3px; background-color: rgba(0, 123, 255, 0.45); color: black; font-weight: 500;" title="Impact: -0.152">years.</span> 
                        Her history <span class="highlight-red" style="display: inline-block; padding: 2px 4px; margin: 0 2px; border-radius: 3px; background-color: rgba(220, 53, 69, 0.30); color: black; font-weight: 500;" title="Impact: +0.102">includes</span> 
                        controlled hypertension and <span class="highlight-red" style="display: inline-block; padding: 2px 4px; margin: 0 2px; border-radius: 3px; background-color: rgba(220, 53, 69, 0.36); color: black; font-weight: 500;" title="Impact: +0.119">hyperlipidemia.</span> 
                        <span class="highlight-blue" style="display: inline-block; padding: 2px 4px; margin: 0 2px; border-radius: 3px; background-color: rgba(0, 123, 255, 0.46); color: black; font-weight: 500;" title="Impact: -0.152">She</span> now presents with new onset of 
                        <span class="highlight-red" style="display: inline-block; padding: 2px 4px; margin: 0 2px; border-radius: 3px; background-color: rgba(220, 53, 69, 0.49); color: black; font-weight: 500;" title="Impact: +0.163">palpitations</span> and 
                        <span class="highlight-red" style="display: inline-block; padding: 2px 4px; margin: 0 2px; border-radius: 3px; background-color: rgba(220, 53, 69, 0.53); color: black; font-weight: 500;" title="Impact: +0.178">shortness</span> of 
                        <span class="highlight-red" style="display: inline-block; padding: 2px 4px; margin: 0 2px; border-radius: 3px; background-color: rgba(220, 53, 69, 0.32); color: black; font-weight: 500;" title="Impact: +0.106">breath.</span>
                    </div>
                </div>
                """,
                
                # Explanation legend HTML
                """
                <div class="highlight-explanation" style="margin-top: 15px; line-height: 1.6; font-size: 18px;">
                    <span class="highlight-legend-red" style="color: rgb(220, 53, 69); font-weight: 600;">Red highlights</span> show the words with the highest impact on the model's answer. They boost its confidence the most.<br><br>
                    <span class="highlight-legend-blue" style="color: rgb(0, 123, 255); font-weight: 600;">Blue highlights</span> show the words with the lowest impact. They lower its confidence the most.<br><br>
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
            # Initialize prompt count per task
            st.session_state.prompt_counts = {i: 0 for i in range(1, total_tasks + 1)}
            
        # Add global styles once during initialization
        st.markdown("""
            <style>
                /* Existing styles */
                .clinical-note {
                    line-height: 1.8;
                    font-size: 18px !important; /* Updated from 16px to 18px */
                    margin: 15px 0;
                    padding: 15px;
                    background-color: white;
                    border-radius: 8px;
                    border: 1px solid #eee;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                
                /* Updated clinical note content text size */
                .clinical-note div, .clinical-note span, .clinical-note p, .clinical-note strong {
                    font-size: 18px !important;
                }
                
                /* Updated highlight styles with fixed opacity values */
                .highlight-red {
                    display: inline-block;
                    padding: 2px 4px;
                    margin: 0 2px;
                    border-radius: 3px;
                    background-color: rgba(220, 53, 69, 0.37);
                    color: black;
                    font-weight: 500;
                    font-size: 18px !important;
                }
                .highlight-blue {
                    display: inline-block;
                    padding: 2px 4px;
                    margin: 0 2px;
                    border-radius: 3px;
                    background-color: rgba(0, 123, 255, 0.22);
                    color: black;
                    font-weight: 500;
                    font-size: 18px !important;
                }
                .highlight-legend-red {
                    color: rgb(220, 53, 69);
                    font-weight: 600;
                    font-size: 18px !important;
                }
                .highlight-legend-blue {
                    color: rgb(0, 123, 255);
                    font-weight: 600;
                    font-size: 18px !important;
                }
                .highlight-explanation {
                    margin-top: 15px;
                    line-height: 1.6;
                    font-size: 18px !important;
                }
                
                /* Survey styling */
                div[data-testid="stMarkdownContainer"] p,
                div[data-testid="stRadio"] label,
                div[data-testid="stTextArea"] label {
                    font-size: 18px !important;
                }
            </style>
        """, unsafe_allow_html=True)

    def start_task(self, task_number: int) -> None:
        """Record the exact time when a task is started"""
        task = st.session_state.task_states[task_number - 1]
        # Record the precise start time 
        task.started_at = datetime.now()
        
        # Also log this start time to help with analysis
        storage = DataStorage()
        task_start_data = {
            'user_id': st.session_state.user_id,
            'task_id': task_number,
            'completion_status': 'started',
            'task_start': task.started_at.isoformat(),
            'timestamp': task.started_at.isoformat()
        }
        storage.log_task(task_start_data)
        
        st.session_state.current_task = task_number
        # Reset survey page for new task
        st.session_state[f"task_{task_number}_survey_page"] = 0
    
    def complete_task(self, task_number: int, survey_data: Dict) -> None:
        """Complete task and handle state transition"""
        task = st.session_state.task_states[task_number - 1]
        task.completed = True 
        task.completed_at = datetime.now()
        
        # Calculate task duration
        if task.started_at:
            duration_seconds = (task.completed_at - task.started_at).total_seconds()
        else:
            duration_seconds = 0.0
            
        # Add duration and prompt count to survey data
        survey_data['task_duration'] = duration_seconds
        survey_data['start_time'] = task.started_at.isoformat() if task.started_at else None
        survey_data['end_time'] = task.completed_at.isoformat() if task.completed_at else None
        prompt_count = st.session_state.prompt_counts.get(task_number, 0)
        survey_data['prompt_count'] = prompt_count
        
        # Store feedback data if available - this is where we need to ensure feedback is saved
        if hasattr(st.session_state, 'message_feedback') and st.session_state.message_feedback:
            survey_data['message_feedback'] = st.session_state.message_feedback
            
            # Also explicitly save each feedback entry to ensure it's recorded
            storage = DataStorage()
            for message_id, feedback_data in st.session_state.message_feedback.items():
                try:
                    # Ensure we have the necessary data for feedback
                    feedback_value = feedback_data.get('feedback_value')
                    if feedback_value is not None:
                        # Find the associated message content if available
                        original_prompt = ""
                        model_response = ""
                        
                        # Look through messages to find the corresponding content
                        if hasattr(st.session_state, 'messages'):
                            for msg in st.session_state.messages:
                                if msg.get('message_id') == message_id:
                                    if msg.get('role') == 'user':
                                        original_prompt = msg.get('content', '')
                                    elif msg.get('role') == 'assistant':
                                        model_response = msg.get('content', '')
                                        
                                # Also check if this is a response to the message we're looking for
                                elif msg.get('response_to') == message_id and msg.get('role') == 'assistant':
                                    model_response = msg.get('content', '')
                                    
                        # Create feedback data with all necessary information
                        complete_feedback_data = {
                            'feedback_value': feedback_value,
                            'timestamp': feedback_data.get('timestamp', datetime.now().isoformat()),
                            'original_prompt': original_prompt,
                            'model_response': model_response,
                            'task_id': task_number,
                            'group': st.session_state.get('group', 'A')
                        }
                        
                        # Save the feedback
                        storage.save_feedback(st.session_state.user_id, message_id, complete_feedback_data)
                        print(f"DEBUG - Saved feedback for message {message_id} in task {task_number}")
                except Exception as e:
                    print(f"ERROR - Failed to save feedback for message {message_id}: {str(e)}")
    
        # Store survey data
        task.survey_data = survey_data
        
        # Explicitly save the task survey data here to ensure it gets saved for all tasks
        storage = DataStorage()
        storage.save_task_survey(
            st.session_state.user_id,
            task_number,
            survey_data
        )
        
        # Get final prompt from task prompts
        prompts = st.session_state.task_prompts.get(task_number, [])
        if prompts:
            final_prompt = prompts[-1]
            
            # Try to get the model's final response from the messages
            final_response = ""
            if hasattr(st.session_state, 'messages') and st.session_state.messages:
                for msg in reversed(st.session_state.messages):
                    if msg.get('role') == 'assistant':
                        final_response = msg.get('content', '')
                        break
            
            # Create metrics data manually instead of using analyze_prompts
            storage = DataStorage()
            
            # Create metrics data dictionary with default values
            metrics_data = {
                'user_id': st.session_state.user_id,
                'task_id': task_number,
                'group': st.session_state.get('group', 'A'),
                'prompt_count': len(prompts),
                'first_prompt': prompts[0] if prompts else "",
                'last_prompt': final_prompt,
                'levenshtein_distance': 0,  # Default value
                'word_count': len(final_prompt.split()) if final_prompt else 0,
                'timestamp': datetime.now().isoformat(),
                'medical_term_count': 0,  # Default value
                'highlighted_terms': [],
                'diff_type': "none",
                'model_response': final_response  # Add the model response
            }
            
            # Explicitly track the final model response to ensure it's in the CSV
            # This is an important addition to fix the missing model responses
            if final_prompt and final_response:
                self.track_model_response(
                    task_number,
                    final_prompt,
                    final_response,
                    f"{st.session_state.user_id[:8]}_task{task_number}_final"
                )
            
            # Log a final interaction with the prompt and response
            try:
                interaction_data = {
                    'user_id': st.session_state.user_id,
                    'task_id': task_number,
                    'action_type': 'TASK_COMPLETION',
                    'event_type': 'INTERACTION',
                    'timestamp': datetime.now().isoformat(),
                    'original_prompt': final_prompt,
                    'model_response': final_response,  # Ensure model response is included
                    'message_id': f"{st.session_state.user_id[:8]}_task{task_number}_final",
                    'model_type': st.session_state.get('model_type', ''),
                    'model_name': st.session_state.get('model_name', ''),
                    'group': st.session_state.get('group', 'A'),
                    'duration_total': duration_seconds
                }
                storage.log_interaction(interaction_data)
            except Exception as e:
                print(f"ERROR - Failed to log final interaction: {str(e)}")
            
            # Save metrics using the DataStorage class with unified approach
            storage.save_prompt_metrics(
                st.session_state.user_id,
                task_number,
                st.session_state.get('group', 'A'),
                metrics_data
            )
            
            # Calculate and store highlight coverage metrics
            highlight_coverage = self.highlight_metrics.calculate_coverage(task_number, final_prompt)
            if highlight_coverage:
                # Create unified data for highlight metrics
                highlight_data = {
                    'user_id': st.session_state.user_id,
                    'task_id': task_number,
                    'group': st.session_state.get('group', 'A'),
                    'timestamp': datetime.now().isoformat(),
                    'action_type': 'HIGHLIGHT_METRICS',
                    'prompt_count': prompt_count,
                    'last_prompt': final_prompt,
                    'model_response': final_response,  # Add the model response
                    'medical_term_count': len(highlight_coverage.get('matched_terms', [])),
                    'highlighted_terms': highlight_coverage.get('matched_terms', []),
                }
                storage.save_unified_prompt_data(highlight_data)
                
                # For backward compatibility
                storage.save_highlight_metrics(
                    st.session_state.user_id,
                    task_number,
                    st.session_state.get('group', 'A'),
                    highlight_coverage
                )
            
            # Save prompt counts to the unified file
            storage.save_prompt_counts({
                'user_id': st.session_state.user_id,
                'group': st.session_state.get('group', 'A'),
                'task_id': task_number,
                'prompt_count': prompt_count,
                'timestamp': datetime.now().isoformat()
            })
            
            # Also save the entire chat history with all messages
            if hasattr(st.session_state, 'messages'):
                try:
                    storage.save_chat_history(
                        st.session_state.user_id,
                        task_number,
                        st.session_state.messages
                    )
                except Exception as e:
                    print(f"ERROR - Failed to save chat history: {str(e)}")
        
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

    def track_prompt_submission(self, task_number: int, prompt: str) -> None:
        """Track a prompt submission for the given task"""
        if task_number not in st.session_state.task_prompts:
            st.session_state.task_prompts[task_number] = []
            st.session_state.prompt_counts[task_number] = 0
            
        # Add to prompt history
        st.session_state.task_prompts[task_number].append(prompt)
        # Increment count
        st.session_state.prompt_counts[task_number] += 1
        
        # Store the current prompt count in the session state for validation
        st.session_state['current_prompt_count'] = st.session_state.prompt_counts[task_number]
        
        # Generate a consistent message ID for this prompt
        user_id = st.session_state.get('user_id', 'unknown')
        user_prefix = user_id[:8] if user_id else "unknown"
        prompt_count = st.session_state.prompt_counts[task_number]
        message_id = f"{user_prefix}_task{task_number}_prompt{prompt_count}"
        
        # Store in session state for validation and tracking
        st.session_state['current_message_id'] = message_id
        
        logger.info(f"Tracked prompt submission for task {task_number}, count: {prompt_count}, message_id: {message_id}")
    
    def track_model_response(self, task_number: int, prompt: str, response: str, message_id: str = None) -> None:
        """Track a model response for the given task and prompt"""
        # Use provided message_id or get from session state
        if not message_id and 'current_message_id' in st.session_state:
            message_id = st.session_state['current_message_id']
        
        # If we still don't have a message_id, generate one
        if not message_id:
            user_id = st.session_state.get('user_id', 'unknown')
            user_prefix = user_id[:8] if user_id else "unknown"
            prompt_count = st.session_state.prompt_counts.get(task_number, 0)
            message_id = f"{user_prefix}_task{task_number}_prompt{prompt_count}"
        
        # Generate response message ID
        response_message_id = f"{message_id}_response"
        
        # Preserve the original response (without sanitization) for accurate tracking
        original_response = response
        
        # Log interaction with model response included
        try:
            storage = DataStorage()
            
            # First, update any existing CHAT entries for this message
            update_data = {
                'user_id': st.session_state.get('user_id', 'unknown'),
                'task_id': task_number,
                'message_id': message_id,
                'model_response': original_response,  # Use original unsanitized response
                'timestamp': datetime.now().isoformat(),
                'model_type': st.session_state.get('model_type', ''),
                'model_name': st.session_state.get('model_name', ''),
                'group': st.session_state.get('group', 'A')
            }
            storage.update_chat_with_response(update_data)
            
            # Then log a MODEL_OUTPUT entry to ensure we have complete data
            interaction_data = {
                'user_id': st.session_state.get('user_id', 'unknown'),
                'task_id': task_number,
                'action_type': 'MODEL_OUTPUT',
                'event_type': 'INTERACTION',
                'timestamp': datetime.now().isoformat(),
                'original_prompt': prompt,
                'model_response': original_response,  # Use original unsanitized response
                'message_id': message_id,
                'response_message_id': response_message_id,
                'model_type': st.session_state.get('model_type', ''),
                'model_name': st.session_state.get('model_name', ''),
                'group': st.session_state.get('group', 'A'),
                'duration_generation': st.session_state.get('generation_duration', 0)
            }
            storage.log_interaction(interaction_data)
            
            # Also save a direct JSON file as backup
            try:
                # Save a backup of the raw model response as JSON
                chat_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'responses')
                os.makedirs(chat_dir, exist_ok=True)
                
                # Generate a safe filename
                user_id = st.session_state.get('user_id', 'unknown')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{user_id}_task{task_number}_{timestamp}.json"
                
                with open(os.path.join(chat_dir, filename), 'w', encoding='utf-8') as f:
                    json.dump({
                        'user_id': user_id,
                        'task_id': task_number,
                        'message_id': message_id,
                        'timestamp': datetime.now().isoformat(),
                        'model_response': original_response,
                        'prompt': prompt
                    }, f, indent=2, ensure_ascii=False)
            except Exception as backup_err:
                logger.error(f"Failed to save response backup: {str(backup_err)}")
            
            logger.info(f"Tracked model response for task {task_number}, message_id: {message_id}")
        except Exception as e:
            logger.error(f"Failed to track model response: {str(e)}")
            
            # Emergency direct save
            try:
                # Save a backup of the raw model response as JSON
                emergency_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'emergency_responses')
                os.makedirs(emergency_dir, exist_ok=True)
                
                # Generate a safe filename
                user_id = st.session_state.get('user_id', 'unknown')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"emergency_{user_id}_task{task_number}_{timestamp}.json"
                
                with open(os.path.join(emergency_dir, filename), 'w', encoding='utf-8') as f:
                    json.dump({
                        'user_id': user_id,
                        'task_id': task_number,
                        'message_id': message_id,
                        'timestamp': datetime.now().isoformat(),
                        'model_response': original_response,
                        'prompt': prompt,
                        'error': str(e)
                    }, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved emergency response backup for task {task_number}")
            except Exception as emergency_err:
                logger.error(f"Critical failure saving model response: {str(emergency_err)}")

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
            # Special case for Task 3 Group B in sidebar - use the actual highlighted version
            if current_task.task_number == 3 and st.session_state.get('group', 'A') == 'B':
                # Create a container for the task title and number
                st.sidebar.markdown(f"""
                <div style="
                    padding: 1rem;
                    border-radius: 0.5rem;
                    background-color: rgb(231, 245, 255);
                    margin-bottom: 1rem;
                ">
                    <strong>Task {current_task.task_number}: {task_title}</strong><br>
                    ({current_task.task_number} of {len(st.session_state.task_states)})
                </div>
                """, unsafe_allow_html=True)
                
                # Create a simplified but formatted clinical note with highlights
                st.sidebar.markdown("""
                **Task Description:**
                Use PromptDoctor to analyze the clinical note to obtain a concise summary of key findings and recommendations.
                """)
                
                # Use a modified version of the clinical note HTML with highlights
                # Extract just the clinical note part from the tuple
                _, clinical_note_html, _ = self.TASK_DESCRIPTIONS[3]['B']
                
                # Clean up the HTML to avoid any issues with closing tags and make it work in the sidebar
                clinical_note_html = clinical_note_html.replace('</div>', '<!-- closing div -->')
                clinical_note_html = clinical_note_html.replace('data-clipboard-text="</div>"', 'data-clipboard-text="closing div"')
                clinical_note_html = clinical_note_html.replace('<div data-testid="stMarkdownPre"', '<!-- removed markdown pre div')
                
                # Render the highlighted clinical note
                st.sidebar.markdown(clinical_note_html, unsafe_allow_html=True)
                
                # Add hint about highlights
                st.sidebar.markdown("""
                <div style="
                    padding: 0.8rem;
                    border-radius: 0.5rem;
                    background-color: rgb(231, 245, 255);
                    border: 1px solid rgba(0, 123, 255, 0.2);
                    margin-top: 1rem;
                    font-size: 16px;
                ">
                     <span style="color: rgb(220, 53, 69);">Red highlights</span> show the words with the highest impact on the model's answer. They boost its confidence the most.<br><br>
                    <span style="color: rgb(0, 123, 255);">Blue highlights</span> show the words with the lowest impact. They lower its confidence the most.
                </div>
                """, unsafe_allow_html=True)
            else:
                # Standard approach for other tasks
                description = self._get_formatted_description(current_task)
                st.sidebar.markdown(f"""
                <div style="
                    padding: 1rem;
                    border-radius: 0.5rem;
                    background-color: rgb(231, 245, 255);
                    margin-bottom: 1rem;
                ">
                    <strong>Task {current_task.task_number}: {task_title}</strong><br>
                    ({current_task.task_number} of {len(st.session_state.task_states)})
                    
                    {description}
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
                # For sidebar display only, use a simplified format for better display
                is_sidebar = "render_progress_sidebar" in [frame.function for frame in inspect.stack()]
                
                if is_sidebar:
                    # For sidebar, use a simplified plain text version without any HTML
                    return """
Use PromptDoctor to analyze the following Clinical Note to obtain a concise summary of key findings and recommendations for future management.

**Clinical Note**:
The patient, a 50-year-old female, has been followed in the cardiology clinic for symptomatic hypertrophic obstructive cardiomyopathy (HOCM) for three years. Her history includes controlled hypertension and hyperlipidemia. She now presents with new onset of palpitations and shortness of breath.
                    """
                # Handle the tuple of content parts - apply more thorough sanitization
                content_parts = list(self.TASK_DESCRIPTIONS[3]['B'])
                for i in range(len(content_parts)):
                    # Also fix the clipboard text that might contain </div>
                    content_parts[i] = content_parts[i].replace('</div>', '<!-- closing div -->')
                    content_parts[i] = content_parts[i].replace('data-clipboard-text="</div>"', 'data-clipboard-text="closing div"')
                    
                    # Remove all potential code block elements
                    code_elements = [
                        '<pre', '</pre>',
                        '<code', '</code>',
                        'data-testid="stMarkdownPre"',
                        'data-testid="stCode"',
                        'class="st-emotion-cache-',
                        'class="stCode',
                        'class="st-emotion-cache-1nqbjoj e1rzn78k2"',
                        'class="st-emotion-cache-v2jlfx e1rzn78k4"',
                        'class="st-emotion-cache-acwcvw e194bff05"',
                        'data-testid="stCodeCopyButton"'
                    ]
                    
                    for element in code_elements:
                        content_parts[i] = content_parts[i].replace(element, f'<!-- removed: {element} -->')
                    
                    # Also remove SVG elements that might appear in copy buttons
                    if '<svg' in content_parts[i] and '</svg>' in content_parts[i]:
                        svg_start = content_parts[i].find('<svg')
                        svg_end = content_parts[i].find('</svg>', svg_start) + 6
                        if svg_start >= 0 and svg_end > 0:
                            svg_content = content_parts[i][svg_start:svg_end]
                            content_parts[i] = content_parts[i].replace(svg_content, '<!-- removed svg -->')
                    
                return ''.join(content_parts)
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
                if group == 'B':
                    # Special handling for group B with highlights
                    intro, clinical_note, explanation = self.TASK_DESCRIPTIONS[3]['B']
                    
                    # Create a completely sanitized version of the HTML by rebuilding it
                    # Extract only the essential content and rebuild with proper structure
                    
                    # Step 1: Create the wrapper without any direct HTML from the original
                    st.markdown(
                        f"""
                        <div style="
                            padding: 1rem;
                            border-radius: 0.5rem;
                            background-color: rgb(231, 245, 255);
                            margin-bottom: 1rem;
                        ">
                            <h3>Task {current_task.task_number}: {task_title}</h3>
                            <p>{intro}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                    
                    # Step 2: Create a clean version of just the clinical note with properly closed tags
                    # First, extract just the spans with highlights
                    import re
                    
                    # Extract the main note content between the clinical-note div
                    note_content = re.search(r'<div class="clinical-note".*?>(.*?)</div>\s*</div>', 
                                            clinical_note, re.DOTALL)
                    
                    if note_content:
                        clean_note = note_content.group(1).strip()
                        
                        # Remove any stray closing divs
                        clean_note = re.sub(r'</div>\s*</div>', '', clean_note)
                        
                        # Create a fresh clinical note div with the extracted content
                        st.markdown(
                            f"""
                            <div class="clinical-note" style="line-height: 1.8; font-size: 18px; margin: 15px 0; padding: 15px; background-color: white; border-radius: 8px; border: 1px solid #eee; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                                {clean_note}
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                    else:
                        # Fallback if regex didn't match
                        st.markdown(
                            """
                            <div class="clinical-note" style="line-height: 1.8; font-size: 18px; margin: 15px 0; padding: 15px; background-color: white; border-radius: 8px; border: 1px solid #eee; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                                <strong>Clinical Note:</strong><br><br>
                                <div style="line-height: 1.6;">
                                    The patient, a 50-year-old female, has been followed in the cardiology clinic for symptomatic hypertrophic obstructive cardiomyopathy (HOCM) for three years. Her history includes controlled hypertension and hyperlipidemia. She now presents with new onset of palpitations and shortness of breath.
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    
                    # Step 3: Create a clean explanation section
                    explanation_content = re.search(r'<div class="highlight-explanation".*?>(.*?)</div>', 
                                                 explanation, re.DOTALL)
                    
                    if explanation_content:
                        clean_explanation = explanation_content.group(1).strip()
                        st.markdown(
                            f"""
                            <div class="highlight-explanation" style="margin-top: 15px; line-height: 1.6; font-size: 18px;">
                                {clean_explanation}
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                    else:
                        # Fallback for explanation
                        st.markdown(
                            """
                            <div class="highlight-explanation" style="margin-top: 15px; line-height: 1.6; font-size: 18px;">
                                <span class="highlight-legend-red" style="color: rgb(220, 53, 69); font-weight: 600;">Red highlights</span> show the words with the highest impact on the model's answer. They boost its confidence the most.<br><br>
                                <span class="highlight-legend-blue" style="color: rgb(0, 123, 255); font-weight: 600;">Blue highlights</span> show the words with the lowest impact. They lower its confidence the most.<br><br>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    # Group A - make sure we render the task description properly
                    description = self.TASK_DESCRIPTIONS[3]['A']
                    st.markdown(f"""
                    <div style="
                        padding: 1rem;
                        border-radius: 0.5rem;
                        background-color: rgb(231, 245, 255);
                        margin-bottom: 1rem;
                    ">
                        <h3>Task {current_task.task_number}: {task_title}</h3>
                        <p>{description}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Regular tasks (1 and 2)
                description = self.TASK_DESCRIPTIONS[current_task.task_number]
                # Use markdown with info styling instead of st.info
                st.markdown(f"""
                <div style="
                    padding: 1rem;
                    border-radius: 0.5rem;
                    background-color: rgb(231, 245, 255);
                    margin-bottom: 1rem;
                ">
                    <h3>Task {current_task.task_number}: {task_title}</h3>
                    {description}
                </div>
                """, unsafe_allow_html=True)
            
            if st.button("Start Task", key=f"start_task_{current_task.task_number}"):
                # When user clicks "Start Task", record the exact time
                self.start_task(current_task.task_number)
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
        
        # Initialize persistent survey data storage if not exists
        survey_data_key = f"survey_data_task_{task_number}"
        if survey_data_key not in st.session_state:
            st.session_state[survey_data_key] = {}
        
        # Get or create survey instance
        survey = st.session_state[survey_key]
        pages = survey.pages(3, on_submit=lambda: None)

        st.write(f"### Task {task_number} Feedback")
        st.progress((pages.current + 1) / 3, text=f"Page {pages.current + 1} of 3")
        
        # Add survey-specific styling
        st.markdown("""
        <style>
            /* Survey specific font size overrides */
            div[data-testid="stMarkdownContainer"] p,
            div[data-testid="stRadio"] label,
            div[data-testid="stRadio"] div,
            div[data-testid="stTextArea"] label,
            div[data-testid="stTextArea"] textarea {
                font-size: 18px !important;
            }
        </style>
        """, unsafe_allow_html=True)

        # Use the persistent survey data storage
        survey_data = st.session_state[survey_data_key]

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
                "How mentally demanding was the task?",
                options=["1 - Very Low", "2 - Low", "3 - Moderate", 
                        "4 - High", "5 - Very High"],
                index=2,
                horizontal=False
            ).split(" - ")[0]
            
            q1c_frustration = st.radio(
                "How insecure, discouraged, stressed or annoyed were you?",
                options=["1 - Very Low", "2 - Low", "3 - Moderate", 
                        "4 - High", "5 - Very High"],
                index=2,
                horizontal=False
            ).split(" - ")[0]

            # Update persistent survey data
            survey_data.update({
                "timestamp": datetime.now().isoformat(),
                "user_id": st.session_state.user_id,
                "task_number": task_number,
                "difficulty": int(q1a_difficulty),
                "mental_demand": int(q1b_mental),
                "frustration": int(q1c_frustration)
            })
            
            # Save to session state
            st.session_state[survey_data_key] = survey_data
            
            # Log the values for debugging
            print(f"DEBUG - Task {task_number} page 0 values (saved to persistent storage):")
            print(f"  difficulty: {survey_data['difficulty']}")
            print(f"  mental_demand: {survey_data['mental_demand']}")
            print(f"  frustration: {survey_data['frustration']}")

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

            # Update persistent survey data
            survey_data.update({
                "accuracy": int(q2a_accuracy),
                "task_accomplishment": int(q2b_task),
                "expectation_match": int(q2c_expectation)
            })
            
            # Save to session state
            st.session_state[survey_data_key] = survey_data
            
            # Log values for debugging
            print(f"DEBUG - Task {task_number} page 1 values (saved to persistent storage):")
            print(f"  accuracy: {survey_data['accuracy']}")
            print(f"  task_accomplishment: {survey_data['task_accomplishment']}")
            print(f"  expectation_match: {survey_data['expectation_match']}")

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
            
            # Initialize session state for text area if it doesn't exist
            inaccuracies_key = f"inaccuracies_task_{task_number}"
            if inaccuracies_key not in st.session_state:
                st.session_state[inaccuracies_key] = ""
                
            # Create a cached key for immediate storage
            cached_inaccuracies_key = f"cached_inaccuracies_task_{task_number}"
            
            # Use the session state value as the default value for the text area
            q3b_inaccuracies = st.text_area(
                "Please describe any medically inaccurate or concerning aspects of the output:",
                placeholder="Optional: List specific medical inaccuracies, inconsistencies, or concerns...",
                value=st.session_state[inaccuracies_key],
                key=f"inaccuracies_input_{task_number}",
                height=150
            )
            
            # Update session state with current value - store in multiple places for redundancy
            st.session_state[inaccuracies_key] = q3b_inaccuracies
            st.session_state[cached_inaccuracies_key] = q3b_inaccuracies

            # Update persistent survey data
            survey_data.update({
                "clinical_usefulness": int(q3a_usefulness),
                "medical_inaccuracies": q3b_inaccuracies or ""  # Ensure empty string if None
            })
            
            # Save to session state
            st.session_state[survey_data_key] = survey_data

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
                    # Save the current page data even when just moving to next page
                    # This ensures data is saved even if user doesn't complete the survey
                    if pages.current == 0:
                        # Log interim save for page 0
                        print(f"DEBUG - Saving interim data for task {task_number} page 0")
                        try:
                            storage = DataStorage()
                            interim_data = st.session_state[survey_data_key].copy()
                            interim_data['task_id'] = task_number  # Ensure task_id is set correctly
                            interim_data['completion_status'] = 'in_progress'
                            storage.log_task(interim_data)
                        except Exception as e:
                            print(f"ERROR - Failed to save interim data: {str(e)}")
                    elif pages.current == 1:
                        # Log interim save for page 1
                        print(f"DEBUG - Saving interim data for task {task_number} page 1")
                        try:
                            storage = DataStorage()
                            interim_data = st.session_state[survey_data_key].copy()
                            interim_data['task_id'] = task_number  # Ensure task_id is set correctly
                            interim_data['completion_status'] = 'in_progress'
                            storage.log_task(interim_data)
                        except Exception as e:
                            print(f"ERROR - Failed to save interim data: {str(e)}")
                            
                    pages.next()
                    st.rerun()
            else:  # Last page
                if st.button("Submit & Continue", key=f"submit_btn_{task_number}", type="primary", use_container_width=True):
                    # Get the accumulated survey data
                    complete_survey_data = st.session_state[survey_data_key]
                    
                    # Calculate duration and prompt count
                    if task.started_at:
                        duration_seconds = (datetime.now() - task.started_at).total_seconds()
                        complete_survey_data['task_duration'] = duration_seconds
                        complete_survey_data['start_time'] = task.started_at.isoformat()
                        complete_survey_data['end_time'] = datetime.now().isoformat()
                    
                    # Make sure to include text input data from all possible session state keys
                    inaccuracies_key = f"inaccuracies_task_{task_number}"
                    cached_inaccuracies_key = f"cached_inaccuracies_task_{task_number}"
                    
                    # Try multiple locations to get the value
                    inaccuracies_value = ""
                    if inaccuracies_key in st.session_state:
                        inaccuracies_value = st.session_state[inaccuracies_key]
                    elif cached_inaccuracies_key in st.session_state:
                        inaccuracies_value = st.session_state[cached_inaccuracies_key]
                    
                    complete_survey_data['medical_inaccuracies'] = inaccuracies_value or ""
                    
                    # Add prompt count
                    complete_survey_data['prompt_count'] = st.session_state.prompt_counts.get(task_number, 0)
                    complete_survey_data['timestamp'] = datetime.now().isoformat()
                    
                    # Ensure task_id is set correctly - this was missing and might cause issues
                    complete_survey_data['task_id'] = task_number
                    complete_survey_data['completion_status'] = 'completed'
                    
                    # Add model and group information
                    complete_survey_data['model_type'] = st.session_state.get('model_type', '')
                    complete_survey_data['model_name'] = st.session_state.get('model_name', '')
                    complete_survey_data['group'] = st.session_state.get('group', '')
                    
                    # Debug survey data before saving
                    print(f"DEBUG - Task {task_number} final survey data:")
                    for key in ['difficulty', 'mental_demand', 'frustration', 'accuracy', 'task_accomplishment', 'expectation_match', 'clinical_usefulness']:
                        print(f"  {key}: '{complete_survey_data.get(key, 'MISSING')}'")
                    print(f"  medical_inaccuracies: '{complete_survey_data.get('medical_inaccuracies', 'MISSING')}'")
                    
                    # Save survey data
                    storage = DataStorage()
                    try:
                        print(f"DEBUG - Saving task survey for task {task_number}")
                        storage.save_task_survey(
                            st.session_state.user_id,
                            task_number,
                            complete_survey_data
                        )
                        print(f"DEBUG - Task survey saved successfully for task {task_number}")
                    except Exception as e:
                        print(f"ERROR - Failed to save task survey: {str(e)}")
                        # Try emergency backup to dedicated folder
                        try:
                            emergency_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'emergency_backups')
                            os.makedirs(emergency_dir, exist_ok=True)
                            backup_path = os.path.join(emergency_dir, f"task_{task_number}_survey_backup_{st.session_state.user_id}.json")
                            with open(backup_path, 'w') as backup_file:
                                json.dump(complete_survey_data, backup_file)
                            print(f"DEBUG - Emergency backup saved to {backup_path}")
                        except Exception as e:
                            print(f"ERROR - Failed to save emergency backup: {str(e)}")
                            
                    # Mark task as complete
                    task = st.session_state.task_states[task_number - 1]
                    task.completed = True
                    task.completed_at = datetime.now()
                    
                    # Move to next task or finish
                    if task_number < len(st.session_state.task_states):
                        st.session_state.current_task = task_number + 1
                        st.session_state.show_task_intro = True
                        st.session_state.show_feedback = False
                        st.session_state.feedback_submitted = {}
                        if "task_complete_clicked" in st.session_state:
                            del st.session_state.task_complete_clicked
                        if "task_ready_for_completion" not in st.session_state:
                            st.session_state.task_ready_for_completion = True
                    else:
                        st.write("Thank you for completing all tasks!")
                        # Optionally, show a summary of responses or other final information
                        # For example, display all survey data collected
                        st.json(st.session_state.get('survey_data', {}))