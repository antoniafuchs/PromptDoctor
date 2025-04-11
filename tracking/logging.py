from datetime import datetime
import logging
import os


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
    duration: dict = None
) -> None:
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
    
    log_entry += "=" * 50
    logger.info(log_entry)
