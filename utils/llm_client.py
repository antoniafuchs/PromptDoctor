try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("[INFO] Ollama client package not installed. Install with 'pip install ollama' for better performance.")

# Use OLLAMA_AVAILABLE flag to determine if direct API calls should be used