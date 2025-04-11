import os
import uuid  # Import uuid for generating unique user IDs
from dotenv import load_dotenv
from tracking.accuracy import AccuracyTracker
from tracking.logging import Logger
from tracking.feedback import FeedbackCollector
from models.model import DiagnosticModel
from visualization.plot import visualize_prompt_influence

def main():
    load_dotenv()

    # Generate a unique user ID for each session
    user_id = str(uuid.uuid4())
    
    # Initialize components
    model = DiagnosticModel()
    accuracy_tracker = AccuracyTracker()
    logger = Logger()
    feedback_collector = FeedbackCollector()

    # Example usage
    user_prompt = "What is the diagnosis for a patient with a persistent cough?"
    model_output = model.generate_output(user_prompt)
    
    # Log the output
    logger.log_output(user_prompt, model_output, user_id=user_id)
    
    # Collect user feedback
    user_feedback = feedback_collector.collect_feedback(model_output)
    
    # Update accuracy tracking
    ground_truth = "The patient may have a respiratory infection."
    accuracy_tracker.update_accuracy(model_output, ground_truth, user_feedback)
    
    # Visualize prompt influence
    visualize_prompt_influence(user_prompt, model_output)

if __name__ == "__main__":
    main()