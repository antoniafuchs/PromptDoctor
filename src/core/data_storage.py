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
            elif pd.api.types.is_datetime64_any_dtype(existingDf[col]):
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

    def update_chat_with_response(self, chat_data: Dict) -> None:
        """Update an existing CHAT entry with a model response"""
        try:
            # Find and update the corresponding CHAT entry in interactions.csv
            interactions_file = os.path.join(self.data_dir, 'interactions.csv')
            if not os.path.exists(interactions_file):
                logger.warning(f"Cannot update chat with response: {interactions_file} does not exist")
                return
                
            # Sanitize the model response to avoid CSV formatting issues
            if 'model_response' in chat_data and chat_data['model_response'] is not None:
                # Convert to string if not already
                if not isinstance(chat_data['model_response'], str):
                    chat_data['model_response'] = str(chat_data['model_response'])
                
                # Replace semicolons with commas to avoid delimiter issues
                chat_data['model_response'] = chat_data['model_response'].replace(';', ',')
                
                # Replace newlines with space + pipe + space for better readability
                chat_data['model_response'] = chat_data['model_response'].replace('\n', ' | ')
                
                # Replace quotes with single quotes to avoid CSV quoting issues
                chat_data['model_response'] = chat_data['model_response'].replace('"', "'")
                
                # Handle markdown formatting symbols
                chat_data['model_response'] = chat_data['model_response'].replace('**', '*')
            
            # Load interactions CSV with pandas for more robust handling
            try:
                df = pd.read_csv(interactions_file, sep=';', quoting=csv.QUOTE_MINIMAL, 
                                 escapechar='\\', encoding='utf-8')
                
                # Find matching rows
                mask = ((df['message_id'] == chat_data.get('message_id')) & 
                        (df['user_id'] == chat_data.get('user_id')) &
                        (df['task_id'].astype(str) == str(chat_data.get('task_id'))))
                
                if mask.any():
                    # Update model_response field for matching rows
                    df.loc[mask, 'model_response'] = chat_data.get('model_response', '')
                    
                    # Save back to CSV with proper escaping
                    df.to_csv(interactions_file, sep=';', index=False, quoting=csv.QUOTE_MINIMAL,
                             escapechar='\\', encoding='utf-8')
                    logger.info(f"Updated chat entry with model response for message_id={chat_data.get('message_id')}")
                    
                    # Also save a backup of the response in JSON format for reliable retrieval
                    self._save_response_backup(chat_data)
                    return
                
                # If no matching row found, log a new entry
                self.log_interaction({
                    'user_id': chat_data.get('user_id', 'unknown'),
                    'task_id': chat_data.get('task_id', 0),
                    'action_type': 'CHAT_RESPONSE',
                    'event_type': 'INTERACTION',
                    'timestamp': chat_data.get('timestamp', datetime.now().isoformat()),
                    'message_id': chat_data.get('message_id', ''),
                    'model_response': chat_data.get('model_response', ''),
                    'model_type': chat_data.get('model_type', ''),
                    'model_name': chat_data.get('model_name', ''),
                    'group': chat_data.get('group', '')
                })
                
                # Also save a backup of the response in JSON format
                self._save_response_backup(chat_data)
                
            except Exception as e:
                logger.error(f"Error updating chat with pandas: {str(e)}")
                
                # Fallback to CSV reader/writer approach
                updated = False
                rows = []
                headers = []
                
                with open(interactions_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f, delimiter=';')
                    headers = next(reader)  # Get headers
                    
                    # Make sure 'model_response' is in headers
                    if 'model_response' not in headers:
                        headers.append('model_response')
                    
                    for row in reader:
                        row_data = dict(zip(headers, row + [''] * (len(headers) - len(row))))
                        
                        # Check if this is the CHAT entry we want to update
                        if (row_data.get('action_type') == 'CHAT' and 
                            row_data.get('message_id') == chat_data.get('message_id') and
                            row_data.get('user_id') == chat_data.get('user_id') and
                            str(row_data.get('task_id')) == str(chat_data.get('task_id'))):
                            
                            # Update the model_response field
                            row_data['model_response'] = chat_data.get('model_response', '')
                            updated = True
                        
                        # Convert back to list in the right order
                        row_list = [row_data.get(h, '') for h in headers]
                        rows.append(row_list)
                
                # If we found and updated a row, write the file back
                if updated:
                    with open(interactions_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL, 
                                          escapechar='\\')
                        writer.writerow(headers)
                        writer.writerows(rows)
                    logger.info(f"Updated chat entry with model response for message_id={chat_data.get('message_id')}")
                    
                    # Also save a backup of the response in JSON format
                    self._save_response_backup(chat_data)
                else:
                    # If we couldn't find the chat to update, log a new entry
                    self.log_interaction({
                        'user_id': chat_data.get('user_id', 'unknown'),
                        'task_id': chat_data.get('task_id', 0),
                        'action_type': 'CHAT_RESPONSE',
                        'event_type': 'INTERACTION',
                        'timestamp': chat_data.get('timestamp', datetime.now().isoformat()),
                        'message_id': chat_data.get('message_id', ''),
                        'model_response': chat_data.get('model_response', ''),
                        'model_type': chat_data.get('model_type', ''),
                        'model_name': chat_data.get('model_name', ''),
                        'group': chat_data.get('group', '')
                    })
                    logger.info(f"Added new chat response entry for message_id={chat_data.get('message_id')}")
                    
                    # Also save a backup of the response in JSON format
                    self._save_response_backup(chat_data)
                    
        except Exception as e:
            error_msg = f"Error updating chat with response: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self._log_storage_event(error_msg, "ERROR")
            
            # Even in case of error, try to save a backup of the response
            try:
                self._save_response_backup(chat_data)
            except Exception as backup_err:
                logger.error(f"Failed to save response backup: {str(backup_err)}")
    
    def _save_response_backup(self, chat_data: Dict) -> None:
        """Save a backup of the model response in JSON format for reliable retrieval"""
        try:
            # Create responses directory if it doesn't exist
            responses_dir = os.path.join(self.data_dir, 'responses')
            os.makedirs(responses_dir, exist_ok=True)
            
            # Create a filename with user_id, task_id, and message_id
            user_id = chat_data.get('user_id', 'unknown')
            task_id = chat_data.get('task_id', 0)
            message_id = chat_data.get('message_id', datetime.now().strftime('%Y%m%d%H%M%S'))
            
            # Create a sanitized filename
            safe_message_id = ''.join(c for c in message_id if c.isalnum() or c in '_-')
            filename = f"{user_id}_{task_id}_{safe_message_id}.json"
            filepath = os.path.join(responses_dir, filename)
            
            # Save the original unsanitized response
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'user_id': user_id,
                    'task_id': task_id,
                    'message_id': message_id,
                    'timestamp': chat_data.get('timestamp', datetime.now().isoformat()),
                    'model_response': chat_data.get('model_response', ''),
                    'model_type': chat_data.get('model_type', ''),
                    'model_name': chat_data.get('model_name', ''),
                    'group': chat_data.get('group', '')
                }, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved backup of model response for message_id={message_id}")
        except Exception as e:
            logger.error(f"Error saving response backup: {str(e)}")

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
        
        # Sanitize model_response if present
        if 'model_response' in interaction_data and interaction_data['model_response'] is not None:
            # Convert to string if not already
            if not isinstance(interaction_data['model_response'], str):
                interaction_data['model_response'] = str(interaction_data['model_response'])
            
            # Replace semicolons with commas to avoid delimiter issues
            interaction_data['model_response'] = interaction_data['model_response'].replace(';', ',')
            
            # Replace newlines with space + pipe + space for better readability
            interaction_data['model_response'] = interaction_data['model_response'].replace('\n', ' | ')
            
            # Replace quotes with single quotes to avoid CSV quoting issues
            interaction_data['model_response'] = interaction_data['model_response'].replace('"', "'")
            
            # Handle markdown formatting symbols
            interaction_data['model_response'] = interaction_data['model_response'].replace('**', '*')

        # Ensure message_id is always present with a structured format
        if 'message_id' not in interaction_data or not interaction_data['message_id']:
            user_id = interaction_data.get('user_id', '')
            task_id = interaction_data.get('task_id', 0)
            try:
                interaction_data['message_id'] = self.generate_structured_message_id(user_id, task_id)
            except Exception as e:
                # Fallback if method fails
                logger.error(f"Error generating structured message ID: {str(e)}")
                # Generate a simple fallback message ID
                user_prefix = user_id[:8] if user_id else "unknown"
                timestamp = datetime.now().strftime("%H%M%S")
                interaction_data['message_id'] = f"{user_prefix}_task{task_id}_{timestamp}"

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
        
        # Make sure all text fields are at least empty strings
        text_fields = ['original_prompt', 'modified_prompt', 'model_response', 'highlighted_terms']
        for field in text_fields:
            if field in interaction_data and interaction_data[field] is None:
                interaction_data[field] = ''
                
        # Also save a JSON backup for any interaction with model_response
        if 'model_response' in interaction_data and interaction_data['model_response']:
            self._save_response_backup(interaction_data)
        
        # Save to CSV with proper escaping
        try:
            df = safe_concat_dataframe(df, interaction_data)
            self._safe_save_df(df, filepath)
        except Exception as e:
            logger.error(f"Error saving interaction to CSV: {str(e)}")
            # Fallback: write directly with robust quoting
            try:
                with open(filepath, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, delimiter=';', 
                                       quoting=csv.QUOTE_MINIMAL,
                                       escapechar='\\')
                    # Create a row with only the values we have
                    row = []
                    for header in df.columns:
                        row.append(interaction_data.get(header, ''))
                    writer.writerow(row)
            except Exception as e2:
                logger.error(f"Critical error writing interaction: {str(e2)}")
        
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
                                   'prompt_count', 'start_time', 'end_time', 'model_type', 'model_name', 'group'])
            
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
            
            # Handle task_number field which might be present instead of task_id
            if 'task_number' in survey_data and not task_id:
                task_id = survey_data['task_number']
            
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
                # Add all standard fields expected in the CSV
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
                'end_time': survey_data.get('end_time', ''),      # Duplicate to match existing schema
                'model_type': survey_data.get('model_type', ''),
                'model_name': survey_data.get('model_name', ''),
                'group': survey_data.get('group', '')
            }
            
            # If survey_data is provided as a string (JSON), store it directly
            if 'survey_data' not in mapped_data and isinstance(survey_data, dict):
                try:
                    # Create a clean copy without large text fields
                    survey_data_copy = {k: v for k, v in survey_data.items() 
                                        if k != 'medical_inaccuracies' and not isinstance(v, (dict, list))}
                    mapped_data['survey_data'] = json.dumps(survey_data_copy)
                except Exception as e:
                    logger.error(f"Error serializing survey data: {str(e)}")
            
            # Debug mapped data
            print(f"DEBUG - Mapped data field values:")
            print(f"  PE_difficulty: '{mapped_data.get('PE_difficulty', 'MISSING')}'")
            print(f"  PE_understanding: '{mapped_data.get('PE_understanding', 'MISSING')}'")
            print(f"  CL_mental: '{mapped_data.get('CL_mental', 'MISSING')}'")
            print(f"  CL_frustration: '{mapped_data.get('CL_frustration', 'MISSING')}'")
            print(f"  MQ_accuracy: '{mapped_data.get('MQ_accuracy', 'MISSING')}'")
        
            # Check if the file exists and get existing headers
            existing_headers = []
            if os.path.exists(tasks_file):
                try:
                    with open(tasks_file, 'r', newline='') as read_f:
                        reader = csv.reader(read_f, delimiter=';')
                        existing_headers = next(reader)
                except Exception as e:
                    logger.error(f"Error reading task file headers: {str(e)}")
            
            # If we couldn't read headers, use default set
            if not existing_headers:
                existing_headers = [
                    'user_id', 'task_id', 'completion_status', 'task_duration', 'timestamp',
                    'task_start', 'task_end', 'PE_difficulty', 'PE_understanding', 
                    'CL_mental', 'CL_frustration', 'MQ_accuracy', 'MQ_usefulness', 
                    'MQ_inaccuracies', 'CL_performance', 'prompt_count'
                ]
            
            print(f"DEBUG - CSV headers: {existing_headers}")
                
            # Avoid duplicate entries by checking if this task entry already exists
            existing_entries = []
            if os.path.exists(tasks_file):
                try:
                    # Read existing data
                    with open(tasks_file, 'r', newline='') as f:
                        reader = csv.DictReader(f, delimiter=';', fieldnames=existing_headers)
                        next(reader)  # Skip header
                        for row in reader:
                            existing_entries.append(row)
                    
                    # Check for existing entry
                    for i, entry in enumerate(existing_entries):
                        if (entry.get('user_id') == str(user_id) and 
                            entry.get('task_id') == str(task_id)):
                            # Update existing entry
                            for key, value in mapped_data.items():
                                if key in existing_headers:
                                    existing_entries[i][key] = value
                            
                            # Rewrite the entire file
                            with open(tasks_file, 'w', newline='') as f:
                                writer = csv.DictWriter(f, fieldnames=existing_headers, delimiter=';')
                                writer.writeheader()
                                writer.writerows(existing_entries)
                            return
                except Exception as e:
                    logger.error(f"Error checking for existing task entry: {str(e)}")
            
            # If no existing entry was found, append new data
            with open(tasks_file, 'a', newline='') as f:
                # Create a row with only fields that exist in the headers
                row_data = {k: v for k, v in mapped_data.items() if k in existing_headers}
                
                # Handle missing fields by adding empty values
                for header in existing_headers:
                    if header not in row_data:
                        row_data[header] = ''
                
                writer = csv.DictWriter(f, fieldnames=existing_headers, delimiter=';')
                writer.writerow(row_data)
                
                # Debug what was actually written
                print(f"DEBUG - Row data written to CSV:")
                for key in ['PE_difficulty', 'PE_understanding', 'CL_mental', 'CL_frustration', 'MQ_accuracy']:
                    print(f"  {key}: '{row_data.get(key, 'NOT IN ROW')}'")
                
        except Exception as e:
            error_msg = f"Error saving task survey: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self._log_storage_event(error_msg, "ERROR")
            
            # Attempt direct file writing as last resort
            try:
                with open(tasks_file, 'a', newline='') as f:
                    writer = csv.writer(f, delimiter=';')
                    # Write all fields including the problematic ones
                    row_values = [
                        user_id, task_id, 'completed', 
                        survey_data.get('task_duration', 0.0),
                        datetime.now().isoformat(),
                        survey_data.get('start_time', ''),
                        survey_data.get('end_time', ''),
                        # Add the missing fields explicitly
                        str(survey_data.get('difficulty', '')),
                        str(survey_data.get('expectation_match', '')),
                        str(survey_data.get('mental_demand', '')),
                        str(survey_data.get('frustration', '')),
                        str(survey_data.get('accuracy', '')),
                        str(survey_data.get('clinical_usefulness', '')),
                        survey_data.get('medical_inaccuracies', ''),
                        str(survey_data.get('task_accomplishment', '')),
                        survey_data.get('prompt_count', 0)
                    ]
                    writer.writerow(row_values)
                    print(f"DEBUG - Emergency write completed with {len(row_values)} fields")
            except Exception as ex:
                error_msg = f"Critical error saving task data: {str(ex)}\n{traceback.format_exc()}"
                logger.critical(error_msg)
                self._log_storage_event(error_msg, "CRITICAL")

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
        Save highlight metrics data to a CSV file
        
        Args:
            user_id (str): The unique user identifier
            task_number (int): The task number 
            group (str): The user's assigned group
            metrics_data (dict): Dictionary containing highlight metrics
        """
        try:
            # Create file path for highlight metrics
            os.makedirs(self.data_dir, exist_ok=True)
            metrics_file = os.path.join(self.data_dir, "highlight_metrics.csv")
            
            # Create file with headers if it doesn't exist
            if not os.path.exists(metrics_file):
                with open(metrics_file, 'w', newline='') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow([
                        'user_id', 'task_id', 'group', 'timestamp', 
                        'metric_type', 'metric_value', 'metric_count'
                    ])
            
            # Format metrics data as rows for CSV
            timestamp = datetime.now().isoformat()
            rows = []
            
            # If metrics_data is a dictionary with nested values, flatten it
            if isinstance(metrics_data, dict):
                for metric_type, value in metrics_data.items():
                    # Handle both scalar values and dictionaries/lists
                    if isinstance(value, (dict, list)):
                        # For complex types, store as JSON string
                        row = [user_id, task_number, group, timestamp, 
                               metric_type, json.dumps(value), 1]
                    else:
                        # For scalar values, store directly
                        row = [user_id, task_number, group, timestamp, 
                               metric_type, value, 1]
                    rows.append(row)
            else:
                # If metrics_data is not a dictionary, save as a single row
                rows.append([user_id, task_number, group, timestamp, 
                             'raw_metrics', json.dumps(metrics_data), 1])
            
            # Append rows to CSV
            with open(metrics_file, 'a', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerows(rows)
            
            # Also save complete raw data as JSON for backup
            backup_file = os.path.join(
                self.data_dir,
                f"highlight_metrics_{user_id}_task{task_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            )
            with open(backup_file, 'w') as f:
                json.dump({
                    "user_id": user_id,
                    "task_id": task_number,
                    "group": group,
                    "metrics": metrics_data,
                    "timestamp": timestamp
                }, f, indent=2)
                
            return True
        except Exception as e:
            error_msg = f"Error saving highlight metrics: {str(e)}"
            logger.error(error_msg)
            self._log_storage_event(error_msg, "ERROR")
            return False

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
        
        # Fix for FutureWarning: Fill any NA values in new_row to avoid concatenation warnings
        for col in new_row.columns:
            if pd.api.types.is_numeric_dtype(new_row[col]):
                new_row[col] = new_row[col].fillna(0)  # Fill numeric NAs with 0
            else:
                new_row[col] = new_row[col].fillna('')  # Fill string NAs with empty string
                
        # Concatenate the dataframes with explicit dtypes to avoid warnings
        try:
            self.prompt_df = pd.concat([self.prompt_df, new_row], ignore_index=True, sort=False)
        except Exception as e:
            logger.error(f"Error concatenating dataframes: {str(e)}")
            # Alternative approach - append row by row
            for _, row in new_row.iterrows():
                self.prompt_df = self.prompt_df.append(row, ignore_index=True)
        
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
            # Ensure the feedback directory exists
            os.makedirs(self.feedback_dir, exist_ok=True)

            # Initialize placeholders
            model_output = None
            model_prompt = None
            response_timestamp = None
            
            # Attach extra metadata to feedback
            if feedback_data.get('model_response'):
                model_output = feedback_data['model_response']
            if feedback_data.get('original_prompt'):
                model_prompt = feedback_data['original_prompt']
            if feedback_data.get('timestamp'):
                response_timestamp = feedback_data['timestamp']

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

            # Feedback log CSV - ensure all required columns exist
            feedback_log = os.path.join(self.data_dir, 'feedback.csv')
            if not os.path.exists(feedback_log):
                with open(feedback_log, 'w', newline='') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow([
                        'user_id', 'message_id', 'response_message_id', 'feedback_value',
                        'timestamp', 'prompt_hash', 'prompt_excerpt', 'response_excerpt',
                        'response_timestamp', 'task_id', 'group'
                    ])

            # Get task_id and group from session_state if available
            task_id = self._extract_task_id_from_message_id(message_id)
            group = 'unknown'
            try:
                import streamlit as st
                if 'group' in st.session_state:
                    group = st.session_state.get('group', 'unknown')
            except ImportError:
                pass

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
                    feedback_data.get('response_timestamp', ''),
                    task_id,
                    group
                ])

            # Log interaction for feedback - Make sure action field is set correctly
            interaction_data = {
                'user_id': user_id,
                'action_type': 'FEEDBACK',  # Make sure this matches column name
                'message_id': message_id,
                'original_prompt': feedback_data.get('original_prompt', ''),
                'model_response': feedback_data.get('model_response', ''),
                'feedback': feedback_data.get('feedback_value', ''),
                'feedback_timestamp': datetime.now().isoformat(),
                'timestamp': datetime.now().isoformat(),
                'response_message_id': feedback_data.get('response_message_id', message_id),
                'task_id': task_id
            }

            # Add a safe check for the action_type field
            try:
                # First check if we need to update the interactions.csv file
                interactions_file = os.path.join(self.data_dir, 'interactions.csv')
                if os.path.exists(interactions_file):
                    # Check if the action_type column exists
                    with open(interactions_file, 'r', newline='') as f:
                        reader = csv.reader(f, delimiter=';')
                        headers = next(reader, [])
                        
                    if 'action_type' not in headers and 'action' in headers:
                        # If only 'action' exists, rename it as 'action_type' in future entries
                        interaction_data['action'] = interaction_data['action_type']
                        del interaction_data['action_type']
                        
                self.log_interaction(interaction_data)
            except Exception as inner_e:
                # Log error but continue with direct feedback save
                logger.warning(f"Error logging feedback via interaction: {str(inner_e)}")
                # Try to save directly to feedback.csv as a fallback
                
            self._log_storage_event(f"Saved feedback for user {user_id}, message {message_id}, prompt hash {prompt_hash}")
            return True

        except Exception as e:
            error_msg = f"Error saving feedback: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self._log_storage_event(error_msg, "ERROR")
            return False

    def save_chat_history(self, user_id: str, task_id: int, messages: List[Dict]) -> str:
        """Save chat history for a user and task to both CSV and JSON formats"""
        try:
            # Ensure directories exist
            chat_dir = os.path.join(self.data_dir, 'chat_history')
            merged_dir = os.path.join(self.data_dir, 'merged_data')
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
                    'feedback': message.get('feedback', None),  # Include feedback if available
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
            return ""
    
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
    
    # Add this method to extract task_id from message_id
    def _extract_task_id_from_message_id(self, message_id: str) -> int:
        """Extract task ID from a message ID if possible"""
        try:
            if not message_id or '_task' not in message_id:
                return 0
                
            # Try to extract task number from format "prefix_task{num}_prompt{num}"
            parts = message_id.split('_')
            for i, part in enumerate(parts):
                if part == 'task' and i + 1 < len(parts):
                    task_part = parts[i + 1]
                    # Extract just the numeric part
                    task_id = ''.join(c for c in task_part if c.isdigit())
                    if task_id:
                        return int(task_id)
            return 0
        except Exception as e:
            logger.error(f"Error extracting task ID from message ID '{message_id}': {str(e)}")
            return 0

    def _append_to_csv(self, filepath, data):
        """Append data to a CSV file with improved handling for text fields"""
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Debug incoming data text fields
        text_fields = ['FB_likes', 'FB_improvements', 'FB_clinical', 'FB_other', 
                       'EX_edit_reason', 'EX_comment', 'EX_edit_changed',
                       'clinical_reasoning_desc', 'specialization', 'expectations',
                       'EX_highlight_meaning', 'EX_highlight_missed_terms', 'TR_trust_other']
        
        logger.info(f"Appending data to CSV: {filepath}")
        logger.info(f"Data keys: {list(data.keys())}")
        
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
        
        # If the file doesn't exist, create it with headers
        headers = []
        if not os.path.exists(filepath):
            # For surveys.csv, ensure we include all expected columns
            if 'surveys.csv' in filepath:
                headers = [
                    'user_id', 'timestamp', 'group',
                    # Usability
                    'US_ease', 'US_clarity', 'US_reuse', 
                    # Trust
                    'TR_model_trust', 'TR_understanding', 'TR_current_trust', 'TR_explanations', 'TR_trust_factors', 'TR_trust_other',
                    # Feedback
                    'FB_likes', 'FB_improvements', 'FB_clinical_yn', 'FB_clinical', 'FB_other',
                    # Explainability
                    'EX_helpful', 'EX_refinement', 'EX_understanding', 'EX_trust',
                    'EX_terms_useful', 'EX_edit_helpful', 'EX_edit_understanding',
                    'EX_self_efficacy', 'EX_clarity', 'EX_edit_changed',
                    'EX_highlight_meaning', 'EX_highlight_missed_terms', 'EX_edit_reason', 'EX_reuse', 'EX_comment',
                    # Additional fields
                    'login_time', 'logout_time'
                ]
            else:
                # Use the keys from the data
                headers = list(data.keys())
                
            # Create the file with headers
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers, delimiter=';',
                                       quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
        
        # Get existing headers if file exists
        else:
            try:
                with open(filepath, 'r', newline='') as read_file:
                    reader = csv.reader(read_file, delimiter=';')
                    headers = next(reader, [])
            except Exception as e:
                logger.error(f"Error reading headers from {filepath}: {e}")
                # Fall back to data keys
                headers = list(data.keys())
        
        # Debug the headers we're working with
        logger.info(f"CSV headers: {headers}")
        
        # Make sure all required headers are present for surveys.csv
        if 'surveys.csv' in filepath and len(headers) < 10:  # Sanity check for minimal headers
            logger.warning(f"Headers in {filepath} seem incomplete: {headers}")
            # Use a comprehensive set of headers
            headers = [
                'user_id', 'timestamp', 'group',
                # Usability
                'US_ease', 'US_clarity', 'US_reuse', 
                # Trust
                'TR_model_trust', 'TR_understanding', 'TR_current_trust', 'TR_explanations', 'TR_trust_factors', 'TR_trust_other',
                # Feedback
                'FB_likes', 'FB_improvements', 'FB_clinical_yn', 'FB_clinical', 'FB_other',
                # Explainability
                'EX_helpful', 'EX_refinement', 'EX_understanding', 'EX_trust',
                'EX_terms_useful', 'EX_edit_helpful', 'EX_edit_understanding',
                'EX_self_efficacy', 'EX_clarity', 'EX_edit_changed',
                'EX_highlight_meaning', 'EX_highlight_missed_terms', 'EX_edit_reason', 'EX_reuse', 'EX_comment',
                # Additional fields
                'login_time', 'logout_time'
            ]
            
            # Create a new file with the full headers
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers, delimiter=';',
                                       quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
        
        # Ensure data contains all headers (with empty strings for missing fields)
        for header in headers:
            if header not in data:
                data[header] = ''
        
        # Write the row with values for all headers
        try:
            with open(filepath, 'a', newline='') as f:
                writer = csv.DictWriter(
                    f, 
                    fieldnames=headers, 
                    delimiter=';',
                    quoting=csv.QUOTE_NONNUMERIC,  # Quote all non-numeric fields
                    quotechar='"',                 # Use double quotes for quoting
                    escapechar='\\'                # Use backslash as escape character
                )
                writer.writerow(data)
                logger.info(f"Successfully wrote row to {filepath}")
        except Exception as e:
            logger.error(f"Error writing to {filepath}: {e}")
            # Try one more time with a more basic approach
            try:
                with open(filepath, 'a', newline='') as f:
                    row_values = [data.get(header, '') for header in headers]
                    csv.writer(f, delimiter=';').writerow(row_values)
                    logger.info(f"Successfully wrote row with basic writer to {filepath}")
            except Exception as e2:
                logger.error(f"Critical error writing to {filepath}: {e2}")
                raise
    
        return data

    def log_survey(self, survey_data: Dict) -> bool:
        """
        Save final survey responses to surveys.csv
        
        Args:
            survey_data (Dict): Survey response data with all fields
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Log debug information
            logger.info(f"Saving survey data for user: {survey_data.get('user_id', 'unknown')}")
            
            # Ensure directory exists
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Define filepath for surveys
            filepath = os.path.join(self.data_dir, 'surveys.csv')
            
            # Create backup of survey data in JSON format for redundancy
            backup_dir = os.path.join(self.data_dir, 'survey_backups')
            os.makedirs(backup_dir, exist_ok=True)
            backup_file = os.path.join(
                backup_dir, 
                f"{survey_data.get('user_id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            # Save backup
            with open(backup_file, 'w') as f:
                json.dump(survey_data, f, indent=2)
            
            # Pre-process text fields to avoid CSV issues
            text_fields = ['FB_likes', 'FB_improvements', 'FB_clinical', 'FB_other', 
                          'EX_highlight_meaning', 'EX_highlight_missed_terms', 
                          'EX_edit_reason', 'EX_comment', 'TR_trust_other']
            
            for field in text_fields:
                if field in survey_data and survey_data[field] is not None:
                    # Convert to string if not already
                    if not isinstance(survey_data[field], str):
                        survey_data[field] = str(survey_data[field])
                    
                    # Clean text data to avoid CSV formatting issues
                    survey_data[field] = (survey_data[field]
                        .replace('\n', ' ')
                        .replace('\r', ' ')
                        .replace(';', ','))  # Replace semicolons with commas
                    
                    # Log text field lengths for debugging
                    logger.debug(f"Field {field} length: {len(survey_data[field])}")
                    
                    # Truncate extremely long fields
                    if len(survey_data[field]) > 1000:
                        survey_data[field] = survey_data[field][:997] + "..."
            
            # Ensure numeric fields are properly formatted
            numeric_fields = [
                'US_ease', 'US_clarity', 'US_reuse', 
                'TR_model_trust', 'TR_understanding', 'TR_current_trust', 'TR_explanations',
                'EX_edit_helpful', 'EX_self_efficacy', 'EX_terms_useful',
                'EX_refinement', 'EX_helpful', 'EX_reuse', 'EX_trust', 'EX_edit_understanding',
                'EX_clarity', 'EX_understanding'
            ]
            
            for field in numeric_fields:
                if field in survey_data:
                    # Convert string values with format "1 - Text" to just "1"
                    if isinstance(survey_data[field], str) and ' - ' in survey_data[field]:
                        survey_data[field] = survey_data[field].split(' - ')[0]
                    
                    # Ensure it's a valid number or empty
                    try:
                        if survey_data[field] is not None and survey_data[field] != '':
                            survey_data[field] = int(survey_data[field])
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert {field} value to integer: {survey_data[field]}")
                        survey_data[field] = None
            
            # Add timestamp if not provided
            if 'timestamp' not in survey_data:
                survey_data['timestamp'] = datetime.now().isoformat()
            
            # Debug the data before saving
            logger.info(f"Survey data fields: {list(survey_data.keys())}")
            logger.info(f"Text fields values:")
            for field in text_fields:
                if field in survey_data:
                    logger.info(f"  {field}: {survey_data.get(field, 'NOT PRESENT')}")
                    
            # Only use one method to save to CSV to avoid duplication
            try:
                # Get existing headers
                headers = []
                if os.path.exists(filepath):
                    with open(filepath, 'r', newline='') as f:
                        reader = csv.reader(f, delimiter=';')
                        headers = next(reader, [])
                
                # If headers don't exist, use a predefined set
                if not headers:
                    headers = [
                        'user_id', 'timestamp', 'group',
                        # Usability
                        'US_ease', 'US_clarity', 'US_reuse', 
                        # Trust
                        'TR_model_trust', 'TR_understanding', 'TR_current_trust', 'TR_explanations', 'TR_trust_factors', 'TR_trust_other',
                        # Feedback
                        'FB_likes', 'FB_improvements', 'FB_clinical_yn', 'FB_clinical', 'FB_other',
                        # Explainability
                        'EX_helpful', 'EX_refinement', 'EX_understanding', 'EX_trust',
                        'EX_terms_useful', 'EX_edit_helpful', 'EX_edit_understanding',
                        'EX_self_efficacy', 'EX_clarity', 'EX_edit_changed',
                        'EX_highlight_meaning', 'EX_highlight_missed_terms', 'EX_edit_reason', 'EX_reuse', 'EX_comment',
                        # Additional fields
                        'login_time', 'logout_time'
                    ]
                    
                    # Create file with headers
                    with open(filepath, 'w', newline='') as f:
                        writer = csv.writer(f, delimiter=';')
                        writer.writerow(headers)
                
                # Check if this user already has a survey entry and update it instead of adding a duplicate
                existing_entries = []
                user_entry_index = -1
                
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r', newline='') as f:
                            reader = csv.DictReader(f, delimiter=';', fieldnames=headers)
                            next(reader)  # Skip header
                            
                            for i, row in enumerate(reader):
                                existing_entries.append(row)
                                if row.get('user_id') == survey_data.get('user_id'):
                                    user_entry_index = i
                    except Exception as e:
                        logger.error(f"Error reading existing survey entries: {str(e)}")
                
                if user_entry_index >= 0:
                    # Update existing entry instead of adding a new one
                    logger.info(f"Updating existing survey entry for user {survey_data.get('user_id')}")
                    for key, value in survey_data.items():
                        if key in headers:
                            existing_entries[user_entry_index][key] = value
                    
                    # Rewrite the entire file
                    with open(filepath, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=headers, delimiter=';')
                        writer.writeheader()
                        writer.writerows(existing_entries)
                else:
                    # Prepare row with proper field ordering for a new entry
                    row_data = {}
                    for header in headers:
                        row_data[header] = survey_data.get(header, '')
                    
                    # Append row to CSV
                    with open(filepath, 'a', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=headers, delimiter=';')
                        writer.writerow(row_data)
                
                logger.info(f"Successfully wrote survey data to CSV")
            except Exception as e:
                logger.error(f"Error writing to CSV: {str(e)}")
                # Use the _append_to_csv helper function as a fallback
                self._append_to_csv(filepath, survey_data)
            
            # Write to emergency backup in case normal CSV write fails
            emergency_backup = os.path.join(self.data_dir, 'emergency_surveys.json')
           
           
            try:
                existing_data = []
                if os.path.exists(emergency_backup):
                    with open(emergency_backup, 'r') as f:
                        existing_data = json.load(f)
                        if not isinstance(existing_data, list):
                            existing_data = []
                
                existing_data.append(survey_data)
                
                with open(emergency_backup, 'w') as f:
                    json.dump(existing_data, f, indent=2)
            except Exception as backup_err:
                logger.error(f"Failed to write emergency backup: {str(backup_err)}")
            
            logger.info(f"Successfully saved survey data for user: {survey_data.get('user_id', 'unknown')}")
            return True
            
        except Exception as e:
            error_msg = f"Error saving survey: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self._log_storage_event(error_msg, "ERROR")
            
            # Try emergency direct write
            try:
                emergency_file = os.path.join(
                    self.data_dir, 
                    f"emergency_survey_{survey_data.get('user_id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                with open(emergency_file, 'w') as f:
                    json.dump(survey_data, f, indent=2)
                logger.info(f"Emergency survey backup saved to {emergency_file}")
            except Exception as emergency_err:
                logger.critical(f"Failed even emergency survey backup: {str(emergency_err)}")
            
            return False

    def update_chat_with_response(self, chat_data: Dict) -> None:
        """Update an existing CHAT entry with a model response"""
        try:
            # Find and update the corresponding CHAT entry in interactions.csv
            interactions_file = os.path.join(self.data_dir, 'interactions.csv')
            if not os.path.exists(interactions_file):
                logger.warning(f"Cannot update chat with response: {interactions_file} does not exist")
                return
                
            # Sanitize the model response to avoid CSV formatting issues
            if 'model_response' in chat_data and chat_data['model_response'] is not None:
                # Convert to string if not already
                if not isinstance(chat_data['model_response'], str):
                    chat_data['model_response'] = str(chat_data['model_response'])
                
                # Replace semicolons with commas to avoid delimiter issues
                chat_data['model_response'] = chat_data['model_response'].replace(';', ',')
                
                # Replace newlines with space + pipe + space for better readability
                chat_data['model_response'] = chat_data['model_response'].replace('\n', ' | ')
                
                # Replace quotes with single quotes to avoid CSV quoting issues
                chat_data['model_response'] = chat_data['model_response'].replace('"', "'")
                
                # Handle markdown formatting symbols
                chat_data['model_response'] = chat_data['model_response'].replace('**', '*')
            
            # Load interactions CSV with pandas for more robust handling
            try:
                df = pd.read_csv(interactions_file, sep=';', quoting=csv.QUOTE_MINIMAL, 
                                 escapechar='\\', encoding='utf-8')
                
                # Find matching rows
                mask = ((df['message_id'] == chat_data.get('message_id')) & 
                        (df['user_id'] == chat_data.get('user_id')) &
                        (df['task_id'].astype(str) == str(chat_data.get('task_id'))))
                
                if mask.any():
                    # Update model_response field for matching rows
                    df.loc[mask, 'model_response'] = chat_data.get('model_response', '')
                    
                    # Save back to CSV with proper escaping
                    df.to_csv(interactions_file, sep=';', index=False, quoting=csv.QUOTE_MINIMAL,
                             escapechar='\\', encoding='utf-8')
                    logger.info(f"Updated chat entry with model response for message_id={chat_data.get('message_id')}")
                    
                    # Also save a backup of the response in JSON format for reliable retrieval
                    self._save_response_backup(chat_data)
                    return
                
                # If no matching row found, log a new entry
                self.log_interaction({
                    'user_id': chat_data.get('user_id', 'unknown'),
                    'task_id': chat_data.get('task_id', 0),
                    'action_type': 'CHAT_RESPONSE',
                    'event_type': 'INTERACTION',
                    'timestamp': chat_data.get('timestamp', datetime.now().isoformat()),
                    'message_id': chat_data.get('message_id', ''),
                    'model_response': chat_data.get('model_response', ''),
                    'model_type': chat_data.get('model_type', ''),
                    'model_name': chat_data.get('model_name', ''),
                    'group': chat_data.get('group', '')
                })
                
                # Also save a backup of the response in JSON format
                self._save_response_backup(chat_data)
                
            except Exception as e:
                logger.error(f"Error updating chat with pandas: {str(e)}")
                
                # Fallback to CSV reader/writer approach
                updated = False
                rows = []
                headers = []
                
                with open(interactions_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f, delimiter=';')
                    headers = next(reader)  # Get headers
                    
                    # Make sure 'model_response' is in headers
                    if 'model_response' not in headers:
                        headers.append('model_response')
                    
                    for row in reader:
                        row_data = dict(zip(headers, row + [''] * (len(headers) - len(row))))
                        
                        # Check if this is the CHAT entry we want to update
                        if (row_data.get('action_type') == 'CHAT' and 
                            row_data.get('message_id') == chat_data.get('message_id') and
                            row_data.get('user_id') == chat_data.get('user_id') and
                            str(row_data.get('task_id')) == str(chat_data.get('task_id'))):
                            
                            # Update the model_response field
                            row_data['model_response'] = chat_data.get('model_response', '')
                            updated = True
                        
                        # Convert back to list in the right order
                        row_list = [row_data.get(h, '') for h in headers]
                        rows.append(row_list)
                
                # If we found and updated a row, write the file back
                if updated:
                    with open(interactions_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL, 
                                          escapechar='\\')
                        writer.writerow(headers)
                        writer.writerows(rows)
                    logger.info(f"Updated chat entry with model response for message_id={chat_data.get('message_id')}")
                    
                    # Also save a backup of the response in JSON format
                    self._save_response_backup(chat_data)
                else:
                    # If we couldn't find the chat to update, log a new entry
                    self.log_interaction({
                        'user_id': chat_data.get('user_id', 'unknown'),
                        'task_id': chat_data.get('task_id', 0),
                        'action_type': 'CHAT_RESPONSE',
                        'event_type': 'INTERACTION',
                        'timestamp': chat_data.get('timestamp', datetime.now().isoformat()),
                        'message_id': chat_data.get('message_id', ''),
                        'model_response': chat_data.get('model_response', ''),
                        'model_type': chat_data.get('model_type', ''),
                        'model_name': chat_data.get('model_name', ''),
                        'group': chat_data.get('group', '')
                    })
                    logger.info(f"Added new chat response entry for message_id={chat_data.get('message_id')}")
                    
                    # Also save a backup of the response in JSON format
                    self._save_response_backup(chat_data)
                    
        except Exception as e:
            error_msg = f"Error updating chat with response: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self._log_storage_event(error_msg, "ERROR")
            
            # Even in case of error, try to save a backup of the response
            try:
                self._save_response_backup(chat_data)
            except Exception as backup_err:
                logger.error(f"Failed to save response backup: {str(backup_err)}")
