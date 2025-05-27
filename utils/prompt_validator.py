import re
import nltk
import streamlit as st
from utils.nltk_utils import ensure_nltk_resources
from typing import List, Tuple, Dict, Any
from tracking.logging import log_validation_action, _calculate_edit_distance, _determine_diff_type

# Try to ensure NLTK resources with error handling
try:
    ensure_nltk_resources()
except Exception as e:
    print(f"[WARNING] Failed to ensure NLTK resources: {e}")

def validate_prompt(prompt: str, medical_processor, prompt_count: int = 0) -> Tuple[List[str], List[str], bool]:
    """
    Validate and highlight a prompt string
    Returns tuple of (sentences, highlighted_sentences, has_medical_terms)
    """
    # Get current task ID from session state
    task_id = st.session_state.get('current_task', 0)
    user_id = st.session_state.get('user_id', '')
    
    # Split prompt into sentences with better error handling
    try:
        sentences = nltk.sent_tokenize(prompt)
    except Exception as e:
        print(f"[WARNING] Error in sentence tokenization: {str(e)}")
        # Fallback to simple splitting if NLTK fails
        try:
            sentences = re.split(r'(?<=[.!?])\s+', prompt)
            if len(sentences) == 1 and len(prompt) > 0:
                # If still only one sentence but input is not empty,
                # try breaking by newlines or just return the full prompt
                sentences = prompt.split('\n') if '\n' in prompt else [prompt]
        except Exception:
            # Ultimate fallback is just the full prompt as one sentence
            sentences = [prompt]
    
    # Highlight medical terms in each sentence with error handling
    highlighted_sentences = []
    for sentence in sentences:
        try:
            highlighted = medical_processor.highlight_medical_terms(sentence)
            highlighted_sentences.append(highlighted)
        except Exception as e:
            print(f"[WARNING] Error highlighting medical terms: {str(e)}")
            highlighted_sentences.append(sentence)  # Fall back to original
    
    # Check if each sentence has medical terms
    has_medical_terms = any(":red-background" in sentence for sentence in highlighted_sentences)
    
    # Get medical terms with error handling
    try:
        terms = medical_processor.get_medical_terms(prompt)
    except Exception as e:
        print(f"[WARNING] Error extracting medical terms: {str(e)}")
        terms = []
    
    # Generate structured message ID
    user_id_prefix = user_id[:8] if user_id else ''
    message_id = f"task_{task_id}_prompt_{prompt_count}_{user_id_prefix}"
    
    # Log validation action with structured message ID and term count
    try:
        log_validation_action(
            user_id=user_id,
            task_id=task_id,
            action_type="VALIDATION_VIEW",
            original_prompt=prompt,
            highlighted_terms=terms,
            medical_term_count=len(terms),
            prompt_count=prompt_count,
            message_id=message_id
        )
    except Exception as e:
        print(f"[WARNING] Error logging validation action: {str(e)}")
    
    return sentences, highlighted_sentences, has_medical_terms

def add_highlights(sentences, validation_list, bg="red", text="red"):
    """Add visual highlights to sentences with customizable colors"""
    return [
        f":{text}[:{bg}-background[{sentence}]]" if not is_valid else sentence
        for sentence, is_valid in zip(sentences, validation_list)
    ]