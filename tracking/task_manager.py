from dataclasses import dataclass
from typing import Dict, List, Optional
import streamlit as st
from datetime import datetime

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
        1: "Analyze a patient's medical history and identify key symptoms",
        2: "Generate a differential diagnosis based on clinical findings",
        3: "Recommend appropriate follow-up tests and treatment plan"
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
    
    def complete_task(self, task_number: int, survey_data: Dict) -> None:
        task = st.session_state.task_states[task_number - 1]
        task.completed = True
        task.completed_at = datetime.now()
        task.survey_data = survey_data
    
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
        """Show feedback survey in chat UI"""
        print(f"[DEBUG] Showing survey for task {task_number}")
        print(f"[DEBUG] show_feedback: {st.session_state.get('show_feedback')}")
        print(f"[DEBUG] task_complete_clicked: {st.session_state.get('task_complete_clicked')}")
        
        if not st.session_state.get('show_feedback', False):
            print("[DEBUG] Survey not shown - show_feedback is False")
            return None
        
        if not st.session_state.get('task_complete_clicked', False):
            print("[DEBUG] Survey not shown - task_complete_clicked is False")
            return None
            
        # Show survey form
        with st.container():
            st.write(f"### Task {task_number} Feedback")
            difficulty = st.slider("Task difficulty", 1, 5, 3)
            usefulness = st.slider("Assistant helpfulness", 1, 5, 3)
            comments = st.text_area("Additional comments")
            
            if st.button("Submit & Continue", type="primary"):
                print("[DEBUG] Submit button clicked")
                survey_data = {
                    "difficulty": difficulty,
                    "usefulness": usefulness,
                    "comments": comments,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Update current task state
                print("[DEBUG] Completing current task...")
                current_task = st.session_state.task_states[task_number - 1]
                current_task.completed = True
                current_task.completed_at = datetime.now()
                current_task.survey_data = survey_data
                
                # Setup next task
                next_task = task_number + 1
                print(f"[DEBUG] Setting up next task {next_task}")
                
                if next_task <= len(st.session_state.task_states):
                    # Reset states for next task
                    st.session_state.current_task = next_task
                    st.session_state.show_task_intro = True
                    st.session_state.show_feedback = False
                    st.session_state.task_complete_clicked = False
                    st.session_state.messages = []
                    print(f"[DEBUG] States reset for task {next_task}")
                else:
                    print("[DEBUG] All tasks completed")
                    st.success("🎉 All tasks completed!")
                
                st.rerun()
                return survey_data
        
        return None
