def format_api_error(error_message):
    """Format API error messages to be more user-friendly"""
    
    # Handle sleeping endpoint error
    if "503 Server Error: Service Unavailable" in error_message:
        return """
        ### The AI model service is currently waking up
        
        The HuggingFace endpoint is initializing. This typically happens when the service hasn't been used for a while.
        
        **Please wait about 2 minutes and try again.** The model should be ready after that time.
        
        Technical details: 503 Service Unavailable error from HuggingFace.
        """
    
    # Handle rate limiting
    if "429 Too Many Requests" in error_message:
        return """
        ### Rate limit exceeded
        
        You've sent too many requests in a short period of time. 
        
        Please wait a minute before trying again.
        """
    
    # Generic error handling
    return f"""
    ### An error occurred
    
    There was an issue connecting to the AI model. Please try again in a moment.
    
    Technical details: {error_message}
    """
