from .base import BaseSurvey
import streamlit as st

class LoginSurvey(BaseSurvey):
    def __init__(self):
        super().__init__("Login Survey")
    
    def show(self):
        """Display login survey"""
        with self.survey:
            st.markdown("### Quick Survey")
            st.write("Help us improve PromptDoctor!")
            
            role = self.survey.radio(
                "What is your role?",
                options=["Healthcare Professional", "Medical Student", "Researcher", "Other"],
                horizontal=True
            )
            
            experience = self.survey.slider(
                "Years of experience in healthcare",
                0, 30, 5
            )
            
            comfort = self.survey.radio(
                "How comfortable are you with AI tools?",
                options=["😞", "🙁", "😐", "🙂", "😀"],
                horizontal=True
            )
            
            expectations = self.survey.text_area(
                "What are your expectations from PromptDoctor?"
            )
            
            if st.button("Submit Survey"):
                return {
                    "role": role,
                    "experience": experience,
                    "comfort_level": comfort,
                    "expectations": expectations
                }
        return None
