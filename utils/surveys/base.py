from streamlit_survey import StreamlitSurvey
import streamlit as st
import json
from datetime import datetime

class BaseSurvey:
    def __init__(self, name: str):
        self.survey = StreamlitSurvey(name)
        self.completed = False
    
    def save_response(self, user_id: str):
        """Save survey response to JSON"""
        data = {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "responses": self.survey.to_json()
        }
        return data
