import pandas as pd
import datasets
import re

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

    def _escape_special_chars(self, text: str) -> str:
        """Escape special characters used in Streamlit markdown"""
        special_chars = '[]:-'
        for char in special_chars:
            text = text.replace(char, '\\' + char)
        return text

    def highlight_medical_terms(self, text: str) -> str:
        """Highlights medical terms in the text using Streamlit color syntax"""
        if not text:
            return text

        # Convert text to lowercase for matching
        text_lower = text.lower()
        result = text
        matches = []

        # Sort terms by length (longest first)
        sorted_terms = sorted(self.medical_terms, key=len, reverse=True)

        for term in sorted_terms:
            # Create pattern with word boundaries
            pattern = r'\b' + re.escape(term) + r'\b'
            for match in re.finditer(pattern, text_lower):
                start, end = match.span()
                original_term = text[start:end]
                escaped_term = self._escape_special_chars(original_term)
                matches.append((start, end, escaped_term))

        # Sort matches by position
        matches.sort(key=lambda x: x[0])
        
        # Apply highlighting in reverse to preserve positions
        for start, end, escaped_term in reversed(matches):
            result = result[:start] + f":red[:red-background[{escaped_term}]]" + result[end:]

        return result
