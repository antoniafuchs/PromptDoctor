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
            df = pd.concat([pd.read_csv(filename), df], ignore_index=True)
        df.to_csv(filename, index=False)

    def save_task_survey(self, user_id: str, task_number: int, data: Dict[str, Any]):
        """Save task survey data"""
        filename = os.path.join(self.base_path, 'task', 'task_surveys.csv')
        
        survey_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'task_number': task_number,
            'difficulty': data.get('difficulty', ''),
            'usefulness': data.get('usefulness', ''),
            'comments': data.get('comments', ''),
            'duration': data.get('duration', '')
        }
        
        df = pd.DataFrame([survey_data])
        if os.path.exists(filename):
            df = pd.concat([pd.read_csv(filename, sep=';'), df], ignore_index=True)
        df.to_csv(filename, sep=';', index=False)

    def save_logout_survey(self, user_id: str, data: Dict[str, Any]):
        """Save logout survey data"""
        filename = os.path.join(self.base_path, 'logout', 'logout_surveys.csv')
        
        survey_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'group': data.get('group', 'unknown'),  # Get group from data instead of session state
            'satisfaction': data.get('satisfaction', ''),
            'feedback': data.get('feedback', ''),
            'tasks_completed': data.get('tasks_completed', 0),
            'survey_duration_seconds': data.get('survey_duration_seconds', 0),
            'login_time': data.get('login_time', ''),
            'logout_time': data.get('logout_time', '')
        }
        
        df = pd.DataFrame([survey_data])
        if os.path.exists(filename):
            df = pd.concat([pd.read_csv(filename, sep=';'), df], ignore_index=True)
        df.to_csv(filename, sep=';', index=False)
