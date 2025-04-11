def process_data(data):
    # Function to process input data
    processed_data = data.strip().lower()
    return processed_data

def validate_input(data):
    # Function to validate user input
    if not data:
        raise ValueError("Input cannot be empty.")
    return True

def format_output(output):
    # Function to format the model output for display
    return f"Output: {output}"