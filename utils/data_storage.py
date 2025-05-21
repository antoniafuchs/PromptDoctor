import pandas as pd
import os
import csv
from datetime import datetime
from typing import Dict, List, Optional, Any
import difflib
import shutil
import json

def safe_concat_dataframe(existing_df: pd.DataFrame, new_data: dict) -> pd.DataFrame:
    """
    Safely concatenate new data to existing DataFrame, handling empty/NA values properly
    """
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
        self._ensure_data_directory()
        self._initialize_csv_files()

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
                         'clinical_reasoning_training', 'clinical_notes_confidence',
                         # AI Experience
                         'gen_ai_familiarity', 'prompt_eng_familiarity', 'cds_familiarity',
                         'tools_used', 'other_tools', 'llm_usage_frequency',
                         # Usage Patterns
                         'use_cases', 'other_use_cases', 'trust_level', 'expectations'],
            
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
                          'US_ease', 'US_clarity', 'US_reuse', 'US_prior_exp',
                          'US_exp_affect', 'US_exp_how', 'US_understanding',
                          # Trust Questions
                          'TR_model_trust', 'TR_understanding', 'TR_explanations',
                          # Feedback Questions
                          'FB_likes', 'FB_improvements', 'FB_clinical', 'FB_other',
                          # Explainability Questions (Group B)
                          'EX_helpful', 'EX_refinement', 'EX_comment',
                          'EX_understanding', 'EX_expectations', 'EX_trust'],

            'logins.csv': ['timestamp', 'user_id', 'group', 'model_type', 'model_name', 'model_display_name'],
            'task_surveys.csv': [
                'timestamp', 'user_id', 'task_number',
                # Task Experience
                'difficulty', 'mental_demand', 'frustration',
                # Clinical Accuracy
                'accuracy', 'task_accomplishment', 'expectation_match',
                # Clinical Utility
                'clinical_usefulness', 'medical_inaccuracies'
            ]
        }

        for filename, headers in files_and_headers.items():
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)

    def _calculate_edit_distance(self, original: str, modified: str) -> float:
        """Calculate normalized Levenshtein distance between prompts"""
        if original is None or modified is None:
            return 0.0
        return difflib.SequenceMatcher(None, str(original), str(modified)).ratio()

    def log_user(self, user_data: Dict) -> None:
        """Log user information"""
        filepath = os.path.join(self.data_dir, 'users.csv')
        df = self._read_or_create_df(filepath, [
            'user_id', 'group', 'login_time', 'logout_time', 'q1_training', 
            'q2_records', 'q3_training', 'q4_confidence', 'q5a_gen_ai', 
            'q5b_prompt', 'q5c_cds', 'q6_tools', 'q7_frequency', 'q8_uses', 
            'q9_trust', 'q10_expectations'
        ])
        
        # Convert likert scales to numeric
        likert_columns = ['q4_confidence', 'q5a_gen_ai', 'q5b_prompt', 'q9_trust']
        for col in likert_columns:
            if col in user_data:
                user_data[col] = int(user_data[col].split(' - ')[0])

        df = safe_concat_dataframe(df, user_data)
        self._safe_save_df(df, filepath)

    def log_task(self, task_data: Dict) -> None:
        """Log task completion data"""
        filepath = os.path.join(self.data_dir, 'tasks.csv')
        df = self._read_or_create_df(filepath, [
            'user_id', 'task_id', 'task_start', 'task_end', 'completion_status',
            'task_duration', 'q1a_difficulty', 'q1b_satisfaction', 'q2a_mental',
            'q3a_accuracy', 'q3d_inaccuracies'
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

        df = safe_concat_dataframe(df, task_data)
        self._safe_save_df(df, filepath)

    def log_interaction(self, interaction_data: Dict) -> None:
        """Log user interaction data"""
        filepath = os.path.join(self.data_dir, 'interactions.csv')
        df = self._read_or_create_df(filepath, [
            'user_id', 'task_id', 'action_type', 'timestamp', 
            'original_prompt', 'modified_prompt', 'model_response',
            'highlighted_terms', 'term_count', 'diff_type', 'feedback',
            'feedback_timestamp', 'message_id'
        ])
        
        # For feedback actions, check if already exists
        if interaction_data.get('action_type') == 'FEEDBACK' and 'message_id' in interaction_data:
            existing = df[
                (df['user_id'] == interaction_data['user_id']) & 
                (df['message_id'] == interaction_data['message_id']) &
                (df['action_type'] == 'FEEDBACK')
            ]
            if not existing.empty:
                return  # Skip if feedback already exists
        
        # Calculate term counts if needed
        if 'highlighted_terms' in interaction_data:
            interaction_data['term_count'] = len(interaction_data['highlighted_terms'].split(','))

        # Ensure feedback is numeric if present
        if 'feedback' in interaction_data:
            feedback_map = {'positive': 1, 'negative': -1, 'neutral': 0}
            interaction_data['feedback'] = feedback_map.get(interaction_data.get('feedback'), None)
            interaction_data['feedback_timestamp'] = datetime.now().isoformat()
        
        df = safe_concat_dataframe(df, interaction_data)
        self._safe_save_df(df, filepath)

    def log_validation(self, validation_data: Dict) -> None:
        """Log prompt validation data"""
        filepath = os.path.join(self.data_dir, 'validation.csv')
        df = self._read_or_create_df(filepath, [
            'user_id', 'task_id', 'timestamp', 'action_type',
            'original_prompt', 'modified_prompt', 'changed_terms',
            'reason_for_change', 'edit_distance'
        ])
        
        # Calculate edit distance only if both prompts exist
        if 'original_prompt' in validation_data and 'modified_prompt' in validation_data:
            original = validation_data.get('original_prompt')
            modified = validation_data.get('modified_prompt')
            if original is not None and modified is not None:
                validation_data['edit_distance'] = self._calculate_edit_distance(original, modified)
            else:
                validation_data['edit_distance'] = 0.0
        else:
            validation_data['edit_distance'] = 0.0

        df = safe_concat_dataframe(df, validation_data)
        self._safe_save_df(df, filepath)

    def log_survey(self, survey_data: Dict) -> None:
        """Log survey responses"""
        filepath = os.path.join(self.data_dir, 'surveys.csv')
        df = self._read_or_create_df(filepath, [
            'user_id', 'timestamp', 'group',
                          # Usability Questions
                          'US_ease', 'US_clarity', 'US_reuse', 'US_prior_exp',
                          'US_exp_affect', 'US_exp_how', 'US_understanding',
                          # Trust Questions
                          'TR_model_trust', 'TR_understanding', 'TR_explanations',
                          # Feedback Questions
                          'FB_likes', 'FB_improvements', 'FB_clinical', 'FB_other',
                          # Explainability Questions (Group B)
                          'EX_helpful', 'EX_refinement', 'EX_comment',
                          'EX_understanding', 'EX_expectations', 'EX_trust'
        ])
        
        # Convert likert scales to numeric
        likert_columns = ['US_ease', 'US_clarity', 'US_reuse', 'TR_model_trust',
                         'TR_understanding', 'TR_explanations', 'EX_helpful',
                         'EX_terms_useful', 'EX_edit_helpful', 'EX_edit_understanding',
                         'EX_self_efficacy', 'EX_valuable', 'EX_clarity', 'EX_learning',
                         'EX_reuse']
        
        for col in likert_columns:
            if col in survey_data and isinstance(survey_data[col], str):
                try:
                    survey_data[col] = int(survey_data[col].split(' - ')[0])
                except (ValueError, IndexError):
                    survey_data[col] = None

        # Ensure timestamp is present
        if 'timestamp' not in survey_data:
            survey_data['timestamp'] = datetime.now().isoformat()

        df = safe_concat_dataframe(df, survey_data)
        self._safe_save_df(df, filepath)

    def save_login_data(self, user_id: str, data: Dict[str, Any]) -> None:
        """Save login data"""
        filepath = os.path.join(self.data_dir, 'logins.csv')
        df = self._read_or_create_df(filepath, ['timestamp', 'user_id', 'group', 'model_type', 'model_name'])
        data.update({'timestamp': datetime.now().isoformat(), 'user_id': user_id})
        df = safe_concat_dataframe(df, data)
        self._safe_save_df(df, filepath)

    def save_task_survey(self, user_id: str, task_number: int, data: Dict[str, Any]) -> None:
        """Save task survey data with fixed field mapping"""
        filepath = os.path.join(self.data_dir, 'task_surveys.csv')
        
        # Define expected fields and their default values
        survey_fields = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'task_number': task_number,
            'difficulty': None,
            'mental_demand': None, 
            'frustration': None,
            'accuracy': None,
            'task_accomplishment': None,
            'expectation_match': None,
            'clinical_usefulness': None,
            'medical_inaccuracies': ''
        }
        
        # Update with provided data
        survey_fields.update(data)
        
        # Convert numeric fields
        numeric_fields = ['difficulty', 'mental_demand', 'frustration', 
                         'accuracy', 'task_accomplishment', 'expectation_match',
                         'clinical_usefulness']
        
        for field in numeric_fields:
            try:
                if survey_fields[field] is not None:
                    survey_fields[field] = int(survey_fields[field])
            except (ValueError, TypeError):
                survey_fields[field] = None
        
        # Load existing data and append new row
        df = self._read_or_create_df(filepath, list(survey_fields.keys()))
        df = safe_concat_dataframe(df, survey_fields)
        self._safe_save_df(df, filepath)

    def merge_user_data(self, user_id: str) -> pd.DataFrame:
        """Merge all data for a user"""
        dfs = []
        for filename in ['users.csv', 'tasks.csv', 'interactions.csv', 'validation.csv', 'surveys.csv', 'logins.csv', 'task_surveys.csv']:
            filepath = os.path.join(self.data_dir, filename)
            if os.path.exists(filepath):
                df = pd.read_csv(filepath, sep=';')
                df = df[df['user_id'] == user_id]
                if not df.empty:
                    dfs.append(df)
        
        if dfs:
            merged = pd.concat(dfs, axis=0, sort=False)
            merged['timestamp'] = pd.to_datetime(merged['timestamp'])
            return merged.sort_values('timestamp')
        return pd.DataFrame()

    def get_recent_validation(self, user_id: str, prompt: str) -> Optional[Dict]:
        """Get most recent validation entry for user/prompt combination"""
        filepath = os.path.join(self.data_dir, 'validation.csv')
        if not os.path.exists(filepath):
            return None
            
        df = pd.read_csv(filepath)
        mask = (df['user_id'] == user_id) & (df['original_prompt'] == prompt)
        if mask.any():
            return df[mask].iloc[-1].to_dict()
        return None

    def get_message_feedback(self, user_id: str, message_id: str) -> dict:
        """Get feedback for a specific message with improved error handling"""
        filepath = os.path.join(self.feedback_dir, f"{user_id}_feedback.csv")
        
        if not os.path.exists(filepath):
            return {}
            
        try:
            # Read CSV with explicit parameters to handle potential formatting issues
            df = pd.read_csv(
                filepath,
                sep=',',
                quoting=csv.QUOTE_ALL,  # Handle all fields as quoted
                escapechar='\\',  # Handle escaped characters
                on_bad_lines='skip',  # Skip problematic lines
                encoding='utf-8'
            )
            
            # If file is empty or has wrong format, return empty dict
            if df.empty or 'message_id' not in df.columns:
                return {}
                
            # Find matching feedback
            feedback = df[df['message_id'] == message_id]
            if not feedback.empty:
                return feedback.iloc[0].to_dict()
            
        except Exception as e:
            print(f"Error reading feedback file: {e}")
            # If file is corrupted, archive it and create new
            self._archive_corrupted_file(filepath)
            
        return {}

    def save_message_feedback(self, user_id: str, message_id: str, feedback_data: dict):
        """Save message feedback with improved error handling"""
        filepath = os.path.join(self.feedback_dir, f"{user_id}_feedback.csv")
        
        # Ensure feedback directory exists
        os.makedirs(self.feedback_dir, exist_ok=True)
        
        # Prepare data as DataFrame
        feedback_df = pd.DataFrame([{
            'message_id': message_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            **feedback_data
        }])
        
        try:
            if os.path.exists(filepath):
                # Read existing with error handling
                existing_df = pd.read_csv(
                    filepath,
                    sep=',',
                    quoting=csv.QUOTE_ALL,
                    escapechar='\\',
                    on_bad_lines='skip',
                    encoding='utf-8'
                )
                # Remove any existing feedback for this message
                existing_df = existing_df[existing_df['message_id'] != message_id]
                feedback_df = pd.concat([existing_df, feedback_df], ignore_index=True)
            
            # Save with proper CSV formatting
            feedback_df.to_csv(
                filepath,
                index=False,
                quoting=csv.QUOTE_ALL,
                escapechar='\\',
                encoding='utf-8'
            )
            
        except Exception as e:
            print(f"Error saving feedback: {e}")
            self._archive_corrupted_file(filepath)
            # Retry save with just new data
            feedback_df.to_csv(
                filepath,
                index=False,
                quoting=csv.QUOTE_ALL,
                escapechar='\\',
                encoding='utf-8'
            )

    def _archive_corrupted_file(self, filepath: str):
        """Archive a corrupted file with timestamp"""
        if not os.path.exists(filepath):
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = os.path.join(os.path.dirname(filepath), "corrupted")
        os.makedirs(archive_dir, exist_ok=True)
        
        filename = os.path.basename(filepath)
        archive_path = os.path.join(archive_dir, f"{filename}.{timestamp}.bak")
        
        try:
            shutil.move(filepath, archive_path)
        except Exception as e:
            print(f"Error archiving corrupted file: {e}")

    def save_prompt_metrics(self, user_id: str, task_number: int, group: str, metrics: dict) -> None:
        """Save prompt metrics for a specific task"""
        metrics_path = self.base_path / 'prompt_metrics'
        metrics_path.mkdir(exist_ok=True)
        
        filename = metrics_path / f"{user_id}_task{task_number}.json"
        data = {
            'user_id': user_id,
            'task_number': task_number,
            'group': group,
            **metrics
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f)

    def save_highlight_metrics(self, user_id: str, task_number: int, 
                             group: str, metrics: dict) -> None:
        """Save highlight coverage metrics for a task"""
        metrics_path = self.base_path / 'highlight_metrics'
        metrics_path.mkdir(exist_ok=True)
        
        filename = metrics_path / f"{user_id}_task{task_number}.json"
        data = {
            'user_id': user_id,
            'task_number': task_number,
            'group': group,
            'timestamp': datetime.now().isoformat(),
            **metrics
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f)
