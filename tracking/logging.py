from datetime import datetime
from typing import List, Dict
import difflib
from utils.data_storage import DataStorage

class EnhancedLogger:
    def __init__(self):
        self.storage = DataStorage()
        
    def log_user_session(self, user_id: str, group: str, survey_data: dict):
        """Log user session data including initial survey responses"""
        user_data = {
            'user_id': user_id,
            'group': group,
            'login_time': datetime.now().isoformat(),
            **survey_data
        }
        self.storage.log_user(user_data)
        
    def log_task_completion(self, user_id: str, task_id: int, survey_data: dict, duration: float):
        """Log task completion data"""
        task_data = {
            'user_id': user_id,
            'task_id': task_id,
            'completion_status': 'completed',
            'task_duration': duration,
            'timestamp': datetime.now().isoformat(),
            'task_start': survey_data.get('start_time'),
            'task_end': survey_data.get('end_time'),
            **survey_data  # Include all survey questions
        }
        self.storage.log_task(task_data)

    def log_interaction(self, user_id: str, action_type: str = None, task_id: int = None,
                       user_prompt: str = None, model_output: str = None, 
                       model_type: str = None, duration: dict = None,
                       additional_data: dict = None, **kwargs):
        """Log user interaction data"""
        interaction_data = {
            'user_id': user_id,
            'task_id': task_id,
            'action_type': action_type,
            'timestamp': datetime.now().isoformat(),
            'original_prompt': user_prompt,
            'model_response': model_output,
            'model_type': model_type
        }
        
        # Handle durations
        if duration:
            for timing_type, value in duration.items():
                interaction_data[f'duration_{timing_type}'] = value

        # Handle survey data if present
        if additional_data and 'survey_data' in additional_data:
            survey_data = additional_data.pop('survey_data')
            if isinstance(survey_data, dict):
                for section, data in survey_data.items():
                    if isinstance(data, dict):
                        interaction_data.update(data)

        # Add remaining data
        interaction_data.update(kwargs)
        if additional_data:
            interaction_data.update(additional_data)

        self.storage.log_interaction(interaction_data)

    def log_validation(self, user_id: str, task_id: int = None, action_type: str = None,
                      original_prompt: str = None, modified_prompt: str = None,
                      highlighted_terms: list = None, medical_term_count: int = None,
                      **kwargs):
        """Log prompt validation data"""
        # Only log VALIDATION_VIEW once per prompt
        if action_type == "VALIDATION_VIEW" and not modified_prompt:
            existing = self.storage.get_recent_validation(user_id, original_prompt)
            if existing and existing['action_type'] == "VALIDATION_VIEW":
                return  # Skip duplicate validation view
                
        validation_data = {
            'user_id': user_id,
            'task_id': task_id,
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'original_prompt': original_prompt,
            'modified_prompt': modified_prompt,
            'highlighted_terms': ','.join(highlighted_terms) if highlighted_terms else None,
            'medical_term_count': medical_term_count
        }
        self.storage.log_validation(validation_data)

    def log_final_survey(self, user_id: str, survey_data: dict):
        """Log final survey responses"""
        # Flatten nested survey data
        flattened_data = {'user_id': user_id}
        for section, items in survey_data.items():
            if isinstance(items, dict):
                for key, value in items.items():
                    flattened_data[f"{section}_{key}"] = value
            else:
                flattened_data[section] = items
        self.storage.log_survey(flattened_data)

    def log_feedback(self, user_id: str, task_id: int, message_id: str, 
                    feedback_value: int, prompt: str, response: str) -> None:
        """Log message feedback"""
        # Check if feedback already exists for this message
        existing = self.storage.get_message_feedback(user_id, message_id)
        if existing:
            return  # Skip if feedback already logged
            
        feedback_text = {
            1: "positive",
            -1: "negative",
            0: "neutral"
        }.get(feedback_value, "neutral")
        
        interaction_data = {
            'user_id': user_id,
            'task_id': task_id,
            'action_type': 'FEEDBACK',
            'timestamp': datetime.now().isoformat(),
            'original_prompt': prompt,
            'model_response': response,
            'feedback': feedback_text,
            'message_id': message_id
        }
        self.storage.log_interaction(interaction_data)

    def log_task_duration(self, user_id: str, task_id: int, duration: float) -> None:
        """Log task duration"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
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

def log_validation_action(*args, **kwargs):
    enhanced_logger.log_validation(*args, **kwargs)

def log_task_completion(*args, **kwargs):
    enhanced_logger.log_task_completion(*args, **kwargs)

def log_final_survey(*args, **kwargs):
    enhanced_logger.log_final_survey(*args, **kwargs)

def log_feedback(*args, **kwargs):
    enhanced_logger.log_feedback(*args, **kwargs)

def log_task_duration(user_id: str, task_id: int, duration: float) -> None:
    """Log task duration"""
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "action_type": "TASK_DURATION",
        "task_id": task_id,
        "duration": duration
    }
    _write_log_entry(log_data)

def log_lime_explanation(
    user_id: str,
    prompt: str,
    explanation_data: dict,
    task_id: int = None,
    model_type: str = None,
    duration: float = None
) -> None:
    """Log LIME explanation results"""
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "action_type": "LIME_EXPLANATION",
        "task_id": task_id,
        "prompt": prompt,
        "model_type": model_type,
        "duration": duration,
        "explanation": explanation_data
    }
    _write_log_entry(log_data)

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
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "action_type": "MODEL_OUTPUT",
        "task_id": task_id,
        "model_type": model_type,
        "prompt": prompt,
        "output": output,
        "duration": duration or {},
        "metadata": metadata or {}
    }
    _write_log_entry(log_data)

def log_user_interaction(
    user_id: str,
    action_type: str,
    metadata: dict = None,
    timestamp: datetime = None
) -> None:
    """Log generic user interaction"""
    log_data = {
        "timestamp": timestamp or datetime.now().isoformat(),
        "user_id": user_id,
        "action_type": action_type,
        "metadata": metadata or {}
    }
    _write_log_entry(log_data)

def _generate_diff(original: str, modified: str) -> str:
    """Generate a human-readable diff between two strings"""
    diff = difflib.ndiff(original.splitlines(keepends=True), 
                        modified.splitlines(keepends=True))
    return ''.join(diff)
