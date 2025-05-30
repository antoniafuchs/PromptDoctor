import pandas as pd
import os
import csv
from datetime import datetime
from typing import Dict, List, Optional, Any
import difflib
import shutil
import json
import uuid
import logging
import traceback
import sys

# Configure logging
logger = logging.getLogger('data_storage')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def safe_concat_dataframe(existing_df: pd.DataFrame, new_data: dict) -> pd.DataFrame:
    """
    Safely concatenate new data to existing DataFrame, handling empty/NA values properly
    """
    # Debug incoming data
    logger.debug(f"Concatenating data with keys: {list(new_data.keys())}")
    
    # Convert complex types to strings to prevent DataFrame errors
    for key, value in new_data.items():
        if isinstance(value, (dict, list)):
            logger.debug(f"Converting complex type for field '{key}': {type(value)} to string")
            new_data[key] = str(value)
    
    # Convert new data to DataFrame
    new_df = pd.DataFrame([new_data])
    
    # If existing df is empty, return new df with proper dtypes
    if existing_df.empty:
        # Ensure proper dtypes for common columns
        for col in new_df.columns:
            if pd.api.types.is_numeric_dtype(new_df[col]):
                new_df[col] = pd.to_numeric(new_df[col], errors='coerce')
            elif pd.api.types.is_datetime64_any_dtype(new_df[col]):
                new_df[col] = pd.to_datetime(new_df[col], errors='coerce')
            else:
                new_df[col] = new_df[col].astype(str)
        return new_df
    
    # Get all columns from both DataFrames
    all_columns = list(set(existing_df.columns) | set(new_df.columns))
    
    # Fill missing columns with appropriate NA values
    for col in all_columns:
        if col not in existing_df:
            # Add missing column with appropriate dtype from new_df
            dtype = new_df[col].dtype
            existing_df[col] = pd.Series(dtype=dtype)
        if col not in new_df:
            # Add missing column with appropriate dtype from existing_df
            dtype = existing_df[col].dtype
            new_df[col] = pd.Series(dtype=dtype)
    
    # Ensure matching dtypes before concatenation
    for col in all_columns:
        if existing_df[col].dtype != new_df[col].dtype:
            if pd.api.types.is_numeric_dtype(existing_df[col]):
                new_df[col] = pd.to_numeric(new_df[col], errors='coerce')
            elif pd.api.types.is_datetime64_any_dtype(existing_df[col]):
                new_df[col] = pd.to_datetime(new_df[col], errors='coerce')
            else:
                new_df[col] = new_df[col].astype(str)
                existing_df[col] = existing_df[col].astype(str)
    
    # Concatenate with aligned columns and dtypes
    return pd.concat(
        [existing_df, new_df],
        ignore_index=True,
        axis=0,
        sort=False,
        copy=True  # Explicit copy to avoid warnings
    )

def save_interaction_data(df: pd.DataFrame, data: dict, filepath: str) -> pd.DataFrame:
    """Save interaction data and return updated DataFrame"""
    df = safe_concat_dataframe(df, data)
    df.to_csv(filepath, index=False)
    return df

def load_interaction_data(filepath: str) -> pd.DataFrame:
    """Load interaction data, create file if doesn't exist"""
    if os.path.exists(filepath):
        return pd.read_csv(filepath)
    return pd.DataFrame()

class DataStorage:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.feedback_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'feedback')
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        
        # Ensure all directories exist
        for directory in [self.data_dir, self.feedback_dir, self.log_dir]:
            os.makedirs(directory, exist_ok=True)
            
        self._ensure_data_directory()
        self._initialize_csv_files()
        
        # Log initialization
        self._log_storage_event("DataStorage initialized")
        
    def _log_storage_event(self, message: str, level: str = "INFO"):
        """Log storage events to a dedicated file"""
        try:
            timestamp = datetime.now().isoformat()
            log_file = os.path.join(self.log_dir, 'storage.log')
            with open(log_file, 'a') as f:
                f.write(f"[{timestamp}] [{level}] {message}\n")
        except Exception as e:
            # Last resort fallback - print to console
            print(f"Error writing to storage log: {str(e)}")
            print(f"Original message: {message}")

    def _ensure_data_directory(self):
        """Create data directory if it doesn't exist"""
        os.makedirs(self.data_dir, exist_ok=True)

    def _read_or_create_df(self, filepath: str, headers: list) -> pd.DataFrame:
        """Read existing CSV or create new DataFrame with headers"""
        try:
            if os.path.exists(filepath):
                return pd.read_csv(filepath, sep=';')
            else:
                df = pd.DataFrame(columns=headers)
                df.to_csv(filepath, index=False, sep=';')
                return df
        except Exception as e:
            print(f"Error accessing {filepath}: {str(e)}")
            return pd.DataFrame(columns=headers)

    def _safe_save_df(self, df: pd.DataFrame, filepath: str) -> None:
        """Safely save DataFrame to CSV with semicolon delimiter"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            df.to_csv(filepath, index=False, sep=';')
        except Exception as e:
            print(f"Error saving to {filepath}: {str(e)}")

    def _initialize_csv_files(self):
        """Initialize CSV files with headers"""
        files_and_headers = {
            'users.csv': ['user_id', 'group', 'login_time', 'logout_time',
                         # Demographics
                         'age', 'gender',
                         # Medical Experience
                         'training_level', 'specialization', 'patient_records_exp',
                         'clinical_notes_confidence',
                         # AI Experience
                         'gen_ai_familiarity', 'prompt_eng_familiarity', 'cds_familiarity',
                         'llm_usage_frequency',
                         # Usage Patterns
                         'trust_level'],
            
            'tasks.csv': ['user_id', 'task_id', 'task_start', 'task_end', 'completion_status',
                         'task_duration', 'timestamp',
                         # Task Survey Questions
                         'PE_difficulty', 'PE_satisfaction', 'PE_understanding',
                         'CL_mental', 'CL_temporal', 'CL_effort', 'CL_performance', 'CL_frustration',
                         'MQ_accuracy', 'MQ_professional', 'MQ_usefulness', 'MQ_inaccuracies'],
            
            'interactions.csv': ['user_id', 'task_id', 'action_type', 'timestamp',
                               'original_prompt', 'modified_prompt', 'model_response',
                               'highlighted_terms', 'term_count', 'diff_type', 'feedback',
                               'feedback_timestamp', 'model_type', 'duration_typing',
                               'duration_generation', 'duration_queue_time', 'message_id'],
            
            'validation.csv': ['user_id', 'task_id', 'timestamp', 'action_type',
                             'original_prompt', 'modified_prompt', 'changed_terms',
                             'reason_for_change', 'edit_distance', 'highlighted_terms',
                             'medical_term_count'],
            
            'surveys.csv': ['user_id', 'timestamp', 'group',
                          # Usability Questions
                          'US_ease', 'US_clarity', 'US_reuse', 
                          # Trust Questions
                          'TR_model_trust', 'TR_understanding', 'TR_current_trust', 'TR_explanations',
                          # Feedback Questions
                          'FB_likes', 'FB_improvements', 'FB_clinical_yn', 'FB_clinical', 'FB_other',
                          # Explainability Questions (Group B)
                          'EX_edit_helpful', 'EX_edit_reason', 'EX_self_efficacy', 'EX_terms_useful',
                          'EX_refinement', 'EX_helpful', 'EX_reuse', 'EX_trust', 'EX_edit_understanding',
                          'EX_clarity', 'EX_edit_changed', 'EX_understanding'],

            'logins.csv': ['timestamp', 'user_id', 'group', 'model_type', 'model_name'],
            # 'task_surveys.csv': [
            #     'timestamp', 'user_id', 'task_number',
            #     # Task Experience
            #     'difficulty', 'mental_demand', 'frustration',
            #     # Clinical Accuracy
            #     'accuracy', 'task_accomplishment', 'expectation_match',
            #     # Clinical Utility
            #     'clinical_usefulness', 'medical_inaccuracies'
            # ]
        }

        for filename, headers in files_and_headers.items():
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w', newline='') as f:
                    # Use semicolon as delimiter consistently for all files
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(headers)

    def _calculate_edit_distance(self, original: str, modified: str) -> float:
        """Calculate normalized Levenshtein distance between prompts"""
        if original is None or modified is None:
            return 0.0
        return difflib.SequenceMatcher(None, str(original), str(modified)).ratio()

    def _calculate_diff_type(self, original: str, modified: str) -> str:
        """Calculate the type of difference between original and modified prompt"""
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

    def log_user(self, user_data: Dict) -> None:
        """Log user information"""
        # Ensure empty strings are stored as empty strings, not None
        for key, value in user_data.items():
            if value is None:
                user_data[key] = ''
        
        filepath = os.path.join(self.data_dir, 'users.csv')
        df = self._read_or_create_df(filepath, [
            'user_id', 'group', 'login_time', 'logout_time', 'age', 'gender', 'training_level',
            'specialization', 'patient_records_exp',
            'clinical_notes_confidence', 'gen_ai_familiarity', 'prompt_eng_familiarity', 
            'cds_familiarity', 'llm_usage_frequency',
            'trust_level'
        ])
        
        # Map older field names to new field names
        field_mappings = {
            'q1_training': 'training_level',
            'q1_other': 'specialization',
            'q2_records': 'patient_records_exp',
            'q4_confidence': 'clinical_notes_confidence',
            'q5a_gen_ai': 'gen_ai_familiarity',
            'q5b_prompt': 'prompt_eng_familiarity',
            'q5c_cds': 'cds_familiarity',
            'q7_frequency': 'llm_usage_frequency',
            'q9_trust': 'trust_level'
        }
        
        # Apply mappings
        for old_field, new_field in field_mappings.items():
            if old_field in user_data and new_field not in user_data:
                user_data[new_field] = user_data[old_field]
        
        # Convert likert scales to numeric
        likert_columns = ['clinical_notes_confidence', 'gen_ai_familiarity', 'prompt_eng_familiarity', 
                          'cds_familiarity', 'trust_level']
        for col in likert_columns:
            if col in user_data:
                if isinstance(user_data[col], str) and ' - ' in user_data[col]:
                    user_data[col] = int(user_data[col].split(' - ')[0])
                elif isinstance(user_data[col], str) and user_data[col].isdigit():
                    user_data[col] = int(user_data[col])
        
        # Ensure all text fields are properly saved as strings
        text_fields = ['specialization']
        for field in text_fields:
            if field in user_data and user_data[field] is not None:
                if not isinstance(user_data[field], str):
                    user_data[field] = str(user_data[field])
                # Ensure the field is not empty
                if user_data[field] is None:
                    user_data[field] = ''
                # Replace any newlines with spaces to prevent CSV issues
                if isinstance(user_data[field], str):
                    user_data[field] = user_data[field].replace('\n', ' ').replace('\r', ' ')
        
        # Log the text fields for debugging
        logger.debug(f"Saving user text fields:")
        for field in text_fields:
            if field in user_data:
                logger.debug(f"  {field}: {user_data[field]}")
        
        df = safe_concat_dataframe(df, user_data)
        self._safe_save_df(df, filepath)

    def log_task(self, task_data: Dict) -> None:
        """Log task completion data"""
        filepath = os.path.join(self.data_dir, 'tasks.csv')
        df = self._read_or_create_df(filepath, [
            'user_id', 'task_id', 'completion_status', 'task_duration', 'timestamp',
            'task_start', 'task_end', 'clinical_usefulness', 'medical_inaccuracies',
            'prompt_count', 'start_time', 'end_time', 'MQ_inaccuracies',
            'CL_performance', 'MQ_usefulness', 'PE_understanding',
            'PE_difficulty', 'CL_mental', 'CL_frustration', 'MQ_accuracy',
            'model_name', 'duration', 'group', 'model_type', 'event_type', 'survey_data'
        ])
        
        # Use provided duration or calculate if timestamps exist
        if 'task_duration' not in task_data:
            if 'task_start' in task_data and 'task_end' in task_data:
                try:
                    start = pd.to_datetime(task_data['task_start'])
                    end = pd.to_datetime(task_data['task_end'])
                    if pd.notna(start) and pd.notna(end):
                        task_data['task_duration'] = (end - start).total_seconds()
                    else:
                        task_data['task_duration'] = None
                except (ValueError, TypeError):
                    task_data['task_duration'] = None
            else:
                task_data['task_duration'] = None
        
        # Handle mapping from survey data fields to task fields
        field_mappings = {
            'difficulty': 'PE_difficulty',
            'mental_demand': 'CL_mental',
            'frustration': 'CL_frustration',
            'accuracy': 'MQ_accuracy',
            'task_accomplishment': 'CL_performance',
            'expectation_match': 'PE_understanding',
            'clinical_usefulness': 'MQ_usefulness',
            'medical_inaccuracies': 'MQ_inaccuracies'
        }
        
        # If survey_data is a string (JSON), try to parse it
        if 'survey_data' in task_data and isinstance(task_data['survey_data'], str):
            try:
                survey_data = json.loads(task_data['survey_data'])
                for src, dest in field_mappings.items():
                    if src in survey_data:
                        task_data[dest] = survey_data[src]
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Map individual fields that might be present in task_data
        for src, dest in field_mappings.items():
            if src in task_data and dest not in task_data:
                task_data[dest] = task_data[src]
        
        # Ensure text fields like medical_inaccuracies are strings
        for field in ['medical_inaccuracies', 'MQ_inaccuracies']:
            if field in task_data and task_data[field] is not None:
                if not isinstance(task_data[field], str):
                    task_data[field] = str(task_data[field])
        
        # Handle group field
        if 'group' not in task_data and 'model_type' in task_data:
            task_data['group'] = task_data['model_type']
        
        df = safe_concat_dataframe(df, task_data)
        self._safe_save_df(df, filepath)

    def log_interaction(self, interaction_data: Dict) -> None:
        """Log user interaction data with enhanced tracking"""
        filepath = os.path.join(self.data_dir, 'interactions.csv')
        df = self._read_or_create_df(filepath, [
            'user_id', 'task_id', 'action_type', 'timestamp', 
            'original_prompt', 'modified_prompt', 'model_response',
            'highlighted_terms', 'term_count', 'diff_type', 'feedback',
            'feedback_timestamp', 'message_id', 'model_type', 
            'duration_typing', 'duration_generation', 'duration_queue_time',
            'model_name', 'group', 'response_message_id'  # Added response_message_id
        ])
        
        # For feedback actions, check if already exists by message_id and user_id
        if interaction_data.get('action_type') == 'FEEDBACK' and 'message_id' in interaction_data:
            existing = df[
                (df['user_id'] == interaction_data['user_id']) & 
                (df['message_id'] == interaction_data['message_id']) &
                (df['action_type'] == 'FEEDBACK')
            ]
            if not existing.empty:
                logger.info(f"Skipping duplicate feedback for message_id={interaction_data['message_id']}")
                return  # Skip if feedback already exists
    
        # Ensure message_id is always present with a structured format
        if 'message_id' not in interaction_data or not interaction_data['message_id']:
            user_id = interaction_data.get('user_id', '')
            task_id = interaction_data.get('task_id', 0)
            interaction_data['message_id'] = self.generate_structured_message_id(user_id, task_id)
    
        # Generate response_message_id for chat messages if needed
        if (interaction_data.get('action_type') == 'CHAT' or 
            interaction_data.get('action_type') == 'MODEL_OUTPUT') and 'response_message_id' not in interaction_data:
            interaction_data['response_message_id'] = f"{interaction_data['message_id']}_response"
    
        # Calculate diff_type if modified_prompt exists but diff_type not provided
        if ('modified_prompt' in interaction_data and 
            interaction_data['modified_prompt'] and 
            'original_prompt' in interaction_data and
            not interaction_data.get('diff_type')):
            interaction_data['diff_type'] = self._calculate_diff_type(
                interaction_data['original_prompt'],
                interaction_data['modified_prompt']
            )
        
        # Process highlighted terms and set term_count
        if 'highlighted_terms' in interaction_data and interaction_data['highlighted_terms']:
            if isinstance(interaction_data['highlighted_terms'], str):
                terms = interaction_data['highlighted_terms'].split(',')
                interaction_data['term_count'] = len(terms)
            elif isinstance(interaction_data['highlighted_terms'], list):
                terms = interaction_data['highlighted_terms']
                interaction_data['term_count'] = len(terms)
                interaction_data['highlighted_terms'] = ','.join(terms)
            else:
                interaction_data['term_count'] = 0
        else:
            interaction_data['term_count'] = 0

        # Ensure feedback is numeric if present
        if 'feedback' in interaction_data:
            feedback_map = {'positive': 1, 'negative': -1, 'neutral': 0}
            if isinstance(interaction_data['feedback'], str) and interaction_data['feedback'] in feedback_map:
                interaction_data['feedback'] = feedback_map[interaction_data['feedback']]
            interaction_data['feedback_timestamp'] = datetime.now().isoformat()
        
        # Ensure group is included if model_type is available
        if 'model_type' in interaction_data and 'group' not in interaction_data:
            interaction_data['group'] = interaction_data['model_type']
        
        # Make sure model_response is stored as string
        if 'model_response' in interaction_data and interaction_data['model_response'] is not None:
            if not isinstance(interaction_data['model_response'], str):
                interaction_data['model_response'] = str(interaction_data['model_response'])
                
        # Ensure all text fields are at least empty strings
        text_fields = ['original_prompt', 'modified_prompt', 'model_response', 'highlighted_terms']
        for field in text_fields:
            if field in interaction_data and interaction_data[field] is None:
                interaction_data[field] = ''
        
        df = safe_concat_dataframe(df, interaction_data)
        self._safe_save_df(df, filepath)
        
        # Also save to unified prompt data if it's a validation or prompt-related action
        if interaction_data.get('action_type') in ['VALIDATION_VIEW', 'EDIT_CLICK', 'EDIT_UPDATE', 'ACCEPT_CLICK', 
                                                 'HIGHLIGHT_METRICS', 'PROMPT_METRICS', 'FEEDBACK']:
            self.save_unified_prompt_data(interaction_data)

    def log_validation(self, validation_data: Dict) -> None:
        """Log prompt validation data with enhanced tracking"""
        filepath = os.path.join(self.data_dir, 'validation.csv')
        df = self._read_or_create_df(filepath, [
            'user_id', 'task_id', 'timestamp', 'action_type',
            'original_prompt', 'modified_prompt', 'highlighted_terms',
            'medical_term_count', 'edit_distance', 'diff_type',
            'message_id', 'reason_for_change'
        ])
        
        # Calculate edit distance only if both prompts exist
        if 'original_prompt' in validation_data and 'modified_prompt' in validation_data:
            original = validation_data.get('original_prompt')
            modified = validation_data.get('modified_prompt')
            if original is not None and modified is not None:
                validation_data['edit_distance'] = self._calculate_edit_distance(original, modified)
                
                # Calculate diff_type if not provided
                if 'diff_type' not in validation_data or not validation_data['diff_type']:
                    validation_data['diff_type'] = self._calculate_diff_type(original, modified)
            else:
                validation_data['edit_distance'] = 0.0
        else:
            validation_data['edit_distance'] = 0.0
            
        # Process highlighted terms
        if 'highlighted_terms' in validation_data:
            if isinstance(validation_data['highlighted_terms'], list):
                terms = validation_data['highlighted_terms']
                validation_data['highlighted_terms'] = ','.join(terms)
                # Set medical term count based on number of terms
                validation_data['medical_term_count'] = len(terms)
            elif isinstance(validation_data['highlighted_terms'], str):
                # Handle case where highlighted terms is already a comma-separated string
                terms = validation_data['highlighted_terms'].split(',')
                validation_data['medical_term_count'] = len(terms) if validation_data['highlighted_terms'] else 0
            else:
                validation_data['medical_term_count'] = 0
            
        # Ensure message_id is always present
        if 'message_id' not in validation_data:
            validation_data['message_id'] = str(uuid.uuid4())

        # Make sure all text fields are strings
        for key in ['original_prompt', 'modified_prompt', 'highlighted_terms', 'reason_for_change']:
            if key in validation_data and validation_data[key] is None:
                validation_data[key] = ''

        df = safe_concat_dataframe(df, validation_data)
        self._safe_save_df(df, filepath)
        
        # Also save to unified prompt data
        validation_data['event_type'] = 'VALIDATION'
        self.save_unified_prompt_data(validation_data)

    def save_login_data(self, user_id: str, data: Dict[str, Any]) -> None:
        """Save login data"""
        filepath = os.path.join(self.data_dir, 'logins.csv')
        df = self._read_or_create_df(filepath, ['timestamp', 'user_id', 'group', 'model_type', 'model_name'])
        data.update({'timestamp': datetime.now().isoformat(), 'user_id': user_id})
        df = safe_concat_dataframe(df, data)
        self._safe_save_df(df, filepath)

    def save_task_survey(self, user_id: str, task_id: int, survey_data: dict) -> None:
        """Save task survey data with improved error handling and complete field mapping"""
        try:
            # Make sure directory exists
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Save to tasks.csv (primary record)
            tasks_file = os.path.join(self.data_dir, "tasks.csv")
            if not os.path.exists(tasks_file):
                with open(tasks_file, 'w', newline='') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(['user_id', 'task_id', 'task_start', 'task_end', 'completion_status',
                                   'task_duration', 'timestamp',
                                   # Task Survey Questions - ensure all fields are included
                                   'PE_difficulty', 'PE_satisfaction', 'PE_understanding',
                                   'CL_mental', 'CL_temporal', 'CL_effort', 'CL_performance', 'CL_frustration',
                                   'MQ_accuracy', 'MQ_professional', 'MQ_usefulness', 'MQ_inaccuracies',
                                   'CL_performance', 'prompt_count', 'start_time', 'end_time'])
            
            # Only save to tasks.csv now - we no longer save to task_surveys.csv
            # Add timestamp if not exists
            if 'timestamp' not in survey_data:
                survey_data['timestamp'] = datetime.now().isoformat()
            
            # Ensure all text fields are properly stored
            if 'medical_inaccuracies' in survey_data and survey_data['medical_inaccuracies'] is None:
                survey_data['medical_inaccuracies'] = ''
            if 'medical_inaccuracies' in survey_data and not isinstance(survey_data['medical_inaccuracies'], str):
                survey_data['medical_inaccuracies'] = str(survey_data['medical_inaccuracies'])
            
            # Debug original survey data
            print(f"DEBUG - Original survey data keys: {list(survey_data.keys())}")
            print(f"DEBUG - Survey data values for key fields:")
            print(f"  difficulty: '{survey_data.get('difficulty', 'MISSING')}'")
            print(f"  expectation_match: '{survey_data.get('expectation_match', 'MISSING')}'")
            print(f"  mental_demand: '{survey_data.get('mental_demand', 'MISSING')}'")
            print(f"  frustration: '{survey_data.get('frustration', 'MISSING')}'")
            print(f"  accuracy: '{survey_data.get('accuracy', 'MISSING')}'")
            
            # Ensure all expected fields have values, even if empty
            # This is the critical part - map ALL survey fields correctly
            mapped_data = {
                'user_id': user_id,
                'task_id': task_id,
                'completion_status': 'completed',
                'task_duration': survey_data.get('task_duration', 0.0),
                'timestamp': survey_data.get('timestamp', datetime.now().isoformat()),
                'task_start': survey_data.get('start_time', ''),  # Make sure we record when task started
                'task_end': survey_data.get('end_time', ''),
                # Ensure all survey fields are properly mapped - convert to strings to prevent nulls
                'PE_difficulty': str(survey_data.get('difficulty', '')),
                'PE_understanding': str(survey_data.get('expectation_match', '')), 
                'CL_mental': str(survey_data.get('mental_demand', '')),
                'CL_frustration': str(survey_data.get('frustration', '')),
                'MQ_accuracy': str(survey_data.get('accuracy', '')),
                'MQ_usefulness': str(survey_data.get('clinical_usefulness', '')),
                'MQ_inaccuracies': survey_data.get('medical_inaccuracies', ''),
                'CL_performance': str(survey_data.get('task_accomplishment', '')),
                'prompt_count': survey_data.get('prompt_count', 0),
                'start_time': survey_data.get('start_time', ''),  # Duplicate to match existing schema
                'end_time': survey_data.get('end_time', '')      # Duplicate to match existing schema
            }
            
            # Debug mapped data
            print(f"DEBUG - Mapped data field values:")
            print(f"  PE_difficulty: '{mapped_data.get('PE_difficulty', 'MISSING')}'")
            print(f"  PE_understanding: '{mapped_data.get('PE_understanding', 'MISSING')}'")
            print(f"  CL_mental: '{mapped_data.get('CL_mental', 'MISSING')}'")
            print(f"  CL_frustration: '{mapped_data.get('CL_frustration', 'MISSING')}'")
            print(f"  MQ_accuracy: '{mapped_data.get('MQ_accuracy', 'MISSING')}'")
        
            # Avoid duplicate entries by checking if this task entry already exists
            if os.path.exists(tasks_file):
                # Read existing CSV with field names preserved exactly as in file
                df = pd.read_csv(tasks_file, sep=';', dtype=str)
                
                # Print column names for debugging
                print(f"DEBUG - CSV columns: {list(df.columns)}")
                
                # Check if entry already exists for this user and task
                mask = (df['user_id'] == str(user_id)) & (df['task_id'] == str(task_id))
                if any(mask):
                    # Update existing entry instead of creating a new one
                    for key, value in mapped_data.items():
                        if key in df.columns:
                            df.loc[mask, key] = value
                
                    # Debug updated row
                    print(f"DEBUG - Updated row values:")
                    for key in ['PE_difficulty', 'PE_understanding', 'CL_mental', 'CL_frustration', 'MQ_accuracy']:
                        if key in df.columns:
                            print(f"  {key}: '{df.loc[mask, key].values[0] if any(mask) else 'NOT FOUND'}'")
                
                    # Save with original column order preserved
                    df.to_csv(tasks_file, index=False, sep=';')
                    return
            
            # If we get here, either the file doesn't exist or the entry doesn't exist
            # Append the new entry
            with open(tasks_file, 'a', newline='') as f:
                # Get existing headers
                existing_headers = []
                try:
                    with open(tasks_file, 'r', newline='') as read_f:
                        reader = csv.reader(read_f, delimiter=';')
                        existing_headers = next(reader)
                except:
                    # If we can't read headers, use all keys from mapped_data
                    existing_headers = list(mapped_data.keys())
                
                print(f"DEBUG - Writing row with headers: {existing_headers}")
                
                writer = csv.DictWriter(f, fieldnames=existing_headers, delimiter=';')
                # Only write header if file is new/empty
                if os.path.getsize(tasks_file) == 0:
                    writer.writeheader()
                
                # Write only fields that match the headers
                row_data = {k: v for k, v in mapped_data.items() if k in existing_headers}
                writer.writerow(row_data)
                
                # Debug what was actually written
                print(f"DEBUG - Row data written to CSV:")
                for key in ['PE_difficulty', 'PE_understanding', 'CL_mental', 'CL_frustration', 'MQ_accuracy']:
                    print(f"  {key}: '{row_data.get(key, 'NOT IN ROW')}'")
                
        except Exception as e:
            print(f"Error saving task survey: {str(e)}")
            # Attempt direct file writing as last resort
            try:
                with open(tasks_file, 'a', newline='') as f:
                    writer = csv.writer(f, delimiter=';')
                    # Write all fields including the problematic ones
                    row_values = [
                        user_id, task_id, 'completed', 
                        survey_data.get('task_duration', 0.0),
                        datetime.now().isoformat(),
                        # Add the missing fields explicitly
                        str(survey_data.get('difficulty', '')),
                        str(survey_data.get('expectation_match', '')),
                        str(survey_data.get('mental_demand', '')),
                        str(survey_data.get('frustration', '')),
                        str(survey_data.get('accuracy', '')),
                        str(survey_data.get('clinical_usefulness', '')),
                        survey_data.get('medical_inaccuracies', ''),
                        str(survey_data.get('task_accomplishment', '')),
                    ]
                    writer.writerow(row_values)
                    print(f"DEBUG - Emergency write completed with {len(row_values)} fields")
            except Exception as ex:
                print(f"Critical error saving task data: {str(ex)}")
    
    def save_prompt_counts(self, task_data: dict) -> None:
        """Save prompt count data for hypothesis testing"""
        # Make sure directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Ensure the prompt counts file exists
        counts_file = os.path.join(self.data_dir, "prompt_counts.csv")
        if not os.path.exists(counts_file):
            with open(counts_file, 'w', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(['user_id', 'group', 'task_id', 'prompt_count', 'timestamp'])
        
        # Append new row
        with open(counts_file, 'a', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([
                task_data.get('user_id', ''),
                task_data.get('group', ''),
                task_data.get('task_id', ''),
                task_data.get('prompt_count', 0),
                task_data.get('timestamp', datetime.now().isoformat())
            ])

    def save_prompt_metrics(self, user_id: str, task_id: int, group: str, metrics: Dict) -> None:
        """Save prompt metrics data for analysis with improved error handling and data validation"""
        # Prepare data for existing CSV files
        timestamp = metrics.get('timestamp', datetime.now().isoformat())
        
        # Update tasks.csv with prompt metrics
        tasks_file = os.path.join(self.data_dir, "tasks.csv")
        if os.path.exists(tasks_file):
            try:
                df = pd.read_csv(tasks_file, sep=';')
                # Try to find the specific task entry
                mask = (df['user_id'] == user_id) & (df['task_id'] == task_id)
                if any(mask):
                    # Update the existing entry with prompt metrics
                    idx = df[mask].index[-1]  # Use the latest matching entry
                    df.at[idx, 'prompt_count'] = metrics.get('prompt_count', 0)
                    df.to_csv(tasks_file, index=False, sep=';')
            except Exception as e:
                print(f"Error updating tasks.csv: {str(e)}")
        
        # Save to dedicated prompt_metrics.csv for comprehensive analysis
        prompt_metrics_file = os.path.join(self.data_dir, "prompt_metrics.csv")
        if not os.path.exists(prompt_metrics_file):
            with open(prompt_metrics_file, 'w', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(['user_id', 'task_id', 'group', 'prompt_count', 
                                'first_prompt', 'last_prompt', 'levenshtein_distance', 
                                'word_count', 'timestamp'])
        
        # Safely write to prompt_metrics.csv
        try:
            with open(prompt_metrics_file, 'a', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([
                    user_id,
                    task_id,
                    group,
                    metrics.get('prompt_count', 0),
                    metrics.get('first_prompt', '')[:500],  # Truncate long prompts to 500 chars
                    metrics.get('last_prompt', '')[:500],   # Truncate long prompts to 500 chars
                    metrics.get('levenshtein_distance', 0.0),
                    metrics.get('word_count', 0),
                    timestamp
                ])
        except Exception as e:
            print(f"Error writing to prompt_metrics.csv: {str(e)}")
        
        # Also record as an interaction for comprehensive analysis
        interaction_data = {
            'user_id': user_id,
            'task_id': task_id,
            'action_type': 'PROMPT_METRICS',
            'timestamp': timestamp,
            'original_prompt': metrics.get('first_prompt', '')[:500],  # Truncate long prompts
            'modified_prompt': metrics.get('last_prompt', '')[:500],   # Truncate long prompts
            'diff_type': 'analysis',
            'message_id': str(uuid.uuid4()),
            'model_type': group,  # Use group as model type for filtering
            'duration_typing': metrics.get('levenshtein_distance', 0.0),
            'duration_generation': metrics.get('word_count', 0),
            'duration_queue_time': metrics.get('prompt_count', 0)
        }
        
        self.log_interaction(interaction_data)

    def save_highlight_metrics(self, user_id, task_number, group, metrics_data):
        """
        Save highlight metrics data to the database
        
        Args:
            user_id (str): The unique user identifier
            task_number (int): The task number 
            group (str): The user's assigned group
            metrics_data (dict): Dictionary containing highlight metrics
        """
        try:
            # Create a document with highlight metrics data
            highlight_doc = {
                "user_id": user_id,
                "task_id": task_number,
                "group": group,
                "metrics": metrics_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store in the highlight_metrics collection
            self.db.collection("highlight_metrics").add(highlight_doc)
            return True
        except Exception as e:
            print(f"Error saving highlight metrics: {str(e)}")
            return False

    def _append_to_csv(self, filepath, data):
        """Append data to a CSV file with improved handling for text fields"""
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Debug incoming data text fields
        text_fields = ['FB_likes', 'FB_improvements', 'FB_clinical', 'FB_other', 
                       'EX_edit_reason', 'EX_comment', 'EX_edit_changed',
                       'clinical_reasoning_desc', 'specialization', 'expectations']
        print(f"DEBUG _append_to_csv - Text fields in data:")
        for field in text_fields:
            if field in data:
                print(f"  {field}: '{data[field]}'")
        
        # Clean the data: convert None to empty string, and ensure all values are strings
        cleaned_data = {}
        for key, value in data.items():
            if value is None:
                cleaned_data[key] = ''
            elif isinstance(value, list):
                cleaned_data[key] = ','.join(map(str, value))
            else:
                # For text fields that might contain multiline content, replace newlines
                if isinstance(value, str) and ('\n' in value or '\r' in value):
                    value = value.replace('\n', ' ').replace('\r', ' ')
                
                # Replace semicolons with commas to avoid delimiter issues
                if isinstance(value, str) and ';' in value:
                    value = value.replace(';', ',')
                
                cleaned_data[key] = value
    
        data = cleaned_data
        
        # Create file with headers if it doesn't exist
        if not os.path.exists(filepath):
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=data.keys(), delimiter=';')
                writer.writeheader()
        
        # Check if the file exists but is empty
        is_empty = False
        if os.path.exists(filepath) and os.path.getsize(filepath) == 0:
            is_empty = True
        
        # Append data
        with open(filepath, 'a', newline='') as f:
            # If the file was empty, write headers first
            if is_empty:
                writer = csv.DictWriter(f, fieldnames=data.keys(), delimiter=';')
                writer.writeheader()
            
            # Get existing headers
            with open(filepath, 'r', newline='') as read_file:
                reader = csv.reader(read_file, delimiter=';')
                headers = next(reader, [])
            
            # Debug headers
            print(f"DEBUG _append_to_csv - CSV headers: {headers}")
            
            # Filter data to include only columns in the CSV
            filtered_data = {k: v for k, v in data.items() if k in headers}
            
            # Debug filtered data
            print(f"DEBUG _append_to_csv - Text fields after filtering:")
            for field in text_fields:
                if field in filtered_data:
                    print(f"  {field}: '{filtered_data[field]}'")
            
            # If there are headers in the file, use them for writing
            if headers:
                # Use a custom writer to handle special characters properly
                writer = csv.DictWriter(
                    f, 
                    fieldnames=headers, 
                    delimiter=';',
                    extrasaction='ignore', 
                    quoting=csv.QUOTE_NONNUMERIC,  # Quote all non-numeric fields
                    quotechar='"',                 # Use double quotes for quoting
                    escapechar='\\'                # Use backslash as escape character
                )
                writer.writerow(filtered_data)
            else:
                # Otherwise use all data keys
                writer = csv.DictWriter(
                    f, 
                    fieldnames=data.keys(), 
                    delimiter=';',
                    quoting=csv.QUOTE_NONNUMERIC,  # Quote all non-numeric fields
                    quotechar='"',                 # Use double quotes for quoting
                    escapechar='\\'                # Use backslash as escape character
                )
                writer.writerow(data)
    
        return data

    def save_unified_prompt_data(self, data):
        """Save unified prompt data to CSV file"""
        # Ensure we have a DataFrame to work with
        if not hasattr(self, 'prompt_df') or self.prompt_df is None:
            # Initialize DataFrame with expected columns
            self.prompt_df = pd.DataFrame(columns=[
                'user_id', 'task_id', 'group', 'event_type', 'action', 'timestamp', 
                'original_prompt', 'modified_prompt', 'highlighted_terms',
                'medical_term_count', 'prompt_count', 'message_id', 'model_type',
                'model_name', 'edit_distance', 'diff_type', 'action_type', 'last_prompt'
            ])
            
            # Create a directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Try to load existing data if file exists
            prompt_data_path = os.path.join(self.data_dir, 'unified_prompts.csv')
            if os.path.exists(prompt_data_path):
                try:
                    self.prompt_df = pd.read_csv(prompt_data_path, sep=';')
                except Exception as e:
                    print(f"Error loading prompt data: {e}")
        
        # Convert list of highlighted terms to string for storage
        if 'highlighted_terms' in data and isinstance(data['highlighted_terms'], list):
            data['highlighted_terms'] = ','.join(data['highlighted_terms'])
            
        # Make sure we have medical_term_count if highlighted_terms exists
        if 'highlighted_terms' in data and data['highlighted_terms'] and 'medical_term_count' not in data:
            if isinstance(data['highlighted_terms'], str):
                data['medical_term_count'] = len(data['highlighted_terms'].split(','))
            else:
                data['medical_term_count'] = 0
                
        # Calculate diff_type if missing but we have original and modified prompts
        if ('diff_type' not in data or not data.get('diff_type')) and 'original_prompt' in data and 'modified_prompt' in data:
            data['diff_type'] = self._calculate_diff_type(data['original_prompt'], data['modified_prompt'])
            
        # Ensure consistent action_type field 
        if 'action' in data and 'action_type' not in data:
            data['action_type'] = data['action']
        elif 'action_type' in data and 'action' not in data:
            data['action'] = data['action_type']
            
        # Make sure we have model info
        if 'model_type' not in data and 'group' in data:
            data['model_type'] = data['group']
        
        # Special handling for text fields that might contain newlines, quotes, or semicolons
        text_fields = ['original_prompt', 'modified_prompt', 'model_response', 'last_prompt']
        for field in text_fields:
            if field in data and data[field] is not None:
                # Make sure it's a string
                if not isinstance(data[field], str):
                    data[field] = str(data[field])
                
                # Replace semicolons with commas to avoid delimiter issues
                data[field] = data[field].replace(';', ',')
                
                # Replace newlines with spaces
                data[field] = data[field].replace('\n', ' ').replace('\r', ' ')
                
                # If the text is very long, truncate it to a reasonable length
                if len(data[field]) > 1000:
                    data[field] = data[field][:997] + "..."
    
        # Append new data
        new_row = pd.DataFrame([data])
        
        # Ensure all columns exist in both dataframes
        all_columns = list(set(self.prompt_df.columns) | set(new_row.columns))
        for col in all_columns:
            if col not in self.prompt_df:
                self.prompt_df[col] = None
            if col not in new_row:
                new_row[col] = None
                
        # Concatenate the dataframes
        self.prompt_df = pd.concat([self.prompt_df, new_row], ignore_index=True)
        
        # Save to CSV
        try:
            prompt_data_path = os.path.join(self.data_dir, 'unified_prompts.csv')
            
            # Use pandas' built-in quoting mechanism to handle fields with special characters
            self.prompt_df.to_csv(
                prompt_data_path, 
                index=False, 
                sep=';', 
                quoting=csv.QUOTE_NONNUMERIC,  # Quote all non-numeric fields
                quotechar='"',                 # Use double quotes for quoting
                escapechar='\\'                # Use backslash as escape character
            )
        except Exception as e:
            print(f"Error saving prompt data: {e}")
            
            # Last resort - try direct write with minimal fields
            try:
                with open(prompt_data_path, 'a', newline='') as f:
                    writer = csv.writer(f, delimiter=';')
                    minimal_data = [
                        data.get('user_id', ''),
                        data.get('task_id', ''),
                        data.get('event_type', ''),
                        data.get('action', ''),
                        data.get('timestamp', datetime.now().isoformat()),
                        data.get('original_prompt', ''),
                        data.get('modified_prompt', ''),
                        data.get('highlighted_terms', ''),
                        data.get('medical_term_count', 0),
                        data.get('prompt_count', 0),
                        data.get('message_id', ''),
                        data.get('model_type', ''),
                        data.get('model_name', ''),
                        data.get('group', ''),
                        data.get('edit_distance', 0.0),
                        data.get('diff_type', '')
                    ]
                    writer.writerow(minimal_data)
            except Exception as e2:
                print(f"Critical error saving prompt data: {e2}")
        
    # This is an alias method to maintain compatibility
    def save_validation_log(self, data):
        """Alias for save_unified_prompt_data for backward compatibility"""
        return self.save_unified_prompt_data(data)
        
    def set_value(self, id, key, value):
        """Set a specific value for a user by ID."""
        mask = self.df['id'] == id
    
        # Handle conversion of empty strings to appropriate types for numeric columns
        if value == '' and key in self.df.columns and pd.api.types.is_numeric_dtype(self.df[key]):
            value = pd.NA  # Use pandas NA for empty values in numeric columns
    
        self.df.loc[mask, key] = value

    def get_message_feedback(self, user_id: str, message_id: str) -> Optional[Dict]:
        """Get feedback for a specific message"""
        try:
            filepath = os.path.join(self.data_dir, 'interactions.csv')
            if not os.path.exists(filepath):
                return None
                
            df = pd.read_csv(filepath, sep=';')
            
            # Find feedback for this message
            mask = (df['user_id'] == user_id) & (df['message_id'] == message_id) & (df['action_type'] == 'FEEDBACK')
            if mask.any():
                row = df[mask].iloc[0]
                return {
                    'feedback_value': row.get('feedback', None),
                    'timestamp': row.get('feedback_timestamp', None)
                }
            return None
        except Exception as e:
            error_msg = f"Error getting message feedback: {str(e)}"
            logger.error(error_msg)
            self._log_storage_event(error_msg, "ERROR")
            return None
    
    def save_feedback(self, user_id: str, message_id: str, feedback_data: Dict) -> bool:
        """Save feedback data for a specific message."""
        try:
            import os
            import json
            import csv
            import traceback
            from datetime import datetime
            import pandas as pd

            # Ensure the feedback directory exists
            os.makedirs(self.feedback_dir, exist_ok=True)

            # Initialize placeholders
            model_output = None
            model_prompt = None
            response_timestamp = None
            interaction_filepath = os.path.join(self.data_dir, 'interactions.csv')

            # Try to extract model output and prompt from interactions.csv
            if os.path.exists(interaction_filepath):
                try:
                    interactions_df = pd.read_csv(interaction_filepath, sep=';')
                    message_row = interactions_df[interactions_df['message_id'] == message_id]

                    if not message_row.empty:
                        # Found the exact message
                        row = message_row.iloc[0]
                        model_output = row.get('model_output')
                        model_prompt = row.get('user_prompt')
                        response_timestamp = row.get('timestamp')
                        logger.info(f"Found exact message match for feedback: {message_id}")
                    else:
                        # Try to find the following model response
                        user_messages = interactions_df[
                            (interactions_df['user_id'] == user_id) & 
                            (interactions_df['action_type'] == 'CHAT')
                        ].sort_values('timestamp')

                        for idx in range(len(user_messages) - 1):
                            if user_messages.iloc[idx]['message_id'] == message_id:
                                next_row = user_messages.iloc[idx + 1]
                                model_output = next_row.get('model_output')
                                model_prompt = next_row.get('user_prompt')
                                response_timestamp = next_row.get('timestamp')
                                logger.info(f"Found model response following user message: {message_id}")
                                break
                except Exception as df_error:
                    logger.warning(f"Error looking up model output for feedback: {str(df_error)}")

            # Attach extra metadata to feedback
            if pd.notna(model_output):
                feedback_data['model_response'] = model_output
            if pd.notna(model_prompt):
                feedback_data['original_prompt'] = model_prompt
            if pd.notna(response_timestamp):
                feedback_data['response_timestamp'] = response_timestamp

            # Compute a hash from the prompt for file uniqueness
            prompt_hash = str(hash(feedback_data.get('original_prompt', '')))[-8:]

            feedback_file = os.path.join(
                self.feedback_dir, f"{user_id}_{prompt_hash}_{message_id}.json"
            )

            feedback_data.update({
                'user_id': user_id,
                'message_id': message_id,
                'saved_at': datetime.now().isoformat()
            })

            with open(feedback_file, 'w') as f:
                json.dump(feedback_data, f, indent=2)

            # Feedback log CSV
            feedback_log = os.path.join(self.data_dir, 'feedback.csv')
            if not os.path.exists(feedback_log):
                with open(feedback_log, 'w', newline='') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow([
                        'user_id', 'message_id', 'response_message_id', 'feedback_value',
                        'timestamp', 'prompt_hash', 'prompt_excerpt', 'response_excerpt',
                        'response_timestamp'
                    ])

            prompt_excerpt = (feedback_data.get('original_prompt') or '')[:100].replace('\n', ' ')
            response_excerpt = (feedback_data.get('model_response') or '')[:100].replace('\n', ' ')

            with open(feedback_log, 'a', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([
                    user_id,
                    message_id,
                    feedback_data.get('response_message_id', message_id),
                    feedback_data.get('feedback_value', ''),
                    feedback_data.get('timestamp', datetime.now().isoformat()),
                    prompt_hash,
                    prompt_excerpt,
                    response_excerpt,
                    feedback_data.get('response_timestamp', '')
                ])

            # Log interaction for feedback
            interaction_data = {
                'user_id': user_id,
                'action_type': 'FEEDBACK',
                'message_id': message_id,
                'original_prompt': feedback_data.get('original_prompt', ''),
                'model_response': feedback_data.get('model_response', ''),
                'feedback': feedback_data.get('feedback_value', ''),
                'feedback_timestamp': datetime.now().isoformat(),
                'timestamp': datetime.now().isoformat(),
                'response_message_id': feedback_data.get('response_message_id', message_id),
                'task_id': self._extract_task_id_from_message_id(message_id)
            }

            self.log_interaction(interaction_data)
            self._log_storage_event(f"Saved feedback for user {user_id}, message {message_id}, prompt hash {prompt_hash}")
            return True

        except Exception as e:
            error_msg = f"Error saving feedback: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self._log_storage_event(error_msg, "ERROR")
            return False


    def _extract_task_id_from_message_id(self, message_id: str) -> int:
        """Extract task ID from a structured message ID"""
        try:
            # Try to extract task ID from structured message ID like 'abc123_task2_prompt1'
            if '_task' in message_id:
                task_part = message_id.split('_task')[1]
                if '_' in task_part:
                    task_id = int(task_part.split('_')[0])
                    return task_id
            # Try other formats like 'task_2_prompt_1_abc123'
            elif 'task_' in message_id:
                parts = message_id.split('_')
                for i, part in enumerate(parts):
                    if part == 'task' and i+1 < len(parts):
                        try:
                            return int(parts[i+1])
                        except ValueError:
                            pass
        except Exception:
            pass
        return 0  # Default task ID if extraction fails

    def get_storage_status(self) -> Dict:
        """Get storage system status for diagnostics"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "python_version": sys.version,
            "pandas_version": pd.__version__,
            "directories": {
                "data_dir": {
                    "path": self.data_dir,
                    "exists": os.path.exists(self.data_dir),
                    "writable": os.access(self.data_dir, os.W_OK) if os.path.exists(self.data_dir) else False
                },
                "feedback_dir": {
                    "path": self.feedback_dir,
                    "exists": os.path.exists(self.feedback_dir),
                    "writable": os.access(self.feedback_dir, os.W_OK) if os.path.exists(self.feedback_dir) else False
                },
                "log_dir": {
                    "path": self.log_dir,
                    "exists": os.path.exists(self.log_dir),
                    "writable": os.access(self.log_dir, os.W_OK) if os.path.exists(self.log_dir) else False
                }
            },
            "files": {}
        }
        
        # Check key data files
        important_files = [
            os.path.join(self.data_dir, 'users.csv'),
            os.path.join(self.data_dir, 'tasks.csv'),
            os.path.join(self.data_dir, 'interactions.csv'),
            os.path.join(self.data_dir, 'surveys.csv'),
            os.path.join(self.data_dir, 'validation.csv')
        ]
        
        for filepath in important_files:
            filename = os.path.basename(filepath)
            file_exists = os.path.exists(filepath)
            status["files"][filename] = {
                "path": filepath,
                "exists": file_exists,
                "size_bytes": os.path.getsize(filepath) if file_exists else 0,
                "writable": os.access(filepath, os.W_OK) if file_exists else False,
                "last_modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat() if file_exists else None,
                "row_count": -1  # Will be filled in below
            }
            
            # Try to count rows in the file
            if file_exists:
                try:
                    with open(filepath, 'r', newline='') as f:
                        reader = csv.reader(f)
                        row_count = sum(1 for _ in reader) - 1  # Subtract header
                        status["files"][filename]["row_count"] = max(0, row_count)
                except Exception as e:
                    status["files"][filename]["row_count_error"] = str(e)
        
        # Perform test write
        test_file = os.path.join(self.log_dir, 'storage_test.txt')
        try:
            with open(test_file, 'w') as f:
                f.write(f"Storage test at {datetime.now().isoformat()}")
            status["test_write_success"] = True
            if os.path.exists(test_file):
                os.remove(test_file)
        except Exception as e:
            status["test_write_success"] = False
            status["test_write_error"] = str(e)
        
        # Log the status check
        self._log_storage_event(f"Storage status check completed: {json.dumps(status, indent=2)}")
        
        return status
    
    def generate_structured_message_id(self, user_id: str, task_id: int, prompt_count: int = None) -> str:
        """Generate a structured and consistent message ID"""
        # Extract the first 8 characters of the user ID as a prefix
        user_prefix = user_id[:8] if user_id else "unknown"
        
        # Use provided prompt count or get the current count
        if prompt_count is None:
            # Try to look up from tasks.csv
            try:
                tasks_file = os.path.join(self.data_dir, "tasks.csv")
                if os.path.exists(tasks_file):
                    df = pd.read_csv(tasks_file, sep=';')
                    matching_tasks = df[(df['user_id'] == user_id) & (df['task_id'] == task_id)]
                    if not matching_tasks.empty:
                        prompt_count = matching_tasks.iloc[-1].get('prompt_count', 0)
                    else:
                        prompt_count = 0
                else:
                    prompt_count = 0
            except Exception as e:
                logger.error(f"Error getting prompt count: {str(e)}")
                prompt_count = int(datetime.now().strftime("%H%M%S"))  # Use time as fallback
    
        # Construct the message ID
        message_id = f"{user_prefix}_task{task_id}_prompt{prompt_count}"
        return message_id

    def log_survey(self, survey_data: Dict) -> None:
        """Log final survey data with improved error handling"""
        try:
            # Make sure directory exists
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Save to surveys.csv
            filepath = os.path.join(self.data_dir, 'surveys.csv')
            
            # Debug survey data
            logger.info(f"Logging survey for user_id={survey_data.get('user_id')} with {len(survey_data)} fields")
            
            # Handle text fields with special care
            text_fields = ['FB_likes', 'FB_improvements', 'FB_clinical', 'FB_other', 
                          'EX_edit_reason', 'EX_comment', 'EX_edit_changed',
                          'EX_highlight_meaning', 'EX_highlight_missed_terms', 'TR_trust_other']
            
            for field in text_fields:
                if field in survey_data:
                    # Ensure text fields are strings
                    if survey_data[field] is None:
                        survey_data[field] = ''
                    elif not isinstance(survey_data[field], str):
                        survey_data[field] = str(survey_data[field])
                    
                    # Clean newlines and semicolons for CSV compatibility
                    if isinstance(survey_data[field], str):
                        survey_data[field] = survey_data[field].replace('\n', ' ').replace('\r', ' ')
                        # Replace semicolons with commas to avoid CSV delimiter issues
                        survey_data[field] = survey_data[field].replace(';', ',')
            
            # Check if file exists, and if not, create with headers
            if not os.path.exists(filepath):
                with open(filepath, 'w', newline='') as f:
                    headers = ['user_id', 'timestamp', 'group', 
                              'US_ease', 'US_clarity', 'US_reuse',
                              'TR_model_trust', 'TR_understanding', 'TR_current_trust', 'TR_explanations', 
                              'TR_trust_factors', 'TR_trust_other',
                              'FB_likes', 'FB_improvements', 'FB_clinical_yn', 'FB_clinical', 'FB_other',
                              'EX_edit_helpful', 'EX_edit_reason', 'EX_self_efficacy', 'EX_terms_useful',
                              'EX_refinement', 'EX_helpful', 'EX_reuse', 'EX_trust', 'EX_edit_understanding',
                              'EX_clarity', 'EX_edit_changed', 'EX_understanding', 'EX_highlight_meaning',
                              'EX_highlight_missed_terms']
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(headers)
            
            # Append data directly to file rather than using _append_to_csv
            with open(filepath, 'a', newline='') as f:
                # Get existing headers
                with open(filepath, 'r', newline='') as read_file:
                    reader = csv.reader(read_file, delimiter=';')
                    headers = next(reader, [])
                
                # Prepare data row with only fields that match headers
                row_data = {}
                for header in headers:
                    if header in survey_data:
                        value = survey_data[header]
                        # Ensure proper escaping for text fields
                        if isinstance(value, str) and (';' in value or '"' in value):
                            # Let CSV module handle escaping
                            row_data[header] = value
                        else:
                            row_data[header] = value
                    else:
                        row_data[header] = ''  # Use empty string for missing fields
                
                # Write data with proper quoting and escaping
                writer = csv.DictWriter(
                    f, 
                    fieldnames=headers, 
                    delimiter=';',
                    quoting=csv.QUOTE_NONNUMERIC,  # Quote all non-numeric fields
                    quotechar='"',                 # Use double quotes for quoting
                    escapechar='\\'                # Use backslash as escape character
                )
                writer.writerow(row_data)
                
            # Also save as JSON for redundancy
            user_id = survey_data.get('user_id', 'unknown')
            backup_dir = os.path.join(self.log_dir, 'survey_backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f"survey_{user_id}_{timestamp}.json")
            
            with open(backup_file, 'w') as f:
                json.dump(survey_data, f, indent=2)
                
            logger.info(f"Survey saved successfully for user_id={user_id}")
            self._log_storage_event(f"Survey saved for user {user_id}")
            
        except Exception as e:
            error_msg = f"Error saving survey: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self._log_storage_event(error_msg, "ERROR")
            
            # Emergency backup - try to save directly
            try:
                user_id = survey_data.get('user_id', 'unknown')
                emergency_file = os.path.join(self.log_dir, 'emergency_surveys.json')
                with open(emergency_file, 'a') as f:
                    f.write(f"\n--- ERROR {datetime.now().isoformat()} ---\n")
                    f.write(f"USER: {user_id}\n")
                    json.dump(survey_data, f, indent=2)
                    f.write("\n\n")
            except Exception as backup_error:
                print(f"Critical error during emergency survey backup: {str(backup_error)}")

    def save_chat_history(self, user_id: str, task_id: int, messages: List[Dict]) -> None:
        """Save chat history for a user and task to both CSV and JSON formats"""
        try:
            # Ensure directories exist
            chat_dir = os.path.join(self.data_dir, 'chat_history')
            merged_dir = os.path.join(os.path.dirname(self.data_dir), 'merged_data')
            os.makedirs(chat_dir, exist_ok=True)
            os.makedirs(merged_dir, exist_ok=True)
            
            # Create a filename based on user_id and task_id
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename_base = f"{user_id}_task{task_id}_{timestamp}"
            
            # Save as JSON file in chat_history directory
            json_file = os.path.join(chat_dir, f"{filename_base}.json")
            with open(json_file, 'w') as f:
                chat_data = {
                    "user_id": user_id,
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "messages": messages
                }
                json.dump(chat_data, f, indent=2)
            
            # Also log to interactions.csv for analysis
            for i, message in enumerate(messages):
                # Skip system messages
                if message.get("role") == "system":
                    continue
                    
                interaction_data = {
                    'user_id': user_id,
                    'task_id': task_id,
                    'action_type': 'CHAT_MESSAGE',
                    'timestamp': message.get('timestamp', datetime.now().isoformat()),
                    'original_prompt': message.get('content', '') if message.get('role') == 'user' else '',
                    'model_response': message.get('content', '') if message.get('role') == 'assistant' else '',
                    'message_id': message.get('message_id', f"{user_id}_task{task_id}_msg{i}"),
                    'iteration': message.get('iteration', i),
                    'message_index': i
                }
                
                # Log the interaction
                self.log_interaction(interaction_data)
            
            # Update the merged chat history JSON file
            self._update_merged_chat_history(user_id, task_id, messages)
            
            logger.info(f"Chat history saved for user {user_id}, task {task_id}: {len(messages)} messages")
            return json_file
            
        except Exception as e:
            error_msg = f"Error saving chat history: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self._log_storage_event(error_msg, "ERROR")
            return None
    
    def _update_merged_chat_history(self, user_id: str, task_id: int, messages: List[Dict]) -> None:
        """Update the merged chat history JSON file with new messages"""
        try:
            merged_file = os.path.join(os.path.dirname(self.data_dir), 'merged_data', 'chat_history.json')
            
            # Create base structure if file doesn't exist
            if not os.path.exists(merged_file):
                merged_data = []
            else:
                # Load existing data
                try:
                    with open(merged_file, 'r') as f:
                        merged_data = json.load(f)
                        if not isinstance(merged_data, list):
                            merged_data = []
                except (json.JSONDecodeError, ValueError):
                    # Reset if invalid JSON
                    merged_data = []
            
            # Find if there's an existing entry for this user and task
            found = False
            for i, entry in enumerate(merged_data):
                if entry.get('user_id') == user_id and entry.get('task_id') == task_id:
                    # Update existing entry
                    merged_data[i]['messages'] = messages
                    merged_data[i]['updated_at'] = datetime.now().isoformat()
                    found = True
                    break
            
            # If not found, add a new entry
            if not found:
                merged_data.append({
                    'user_id': user_id,
                    'task_id': task_id,
                    'messages': messages,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })
            
            # Save the updated file with proper formatting
            with open(merged_file, 'w') as f:
                json.dump(merged_data, f, indent=2)
                
        except Exception as e:
            error_msg = f"Error updating merged chat history: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self._log_storage_event(error_msg, "ERROR")
