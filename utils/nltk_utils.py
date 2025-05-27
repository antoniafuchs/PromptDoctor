import nltk
import os
import streamlit as st

def ensure_nltk_resources():
    """Ensure all required NLTK resources are downloaded."""
    resources = [
        'punkt',         # For sentence tokenization
        'stopwords',     # Common stopwords
        'wordnet',       # For lemmatization
        'averaged_perceptron_tagger'  # For POS tagging
    ]
    
    missing_resources = []
    for resource in resources:
        try:
            nltk.data.find(f'tokenizers/{resource}' if resource == 'punkt' else resource)
        except (LookupError, EOFError, Exception) as e:
            print(f"[WARNING] Error checking NLTK resource {resource}: {e}")
            missing_resources.append(resource)
    
    if missing_resources:
        # Create data directory if it doesn't exist
        nltk_data_dir = os.path.expanduser('~/nltk_data')
        os.makedirs(nltk_data_dir, exist_ok=True)
        
        # Download missing resources with error handling
        downloaded = []
        for resource in missing_resources:
            try:
                nltk.download(resource, quiet=True)
                downloaded.append(resource)
            except Exception as e:
                print(f"[ERROR] Failed to download NLTK resource {resource}: {e}")
        
        if downloaded:
            return f"Downloaded NLTK resources: {', '.join(downloaded)}"
    
    return None
