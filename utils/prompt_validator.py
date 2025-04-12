import streamlit as st

def validate_prompt(prompt: str, medical_processor):
    """Validate and highlight medical terms in the prompt"""
    # Split prompt into sentences
    prompt_sentences = [s.strip() for s in prompt.split(".") if s.strip()]
    
    # Add periods back
    prompt_sentences = [s + "." for s in prompt_sentences]
    
    # Highlight medical terms in each sentence
    highlighted_sentences = [
        medical_processor.highlight_medical_terms(sentence)
        for sentence in prompt_sentences
    ]
    
    # Check if each sentence has medical terms
    has_medical_terms = [
        ":red-background" in sentence for sentence in highlighted_sentences
    ]
    
    return prompt_sentences, highlighted_sentences, has_medical_terms

def add_highlights(sentences, validation_list, bg="red", text="red"):
    """Add visual highlights to sentences with customizable colors"""
    return [
        f":{text}[:{bg}-background[{sentence}]]" if not is_valid else sentence
        for sentence, is_valid in zip(sentences, validation_list)
    ]