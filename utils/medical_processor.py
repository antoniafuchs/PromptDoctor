import pandas as pd
import datasets

class MedicalTermProcessor:
    def __init__(self):
        """Initialize the medical term processor with medical terms"""
        # Fallback medical terms in case dataset loading fails
        self.medical_terms = {
            'fever', 'pain', 'nausea', 'cough', 
            'fatigue', 'dizziness', 'anxiety', 'depression',
            'diabetes', 'asthma', 'hypertension', 'cancer'
        }
        
        try:
            dataset = datasets.load_dataset("gamino/wiki_medical_terms", split="train")
            # Update to use correct column name 'page_title' instead of 'term'
            self.medical_terms.update(
                term.lower() for term in dataset["page_title"] 
                if isinstance(term, str)  # Ensure term is a string
            )
            print(f"Loaded {len(self.medical_terms)} medical terms")
        except Exception as e:
            print(f"Warning: Using fallback medical terms. Error: {e}")

    def highlight_medical_terms(self, text: str) -> str:
        """Highlights medical terms in the text using Streamlit color syntax"""
        if not text:
            return text

        words = text.split()
        highlighted_words = []
        
        for word in words:
            # Clean the word for matching but keep original for display
            clean_word = ''.join(c for c in word.lower() if c.isalnum() or c in ['-', "'"])
            
            if clean_word in self.medical_terms:
                # Updated highlighting syntax to match the example
                highlighted_words.append(f":red[:red-background[{word}]]")
            else:
                highlighted_words.append(word)
        
        return ' '.join(highlighted_words)
