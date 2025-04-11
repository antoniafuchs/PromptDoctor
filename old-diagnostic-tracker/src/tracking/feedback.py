from typing import List, Dict

class FeedbackTracker:
    def __init__(self):
        self.feedback_data: List[Dict[str, str]] = []

    def collect_feedback(self, user_id: str, model_output: str, user_feedback: str) -> None:
        feedback_entry = {
            "user_id": user_id,
            "model_output": model_output,
            "user_feedback": user_feedback
        }
        self.feedback_data.append(feedback_entry)

    def get_feedback(self) -> List[Dict[str, str]]:
        return self.feedback_data

    def analyze_feedback(self) -> Dict[str, float]:
        total_feedback = len(self.feedback_data)
        if total_feedback == 0:
            return {"positive": 0.0, "negative": 0.0}

        positive_feedback = sum(1 for entry in self.feedback_data if entry["user_feedback"].lower() == "agree")
        negative_feedback = total_feedback - positive_feedback

        return {
            "positive": positive_feedback / total_feedback * 100,
            "negative": negative_feedback / total_feedback * 100
        }