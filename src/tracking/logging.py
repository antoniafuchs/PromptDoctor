"""
logging.py
This file provides logging functionality for PromptDoctor, including tracking user interactions and system events.
"""

import os
import sys
import json
import uuid
from datetime import datetime, timezone
import csv
import logging
import traceback
import difflib
from typing import Dict, List, Optional, Any, Union

# Add project root to path to fix import issues
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

# Fix imports to use absolute paths with src prefix
from src.core.data_storage import DataStorage
from src.core.id_manager import get_or_create_unique_id

# Configure logging with directory creation
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'app.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class EnhancedLogger:
    def __init__(self):
        self.storage = DataStorage()
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Verify storage is working on initialization
        self.verify_storage()
        
    def verify_storage(self) -> Dict[str, Any]:
        """Verify storage is working and return diagnostic information"""
        try:
            # Create a test diagnostic file to verify write permissions
            diag_file = os.path.join(self.log_dir, 'storage_diagnostics.log')
            with open(diag_file, 'a') as f:
                timestamp = datetime.now(timezone.utc).isoformat()
                f.write(f"[{timestamp}] Storage diagnostic check\n")
                
            # Check if critical directories exist and are writable
            data_dir = os.path.dirname(os.path.dirname(__file__))
            data_dir = os.path.join(data_dir, 'data')
            
            diagnostic_info = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "log_dir_exists": os.path.exists(self.log_dir),
                "log_dir_writable": os.access(self.log_dir, os.W_OK),
                "data_dir_exists": os.path.exists(data_dir),
                "data_dir_writable": os.access(data_dir, os.W_OK) if os.path.exists(data_dir) else False,
                "python_version": os.sys.version,
                "files_check": {}
            }
            
            # Check for critical CSV files
            critical_files = [
                os.path.join(data_dir, 'surveys.csv'),
                os.path.join(data_dir, 'tasks.csv'),
                os.path.join(data_dir, 'interactions.csv')
            ]
            
            for file_path in critical_files:
                file_name = os.path.basename(file_path)
                exists = os.path.exists(file_path)
                diagnostic_info["files_check"][file_name] = {
                    "exists": exists,
                    "size": os.path.getsize(file_path) if exists else 0,
                    "wable": os.access(file_path, os.W_OK) if exists else False,
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat() if exists else None
                }
            
            # Log diagnostic information
            self._log_to_file(f"Storage diagnostic results: {json.dumps(diagnostic_info, indent=2)}")
            logger.info(f"Storage diagnostic complete. Log dir: {self.log_dir}, Data dir: {data_dir}")
            
            return diagnostic_info
        except Exception as e:
            error_msg = f"Storage verification failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self._log_to_file(error_msg)
            return {"error": error_msg, "timestamp": datetime.now(timezone.utc).isoformat()}
        
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
        # Import streamlit inside the function to ensure we get the actual streamlit module
        import streamlit as st
        
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

    def log_feedback(self, user_id: str, task_id: int, message_id: str, 
              feedback_value: int, prompt: str = None, response: str = None,
              response_message_id: str = None) -> None:
        """Log user feedback on model responses"""
        try:
            # Debug info for troubleshooting
            logger.info(f"Logging feedback: user={user_id}, task={task_id}, message={message_id}, value={feedback_value}")
            
            # Create a structured message ID if not provided
            if not message_id or message_id.startswith("msg_"):
                # Extract first 8 chars of user_id for the prefix
                user_prefix = user_id[:8] if user_id else "unknown"
                # Use incrementing number or current timestamp if not available
                counter = datetime.now().strftime("%H%M%S")
                message_id = f"{user_prefix}_task{task_id}_prompt{counter}"
                logger.info(f"Generated structured message_id: {message_id}")
            
            # Create a structured response_message_id if not provided
            if not response_message_id and response:
                # Response message ID should link to the message it's responding to
                response_message_id = f"{message_id}_response"
                logger.info(f"Generated structured response_message_id: {response_message_id}")
            
            # Format feedback data
            feedback_data = {
                'feedback_value': feedback_value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'original_prompt': prompt,  # Store the original prompt
                'model_response': response,  # Store the model response
                'response_message_id': response_message_id  # Store explicit link to the response message
            }
            
            # Create storage instance
            storage = DataStorage()
            
            # Log as interaction directly without checking for existing feedback
            interaction_data = {
                'user_id': user_id,
                'task_id': task_id,
                'action_type': 'FEEDBACK',
                'message_id': message_id,  # ID of the message being rated
                'response_message_id': response_message_id,  # ID of the response this feedback is for
                'original_prompt': prompt,
                'model_response': response,  # Include the full model response
                'feedback': feedback_value,
                'feedback_timestamp': datetime.now(timezone.utc).isoformat(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            storage.log_interaction(interaction_data)
            
            # Also try to save using dedicated feedback method if available
            try:
                storage.save_feedback(user_id, message_id, feedback_data)
            except Exception as inner_e:
                # If save_feedback fails, we already logged via log_interaction above
                logger.warning(f"Secondary feedback save method failed: {str(inner_e)}")
                
            logger.info(f"Successfully logged feedback: message_id={message_id}, value={feedback_value}")
            
        except Exception as e:
            error_msg = f"Error logging feedback: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            
            # Try emergency direct logging as a last resort
            try:
                log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
                os.makedirs(log_dir, exist_ok=True)
                emergency_log = os.path.join(log_dir, 'emergency_feedback.log')
                with open(emergency_log, 'a') as f:
                    f.write(f"[{datetime.now(timezone.utc).isoformat()}] FEEDBACK ERROR: {error_msg}\n")
                    f.write(f"DATA: user_id={user_id}, task_id={task_id}, message_id={message_id}, value={feedback_value}\n")
                    f.write(f"RESPONSE_MESSAGE_ID: {response_message_id}\n")
                    if prompt:
                        f.write(f"PROMPT: {prompt[:100]}...\n")
                    if response:
                        f.write(f"RESPONSE: {response[:100]}...\n\n")
            except:
                pass
            
    def log_final_survey(self, user_id: str, survey_data: dict):
        """Log final survey responses with improved error handling"""
        try:
            # Debug survey data before flattening
            logger.info(f"Logging final survey for user_id={user_id} with {len(survey_data)} sections")
            self._log_to_file(f"Survey data keys: {list(survey_data.keys())}")
            
            # Flatten nested survey data
            flattened_data = {'user_id': user_id, 'timestamp': datetime.now(timezone.utc).isoformat()}
            for section, items in survey_data.items():
                if isinstance(items, dict):
                    for key, value in items.items():
                        flattened_data[f"{section}_{key}"] = value
                        # Debug each field
                        logger.debug(f"Survey field: {section}_{key} = {value}")
                else:
                    flattened_data[section] = items
                    logger.debug(f"Survey field: {section} = {items}")
            
            # Verify critical fields exist
            if 'q1b_clarity' in survey_data:
                logger.info(f"Survey clarity value: {survey_data['q1b_clarity']}")
            else:
                logger.warning("Missing expected survey field: q1b_clarity")
                
            if 'q2a_trust' in survey_data:
                logger.info(f"Survey trust value: {survey_data['q2a_trust']}")
            else:
                logger.warning("Missing expected survey field: q2a_trust")
            
            # Store the flattened data
            self.storage.log_survey(flattened_data)
            
            # Create backup of survey data in JSON format
            backup_dir = os.path.join(self.log_dir, 'survey_backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_file = os.path.join(backup_dir, f"survey_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json")
            with open(backup_file, 'w') as f:
                json.dump(flattened_data, f, indent=2)
                
            logger.info(f"Survey data saved successfully for user_id={user_id}")
            
        except Exception as e:
            error_msg = f"Error logging final survey: {str(e)}\n{traceback.format_exc()}"
            self._log_to_file(error_msg)
            logger.error(error_msg)
            
            # Try emergency direct logging as a last resort
            try:
                emergency_file = os.path.join(self.log_dir, 'emergency_surveys.json')
                with open(emergency_file, 'a') as f:
                    f.write(f"\n--- ERROR {datetime.now(timezone.utc).isoformat()} ---\n")
                    f.write(f"USER: {user_id}\n")
                    json.dump(survey_data, f, indent=2)
                    f.write("\n\n")
            except:
                pass

    def log_highlighted_terms(self, user_id: str, task_id: int, 
                         prompt: str, highlighted_terms: List[str] = None) -> None:
        """
        Log highlighted terms data for analytics
        
        Args:
            user_id: The user's ID
            task_id: The current task ID
            prompt: The prompt text
            highlighted_terms: List of highlighted terms (if already extracted)
        """
        try:
            # If highlighted terms aren't provided, extract them from prompt
            if highlighted_terms is None:
                from src.medical.medical_processor import MedicalTermProcessor
                processor = MedicalTermProcessor()
                highlighted_terms = processor.get_medical_terms(prompt)
            
            # Create interaction data
            interaction_data = {
                'user_id': user_id,
                'task_id': task_id,
                'action_type': 'HIGHLIGHT_TRACKING',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'original_prompt': prompt,
                'highlighted_terms': highlighted_terms,
                'term_count': len(highlighted_terms) if highlighted_terms else 0
            }
            
            # Log as interaction
            from src.core.data_storage import DataStorage
            storage = DataStorage()
            storage.log_interaction(interaction_data)
            
            # Also log to HighlightMetrics for analytics
            from tracking.metrics.highlight_metrics import HighlightMetrics
            metrics = HighlightMetrics()
            metrics.track_highlighted_terms(set(highlighted_terms), task_id)
            
            logger.info(f"Logged {len(highlighted_terms) if highlighted_terms else 0} highlighted terms for user {user_id}, task {task_id}")
            
        except Exception as e:
            error_msg = f"Error logging highlighted terms: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            
            # Try emergency direct logging as a last resort
            try:
                log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
                os.makedirs(log_dir, exist_ok=True)
                emergency_log = os.path.join(log_dir, 'emergency_highlights.log')
                with open(emergency_log, 'a') as f:
                    f.write(f"[{datetime.now(timezone.utc).isoformat()}] ERROR: {error_msg}\n")
                    f.write(f"DATA: user_id={user_id}, task_id={task_id}\n")
                    if prompt:
                        f.write(f"PROMPT: {prompt[:100]}...\n\n")
            except:
                pass

# Add missing helper functions
def _calculate_edit_distance(original: str, modified: str) -> float:
    """Calculate normalized edit distance between original and modified text"""
    if not original or not modified:
        return 0.0
    return difflib.SequenceMatcher(None, str(original), str(modified)).ratio()

def _determine_diff_type(original: str, modified: str) -> str:
    """Determine the type of difference between original and modified prompt"""
    if not original or not modified:
        return "unknown"
    
    if original == modified:
        return "unchanged"
        
    # Calculate word counts
    original_words = set(original.lower().split())
    modified_words = set(modified.lower().split())
    
    added = modified_words - original_words
    removed = original_words - modified_words
    
    if added and removed:
        return "substitution"
    elif added:
        return "addition"
    elif removed:
        return "deletion"
    else:
        return "reformulation"  # Same words but different structure

# Additional logging functions that might be imported
def log_task_duration(user_id: str, task_id: int, duration: float, start_time=None, end_time=None) -> None:
    """Log task duration information"""
    try:
        storage = DataStorage()
        task_data = {
            'user_id': user_id,
            'task_id': task_id,
            'task_duration': duration,
            'task_start': start_time.isoformat() if start_time else None,
            'task_end': end_time.isoformat() if end_time else None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        storage.log_task(task_data)
        logger.info(f"Task duration logged: {duration:.2f}s for user_id={user_id}, task_id={task_id}")
    except Exception as e:
        error_msg = f"Error logging task duration: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        enhanced_logger._log_to_file(error_msg)

def log_lime_explanation(user_id: str, task_id: int, prompt: str, explanation_data: Dict) -> None:
    """Log LIME explanation data"""
    try:
        storage = DataStorage()
        data = {
            'user_id': user_id,
            'task_id': task_id,
            'action_type': 'LIME_EXPLANATION',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'original_prompt': prompt,
            'explanation_data': json.dumps(explanation_data)
        }
        storage.log_interaction(data)
        logger.info(f"LIME explanation logged for user_id={user_id}, task_id={task_id}")
    except Exception as e:
        error_msg = f"Error logging LIME explanation: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        enhanced_logger._log_to_file(error_msg)

def log_model_output(user_id: str, task_id: int, prompt: str, model_output: str, model_info: Dict = None) -> None:
    """Log model output for analysis"""
    try:
        storage = DataStorage()
        data = {
            'user_id': user_id,
            'task_id': task_id,
            'action_type': 'MODEL_OUTPUT',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'original_prompt': prompt,
            'model_response': model_output
        }
        
        # Add model info if provided
        if model_info:
            for key, value in model_info.items():
                data[key] = value
                
        storage.log_interaction(data)
        logger.info(f"Model output logged for user_id={user_id}, task_id={task_id}")
    except Exception as e:
        error_msg = f"Error logging model output: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        enhanced_logger._log_to_file(error_msg)

# Initialize global logger instance
enhanced_logger = EnhancedLogger()

# Only keep these clean global interfaces
def log_chat_interaction(*args, **kwargs):
    enhanced_logger.log_interaction(*args, **kwargs)

def log_validation_action(user_id, action_type, prompt, modified_prompt=None, highlighted_terms=None, medical_term_count=None):
    """Log validation actions (highlighting, modifying, accepting prompts)"""
    try:
        # Fix the import path by using relative import
        import os
        import sys
        
        # Add project root to path if needed
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.append(project_root)
            
        # Now import with proper path
        from src.core.data_storage import DataStorage
        
        # Create interaction data
        timestamp = datetime.now().isoformat()
        interaction_data = {
            'user_id': user_id,
            'action_type': action_type,
            'event_type': 'VALIDATION',
            'timestamp': timestamp,
            'original_prompt': prompt
        }
        
        # Add optional data if provided
        if modified_prompt:
            interaction_data['modified_prompt'] = modified_prompt
        if highlighted_terms:
            interaction_data['highlighted_terms'] = highlighted_terms
            interaction_data['medical_term_count'] = len(highlighted_terms)
        if medical_term_count is not None:
            interaction_data['medical_term_count'] = medical_term_count
            
        # Save data
        storage = DataStorage()
        storage.log_interaction(interaction_data)
        
    except Exception as e:
        import logging
        import traceback
        logging.error(f"Error logging validation action: {str(e)}")
        logging.error(traceback.format_exc())

def log_task_completion(*args, **kwargs):
    enhanced_logger.log_task_completion(*args, **kwargs)

def log_final_survey(*args, **kwargs):
    enhanced_logger.log_final_survey(*args, **kwargs)

def log_feedback(*args, **kwargs):
    enhanced_logger.log_feedback(*args, **kwargs)
    
def check_storage_status():
    """Diagnostic function to check storage status"""
    return enhanced_logger.verify_storage()

# Run verification on module import
storage_status = check_storage_status()
logger.info(f"Storage verification on startup: {json.dumps(storage_status, indent=2)}")
def log_feedback(*args, **kwargs):
    enhanced_logger.log_feedback(*args, **kwargs)
    
def check_storage_status():
    """Diagnostic function to check storage status"""
    return enhanced_logger.verify_storage()

# Run verification on module import
storage_status = check_storage_status()
logger.info(f"Storage verification on startup: {json.dumps(storage_status, indent=2)}")
