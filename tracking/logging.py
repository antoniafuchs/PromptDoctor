from datetime import datetime
import logging
import os
from typing import List
import difflib

def get_user_logger(user_id: str) -> logging.Logger:
    # Create a directory for logs if it doesn't exist
    log_directory = 'user_logs'
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # Define the log filename based on the user_id
    log_filename = os.path.join(log_directory, f"{user_id}.log")

    # Create or get an existing logger for the user
    logger = logging.getLogger(user_id)

    # Check if handlers already exist to prevent duplicates
    if not logger.hasHandlers():
        handler = logging.FileHandler(log_filename)
        formatter = logging.Formatter('%(asctime)s ; %(levelname)s ; %(message)s')
        handler.setFormatter(formatter)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

    return logger

def log_model_output(user_prompt: str, model_output: str, user_id: str, ground_truth: str = None) -> None:
    logger = get_user_logger(user_id)
    logger.info(f"User Prompt: {user_prompt}")
    logger.info(f"Model Output: {model_output}")
    if ground_truth:
        logger.info(f"Ground Truth: {ground_truth}")
    else:
        logger.info("Ground Truth: Not provided")
    logger.info("-----")

def log_user_interaction(user_id: str, interaction: str) -> None:
    logger = get_user_logger(user_id)
    logger.info(f"Interaction: {interaction}")

def log_task_duration(user_prompt: str, duration: float, user_id: str) -> None:
    logger = get_user_logger(user_id)
    logger.info(f"User Prompt: {user_prompt}")
    logger.info(f"Task Duration: {duration} seconds")
    logger.info("-----")

def log_chat_interaction(
    user_id: str,
    interaction_type: str,
    user_prompt: str = None,
    model_output: str = None,
    model_type: str = None,
    duration: dict = None,
    feedback: str = None
) -> None:
    """Log a chat interaction"""
    logger = get_user_logger(user_id)
    timestamp = datetime.now().isoformat()
    
    log_entry = f"\n=== Interaction at {timestamp} ===\n"
    log_entry += f"Type: {interaction_type}\n"
    
    if user_prompt:
        log_entry += f"User Prompt: {user_prompt}\n"
    if model_type:
        log_entry += f"Model: {model_type}\n"
    if model_output:
        log_entry += f"Model Output: {model_output}\n"
    if duration:
        if isinstance(duration, dict):
            for timing_type, value in duration.items():
                log_entry += f"{timing_type.title()} Duration: {value:.2f} seconds\n"
        else:
            log_entry += f"Duration: {duration:.2f} seconds\n"
    if feedback:
        log_entry += f"Feedback: {feedback}\n"
    
    log_entry += "=" * 50
    logger.info(log_entry)

def _generate_diff(original: str, modified: str) -> str:
    """Generate a human-readable diff between two strings"""
    diff = difflib.ndiff(original.splitlines(keepends=True), 
                        modified.splitlines(keepends=True))
    return ''.join(diff)

def log_validation_action(
    user_id: str,
    action_type: str,
    original_prompt: str,
    highlighted_terms: List[str] = None,
    modified_prompt: str = None,
    medical_term_count: int = 0
) -> None:
    """Log validation stage interactions"""
    logger = get_user_logger(user_id)
    timestamp = datetime.now().isoformat()
    
    log_entry = f"\n=== Validation Action at {timestamp} ===\n"
    log_entry += f"Action: {action_type}\n"
    log_entry += f"Original Prompt: {original_prompt}\n"
    
    if highlighted_terms:
        log_entry += f"Medical Terms: {', '.join(highlighted_terms)}\n"
        log_entry += f"Term Count: {medical_term_count}\n"
    
    if modified_prompt and modified_prompt != original_prompt:
        log_entry += f"Modified Prompt: {modified_prompt}\n"
        log_entry += "Prompt Changes (diff):\n"
        log_entry += _generate_diff(original_prompt, modified_prompt)
        
    log_entry += "=" * 50
    logger.info(log_entry)

def log_lime_explanation(
    user_id: str,
    prompt: str,
    model_response: str,
    explanation_features: List[tuple],
    explanation_duration: float
) -> None:
    """Log LIME explanation details"""
    logger = get_user_logger(user_id)
    timestamp = datetime.now().isoformat()
    
    log_entry = f"\n=== LIME Explanation at {timestamp} ===\n"
    log_entry += f"Original Prompt: {prompt}\n"
    log_entry += f"Model Response: {model_response}\n"
    log_entry += f"Explanation Duration: {explanation_duration:.2f} seconds\n"
    log_entry += "Important Features:\n"
    
    for word, weight in explanation_features:
        log_entry += f"- {word}: {weight:.3f}\n"
    
    log_entry += "=" * 50
    logger.info(log_entry)
