from datetime import datetime, timezone  # Updated to include timezone
import json
import os
import re
import pandas as pd
import streamlit as st
from typing import List, Dict
import difflib
import uuid
import logging
from utils.data_storage import DataStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'app.log'))
    ]
)
logger = logging.getLogger('promptdoctor')

class EnhancedLogger:
    def __init__(self):
        self.storage = DataStorage()
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        
    def _log_to_file(self, message: str) -> None:
        """Write a log message to the error log file"""
        try:
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            log_file = os.path.join(self.log_dir, 'error_log.txt')
            with open(log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            # Last resort fallback - print to console
            logger.error(f"Error writing to log file: {str(e)}")
            logger.error(f"Original message: {message}")
    
    def log_user_session(self, user_id: str, group: str, survey_data: dict):
        """Log user session data including initial survey responses"""
        user_data = {
            'user_id': user_id,
            'group': group,
            'login_time': datetime.now(timezone.utc).isoformat(),
            **survey_data
        }
        self.storage.log_user(user_data)
        
    def log_task_completion(self, user_id, task_id, survey_data, duration=0.0, **kwargs):
        """Log task completion with survey data"""
        # Import streamlit inside the function to ensure we get the actual streamlit module
        import streamlit as st
        
        log_data = {
            'event_type': 'TASK_COMPLETION',
            'user_id': user_id,
            'task_id': task_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'survey_data': survey_data,
            'duration': duration,
            'model_type': kwargs.get('model_type', st.session_state.get('selected_model_type', 'unknown')),
            'model_name': kwargs.get('model_name', st.session_state.get('selected_model_name', 'unknown')),
            'group': kwargs.get('group', st.session_state.get('group', 'A'))
        }
        
        # Store the task completion data
        try:
            # Save task completion data
            self.storage.log_task(log_data)
            
            # Also log as an interaction for consistency
            self.log_interaction(
                user_id=user_id,
                action_type="TASK_COMPLETION",
                task_id=task_id,
                duration={'total': duration},
                additional_data={'survey_data': survey_data},
                **kwargs
            )
        except Exception as e:
            self._log_to_file(f"Error logging task completion: {str(e)}")
            logger.error(f"Error logging task completion: {str(e)}")

    def log_interaction(self, user_id, action_type, **kwargs):
        """Log a user interaction with enhanced data"""
        # Create the log entry with proper datetime usage
        log_data = {
            'event_type': 'INTERACTION',
            'action': action_type,
            'user_id': user_id,
            'task_id': kwargs.get('task_id', st.session_state.get('current_task', 0)),
            'timestamp': datetime.now(timezone.utc).isoformat(),  # Using UTC timezone
            'user_prompt': kwargs.get('user_prompt', ''),
            'model_output': kwargs.get('model_output', ''),
            'model_type': kwargs.get('model_type', st.session_state.get('selected_model_type', 'unknown')),
            'model_name': kwargs.get('model_name', st.session_state.get('selected_model_name', 'unknown')),
            'group': kwargs.get('group', st.session_state.get('group', 'A')),
            'duration': kwargs.get('duration', {}),
            'additional_data': kwargs.get('additional_data', {})
        }
        
        # Explicitly handle modified_prompt if present
        if 'modified_prompt' in kwargs:
            log_data['modified_prompt'] = kwargs.get('modified_prompt')
            
        # Explicitly handle highlighted_terms if present
        if 'highlighted_terms' in kwargs:
            terms = kwargs.get('highlighted_terms')
            if isinstance(terms, list):
                log_data['highlighted_terms'] = ','.join(terms)
            else:
                log_data['highlighted_terms'] = terms
                
        # Explicitly handle diff_type if present
        if 'diff_type' in kwargs:
            log_data['diff_type'] = kwargs.get('diff_type')
        
        # Get duration from kwargs instead of using undefined variable
        duration_data = kwargs.get('duration', {})
        if duration_data:
            for timing_type, value in duration_data.items():
                log_data[f'duration_{timing_type}'] = value

        # Handle survey data if present
        additional_data = kwargs.get('additional_data', {})
        if additional_data and 'survey_data' in additional_data:
            survey_data = additional_data.pop('survey_data')
            if isinstance(survey_data, dict):
                for section, data in survey_data.items():
                    if isinstance(data, dict):
                        log_data.update(data)

        # Add remaining data
        log_data.update(kwargs)
        if additional_data:
            log_data.update(additional_data)

        self.storage.log_interaction(log_data)

    def log_validation(self, user_id: str, task_id: int = None, action_type: str = None,
                      original_prompt: str = None, modified_prompt: str = None,
                      highlighted_terms: list = None, medical_term_count: int = None,
                      diff_type: str = None, message_id: str = None, **kwargs):
        """Log prompt validation data with enhanced tracking"""
        # Only log VALIDATION_VIEW once per prompt
        if action_type == "VALIDATION_VIEW" and not modified_prompt:
            existing = self.storage.get_recent_validation(user_id, original_prompt)
            if existing and existing['action_type'] == "VALIDATION_VIEW":
                return  # Skip duplicate validation view
                
        validation_data = {
            'user_id': user_id,
            'task_id': task_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action_type': action_type,
            'original_prompt': original_prompt,
            'modified_prompt': modified_prompt,
            'highlighted_terms': ','.join(highlighted_terms) if highlighted_terms else None,
            'medical_term_count': medical_term_count,
            'diff_type': diff_type,
            'message_id': message_id or str(uuid.uuid4())  # Ensure message_id is always set
        }
        
        # Also log this to the interactions table to ensure consistency
        self.log_interaction(
            user_id=user_id,
            action_type=f"VALIDATION_{action_type}" if action_type else "VALIDATION",
            task_id=task_id,
            user_prompt=original_prompt,
            model_output=None,
            modified_prompt=modified_prompt,
            highlighted_terms=highlighted_terms,
            diff_type=diff_type,
            message_id=validation_data['message_id'],
            **kwargs
        )
        
        self.storage.log_validation(validation_data)

    def log_final_survey(self, user_id: str, survey_data: dict):
        """Log final survey responses"""
        # Flatten nested survey data
        flattened_data = {'user_id': user_id, 'timestamp': datetime.now(timezone.utc).isoformat()}
        for section, items in survey_data.items():
            if isinstance(items, dict):
                for key, value in items.items():
                    flattened_data[f"{section}_{key}"] = value
            else:
                flattened_data[section] = items
        self.storage.log_survey(flattened_data)

    def log_feedback(self, user_id: str, task_id: int, message_id: str, 
                    feedback_value: int, prompt: str = None, response: str = None) -> None:
        """Log user feedback on model responses"""
        try:
            # Check if feedback already exists
            existing = self.storage.get_message_feedback(user_id, message_id)
            if existing:
                # Skip if feedback already recorded
                return
                
            # Format feedback data
            feedback_data = {
                'feedback_value': feedback_value,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Save feedback using the dedicated method
            self.storage.save_feedback(user_id, message_id, feedback_data)
            
            # Also log as interaction for backwards compatibility
            self.storage.log_interaction({
                'user_id': user_id,
                'task_id': task_id,
                'message_id': message_id,
                'action_type': 'FEEDBACK',
                'original_prompt': prompt,
                'model_response': response,
                'feedback': feedback_value,
                'feedback_timestamp': datetime.now(timezone.utc).isoformat(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            # Use the _log_to_file method to log the error
            self._log_to_file(f"Error logging feedback: {str(e)}")
            logger.error(f"Error logging feedback: {str(e)}")
            
    def log_task_duration(self, user_id: str, task_id: int, duration: float) -> None:
        """Log task duration"""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "action_type": "TASK_DURATION",
            "task_id": task_id,
            "duration": duration
        }
        self.storage.log_task(log_data)

# Initialize global logger instance
enhanced_logger = EnhancedLogger()

# Only keep these clean global interfaces
def log_chat_interaction(*args, **kwargs):
    enhanced_logger.log_interaction(*args, **kwargs)

def log_validation_action(user_id, action_type, original_prompt, highlighted_terms=None, **kwargs):
    """Log validation actions"""
    # Import streamlit inside the function to ensure we get the actual streamlit module
    import streamlit as st
    
    # Get values from kwargs with defaults
    task_id = kwargs.get('task_id', st.session_state.get('current_task', 0))
    prompt_count = kwargs.get('prompt_count', 0)
    message_id = kwargs.get('message_id', '')
    modified_prompt = kwargs.get('modified_prompt', '')
    medical_term_count = kwargs.get('medical_term_count', 0)
    edit_distance = kwargs.get('edit_distance', 0)
    diff_type = kwargs.get('diff_type', '')
    
    log_data = {
        'event_type': 'VALIDATION',
        'action': action_type,
        'user_id': user_id,
        'task_id': task_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),  # Using UTC timezone
        'original_prompt': original_prompt,
        'modified_prompt': modified_prompt,
        'highlighted_terms': highlighted_terms,
        'medical_term_count': medical_term_count,
        'prompt_count': prompt_count,
        'message_id': message_id,
        'model_type': kwargs.get('model_type', st.session_state.get('selected_model_type', 'unknown')),
        'model_name': kwargs.get('model_name', st.session_state.get('selected_model_name', 'unknown')),
        'group': kwargs.get('group', st.session_state.get('group', 'A')),
        'edit_distance': edit_distance,
        'diff_type': diff_type
    }
    
    try:
        from utils.data_storage import DataStorage
        storage = DataStorage()
        
        # Use save_unified_prompt_data instead of save_validation_log
        storage.save_unified_prompt_data(log_data)
    except Exception as e:
        logger.error(f"Error logging validation action: {str(e)}")
        
    return log_data

def log_task_completion(*args, **kwargs):
    enhanced_logger.log_task_completion(*args, **kwargs)

def log_final_survey(*args, **kwargs):
    enhanced_logger.log_final_survey(*args, **kwargs)

def log_feedback(*args, **kwargs):
    enhanced_logger.log_feedback(*args, **kwargs)

def log_task_duration(user_id: str, task_id: int, duration: float) -> None:
    """Log task duration"""
    enhanced_logger.log_task_duration(user_id, task_id, duration)

def log_lime_explanation(
    user_id: str,
    prompt: str,
    explanation_data: dict,
    task_id: int = None,
    model_type: str = None,
    duration: float = None
) -> None:
    """Log LIME explanation results"""
    enhanced_logger.log_interaction(
        user_id=user_id, 
        action_type="LIME_EXPLANATION",
        task_id=task_id,
        user_prompt=prompt,
        model_output=None,
        model_type=model_type,
        duration={"total": duration} if duration else None,
        additional_data={"explanation_data": explanation_data}
    )

def log_model_output(
    user_id: str,
    task_id: int,
    model_type: str,
    prompt: str,
    output: str,
    duration: dict = None,
    metadata: dict = None
) -> None:
    """Log model generation output"""
    enhanced_logger.log_interaction(
        user_id=user_id,
        action_type="MODEL_OUTPUT",
        task_id=task_id,
        user_prompt=prompt,
        model_output=output,
        model_type=model_type,
        duration=duration,
        additional_data=metadata
    )

def log_user_interaction(
    user_id: str,
    action_type: str,
    metadata: dict = None,
    timestamp: datetime = None
) -> None:
    """Log generic user interaction"""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    enhanced_logger.log_interaction(
        user_id=user_id,
        action_type=action_type,
        additional_data=metadata,
        timestamp=timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
    )

# Helper functions for diff generation and analysis
def _generate_diff(original: str, modified: str) -> str:
    """Generate a human-readable diff between two strings"""
    diff = difflib.ndiff(original.splitlines(keepends=True), 
                        modified.splitlines(keepends=True))
    return ''.join(diff)

def _calculate_edit_distance(original: str, modified: str) -> float:
    """
    Calculate normalized Levenshtein distance between original and modified text
    Returns a value between 0.0 (identical) and 1.0 (completely different)
    """
    import Levenshtein
    
    # Handle edge cases
    if not original and not modified:
        return 0.0
    if not original or not modified:
        return 1.0
    
    # Calculate Levenshtein distance
    distance = Levenshtein.distance(original, modified)
    
    # Normalize by the length of the longer string
    max_length = max(len(original), len(modified))
    return distance / max_length if max_length > 0 else 0.0

def _determine_diff_type(original: str, modified: str) -> str:
    """
    Determine the type of difference between original and modified text
    Returns one of: "addition", "deletion", "replacement", "minor_change", "major_change"
    """
    # Calculate edit distance
    edit_distance = _calculate_edit_distance(original, modified)
    
    # Simple string length comparison
    len_diff = len(modified) - len(original)
    
    if edit_distance < 0.1:
        return "minor_change"
    elif edit_distance > 0.5:
        return "major_change"
    elif len_diff > 10:
        return "addition"
    elif len_diff < -10:
        return "deletion"
    else:
        return "replacement"
