from typing import Dict, List, Set
from utils.medical_processor import MedicalTermProcessor
import re

class HighlightMetrics:
    def __init__(self):
        self.medical_processor = MedicalTermProcessor()
        
    # LIME highlighted terms for Task 3 (unchanged)
    LIME_HIGHLIGHTS = {
        "female", "includes", "hyperlipidemia", 
        "palpitations", "shortness", "breath"
    }

    # Clinical notes for medical term extraction
    CLINICAL_NOTES = {
        1: """The patient, a 45-year-old male, presents with chief complaints of right-sided chest pain and shortness of breath. He describes the pain as sharp and intermittent, exacerbated by movement or deep inspiration. The patient also reports experiencing fatigue for two weeks but denies fever, cough, or any recent travel.""",
        2: """The patient, an 82-year-old male, presents with community-acquired pneumonia (CAP) complicated by a history of chronic obstructive pulmonary disease (COPD). He reports moderate dyspnea, no fever, and no recent upper respiratory tract infections. The patient has previously been hospitalized for CAP and is on long-term oxygen therapy."""
    }

    def get_medical_terms(self, text: str) -> Set[str]:
        """Extract medical terms from text"""
        text_lower = text.lower()
        medical_terms = set()
        
        for term in self.medical_processor.medical_terms:
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, text_lower):
                medical_terms.add(term)
                
        return medical_terms

    def calculate_coverage(self, task_number: int, prompt: str) -> Dict:
        """Calculate term coverage based on task number"""
        if task_number in [1, 2]:
            # Get medical terms from both clinical note and prompt
            note_terms = self.get_medical_terms(self.CLINICAL_NOTES[task_number])
            prompt_terms = self.get_medical_terms(prompt)
            
            # Calculate intersection
            matched_terms = note_terms & prompt_terms
            
            return {
                'highlight_type': 'medical',
                'matched_terms': list(matched_terms),
                'total_terms': len(note_terms),
                'coverage_percentage': len(matched_terms) / len(note_terms) * 100 if note_terms else 0,
                'all_medical_terms': list(note_terms)  # For reference
            }
            
        elif task_number == 3:
            # Use existing LIME logic
            prompt_lower = prompt.lower()
            matches = {term for term in self.LIME_HIGHLIGHTS if term in prompt_lower}
            return {
                'highlight_type': 'lime',
                'matched_terms': list(matches),
                'total_terms': len(self.LIME_HIGHLIGHTS),
                'coverage_percentage': len(matches) / len(self.LIME_HIGHLIGHTS) * 100
            }
        return {}
