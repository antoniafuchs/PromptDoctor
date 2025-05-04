from .base import BaseSurvey
import streamlit as st

class LogoutSurvey(BaseSurvey):
    def __init__(self):
        super().__init__("Logout Survey")
    
    def show(self):
        """Display logout survey"""
        with self.survey:
            st.markdown("### Before You Go")
            st.write("Please share your feedback!")
            
            satisfaction = self.survey.radio(
                "Overall experience:",
                options=["😞", "🙁", "😐", "🙂", "😀"],
                horizontal=True
            )
            
            usefulness = self.survey.radio(
                "How useful was PromptDoctor?",
                options=["Not at all", "Slightly", "Moderately", "Very", "Extremely"],
                horizontal=True
            )
            
            features = self.survey.multiselect(
                "Which features did you find most useful?",
                options=[
                    "Chat Interface",
                    "Medical Term Highlighting",
                    "XAI Explanations",
                    "PDF Analysis"
                ]
            )
            
            improvements = self.survey.text_area(
                "Any suggestions for improvements?"
            )
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Submit & Logout"):
                    return {
                        "satisfaction": satisfaction,
                        "usefulness": usefulness,
                        "useful_features": features,
                        "improvements": improvements
                    }
            with col2:
                if st.button("Skip Survey"):
                    return "skip"
        return None
