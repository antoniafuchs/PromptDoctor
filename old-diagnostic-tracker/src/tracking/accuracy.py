from typing import List, Dict, Any

class DiagnosticTracker:
    def __init__(self):
        self.ground_truths = []
        self.predictions = []
        self.feedback = []

    def add_ground_truth(self, truth: Any) -> None:
        self.ground_truths.append(truth)

    def add_prediction(self, prediction: Any) -> None:
        self.predictions.append(prediction)

    def log_feedback(self, user_feedback: str) -> None:
        self.feedback.append(user_feedback)

    def calculate_accuracy(self) -> float:
        if len(self.ground_truths) == 0:
            return 0.0
        correct_predictions = sum(1 for truth, pred in zip(self.ground_truths, self.predictions) if truth == pred)
        return correct_predictions / len(self.ground_truths)

    def get_accuracy_metrics(self) -> Dict[str, Any]:
        accuracy = self.calculate_accuracy()
        return {
            "accuracy": accuracy,
            "total_cases": len(self.ground_truths),
            "correct_cases": sum(1 for truth, pred in zip(self.ground_truths, self.predictions) if truth == pred),
            "incorrect_cases": len(self.ground_truths) - sum(1 for truth, pred in zip(self.ground_truths, self.predictions) if truth == pred),
        }