from .base import BaseSurvey
import streamlit as st

class TaskSurvey(BaseSurvey):
    def __init__(self, task_number):
        super().__init__(f"Task {task_number} Survey")
        self.task_number = task_number
    
    def show(self):
        with self.survey:
            satisfaction = self.survey.slider(
                "How difficult was this task?",
                1, 5, 3,
                help="1 = Very Easy, 5 = Very Difficult"
            )
            
            completion = self.survey.radio(
                "Did you complete the task successfully?",
                ["Yes", "Partially", "No"]
            )
            
            feedback = self.survey.text_area(
                "Any comments about this task?"
            )
            
            return {
                "task_number": self.task_number,
                "satisfaction": satisfaction,
                "completion": completion,
                "feedback": feedback
            }