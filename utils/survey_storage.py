import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any

class SurveyStorage:
    def __init__(self, base_path: str = "survey_data"):
        self.base_path = base_path
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = ['login', 'task', 'logout']
        for dir_name in directories:
            dir_path = os.path.join(self.base_path, dir_name)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

    def save_login_survey(self, user_id: str, data: Dict[str, Any]):
        """Save login survey data"""
        filename = os.path.join(self.base_path, 'login', 'login_surveys.csv')
        
        survey_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'role': data.get('role', ''),
            'experience': data.get('experience', ''),
            'comfort_level': data.get('comfort_level', ''),
            'expectations': data.get('expectations', '')
        }
        
        df = pd.DataFrame([survey_data])
        if os.path.exists(filename):
            df = pd.concat([pd.read_csv(filename, sep=';'), df], ignore_index=True)
        df.to_csv(filename, sep=';', index=False)

    def save_login_data(self, user_id: str, data: Dict[str, Any]):
        """Save login data"""
        filename = os.path.join(self.base_path, 'login', 'login_data.csv')
        
        login_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'model_type': data.get('model_type', ''),
            'model_name': data.get('model_name', ''),
            'model_display_name': data.get('model_display_name', '')
        }
        
        df = pd.DataFrame([login_data])
        if os.path.exists(filename):
            df = pd.concat([pd.read_csv(filename, sep=';'), df], ignore_index=True)
        df.to_csv(filename, sep=';', index=False)

    def save_task_survey(self, user_id: str, task_number: int, data: Dict[str, Any]):
        """Save task survey data with question code columns"""
        # Create task-specific directory
        task_dir = os.path.join(self.base_path, 'task', f'task_{task_number}')
        os.makedirs(task_dir, exist_ok=True)

        # Organize data by section
        survey_data = {
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'task_number': task_number,
            # Question codes from each section
            'PE_difficulty': data.get('q1a_difficulty'),  # PE = Prompting Experience
            'PE_satisfaction': data.get('q1b_satisfaction'),
            'PE_understanding': data.get('q1c_understanding'),
            'CL_mental': data.get('q2a_mental'),  # CL = Cognitive Load
            'CL_temporal': data.get('q2b_temporal'),
            'CL_effort': data.get('q2c_effort'),
            'CL_performance': data.get('q2d_performance'),
            'CL_frustration': data.get('q2e_frustration'),
            'MQ_accuracy': data.get('q3a_accuracy'),  # MQ = Medical Quality
            'MQ_professional': data.get('q3b_professional'),
            'MQ_usefulness': data.get('q3c_usefulness'),
            'MQ_inaccuracies': data.get('q3d_inaccuracies')
        }
        
        # Save to CSV with semicolon delimiter
        filepath = os.path.join(task_dir, 'task_survey.csv')
        df = pd.DataFrame([survey_data])
        if os.path.exists(filepath):
            df = pd.concat([pd.read_csv(filepath, sep=';'), df], ignore_index=True)
        df.to_csv(filepath, sep=';', index=False)

    def save_logout_survey(self, user_id: str, data: Dict[str, Any]):
        """Save logout survey data with question code columns"""
        # Data is already flattened, use it directly
        survey_data = {
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'group': data.get('group', 'unknown'),
            **data  # Include all flattened fields
        }

        # Save to CSV
        filepath = os.path.join(self.base_path, 'logout', 'logout_surveys.csv')
        df = pd.DataFrame([survey_data])
        if os.path.exists(filepath):
            df = pd.concat([pd.read_csv(filepath, sep=';'), df], ignore_index=True)
        df.to_csv(filepath, sep=';', index=False)

    def merge_survey_data(self, user_id: str) -> pd.DataFrame:
        """Merge all survey data with logging data"""
        # Get logging data
        log_file = os.path.join('user_logs', f'{user_id}.log')
        log_df = pd.read_csv(log_file, delimiter=';') if os.path.exists(log_file) else pd.DataFrame()
        
        dfs = [log_df]

        # Merge task surveys
        for task_num in range(1, 4):
            task_file = os.path.join(self.base_path, 'task', f'task_{task_num}', 'task_survey.csv')
            if os.path.exists(task_file):
                task_df = pd.read_csv(task_file)
                task_df = task_df[task_df['user_id'] == user_id]
                if not task_df.empty:
                    dfs.append(task_df)

        # Merge logout survey
        logout_file = os.path.join(self.base_path, 'logout', 'logout_surveys.csv')
        if os.path.exists(logout_file):
            logout_df = pd.read_csv(logout_file)
            logout_df = logout_df[logout_df['user_id'] == user_id]
            if not logout_df.empty:
                dfs.append(logout_df)

        # Merge all dataframes
        if len(dfs) > 1:
            merged_df = pd.concat(dfs, axis=0, sort=False)
            merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp'])
            return merged_df.sort_values('timestamp')
        
        return log_df
