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
            # Only store complete page titles
            self.medical_terms = {
                term.lower() for term in dataset["page_title"] 
                if isinstance(term, str)
            }
            print(f"Loaded {len(self.medical_terms)} medical terms")
        except Exception as e:
            print(f"Warning: Using fallback medical terms. Error: {e}")

    def highlight_medical_terms(self, text: str) -> str:
        """Highlights medical terms in the text using Streamlit color syntax"""
        if not text:
            return text

        # Convert text to lowercase for matching
        text_lower = text.lower()
        result = text
        matches = []

        # Find matches for complete terms only
        for term in self.medical_terms:
            start = 0
            while True:
                pos = text_lower.find(term, start)
                if pos == -1:
                    break
                # Verify it's a complete word/phrase
                before = pos == 0 or not text_lower[pos-1].isalnum()
                after = pos + len(term) == len(text_lower) or not text_lower[pos + len(term)].isalnum()
                if before and after:
                    matches.append((pos, pos + len(term), text[pos:pos + len(term)]))
                start = pos + 1

        # Sort matches by position
        matches.sort(key=lambda x: x[0])
        
        # Apply highlighting in reverse to preserve positions
        for start, end, term in reversed(matches):
            result = result[:start] + f":red[:red-background[{term}]]" + result[end:]

        return result
