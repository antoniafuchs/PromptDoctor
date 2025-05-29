import pandas as pd
import datasets
import re
import logging
import json
import os
from datetime import datetime
from typing import List, Set, Dict

# Configure logging
logger = logging.getLogger(__name__)

class MedicalTermProcessor:
    def __init__(self):
        """Initialize the medical term processor with medical terms"""
        # Fallback medical terms in case dataset loading fails
        self.medical_terms = {
            'fever', 'pain', 'nausea', 'cough', 
            'fatigue', 'dizziness', 'anxiety', 'depression',
            'diabetes', 'asthma', 'hypertension', 'cancer',
            # Add common terms from our clinical notes
            'pneumonia', 'copd', 'dyspnea', 'chest pain',
            'shortness of breath', 'palpitations', 'hyperlipidemia',
            'cardiomyopathy', 'pulmonary', 'respiratory'
        }
        
        # Track terms usage statistics
        self.term_usage = {}
        self.dataset_source = "fallback"
        
        # Analytics directory
        self.analytics_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'medical_terms')
        os.makedirs(self.analytics_dir, exist_ok=True)
        
        try:
            dataset = datasets.load_dataset("gamino/wiki_medical_terms", split="train")
            # Only store complete page titles
            self.medical_terms = {
                term.lower() for term in dataset["page_title"] 
                if isinstance(term, str)
            }
            self.dataset_source = "gamino/wiki_medical_terms"
            logger.info(f"Loaded {len(self.medical_terms)} medical terms from {self.dataset_source}")
            
            # Save dataset info for analytics
            self.save_dataset_info(dataset)
            
        except Exception as e:
            logger.warning(f"Using fallback medical terms. Error: {e}")
            self.dataset_source = "fallback"

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
                matches.append((start, end, escaped_term, term.lower()))
                
                # Track usage of this term
                self.track_term_usage(term.lower())

        # Sort matches by position
        matches.sort(key=lambda x: x[0])
        
        # Track all highlighted terms in this session
        highlighted_terms = [match[3] for match in matches]
        if highlighted_terms:
            self.track_highlighted_terms(highlighted_terms)
        
        # Apply highlighting in reverse to preserve positions
        for start, end, escaped_term, _ in reversed(matches):
            result = result[:start] + f":red[:red-background[{escaped_term}]]" + result[end:]

        return result

    def track_term_usage(self, term: str) -> None:
        """Track usage of a specific medical term"""
        if term not in self.term_usage:
            self.term_usage[term] = {
                'count': 0,
                'first_seen': datetime.now().isoformat(),
                'last_seen': None
            }
        
        self.term_usage[term]['count'] += 1
        self.term_usage[term]['last_seen'] = datetime.now().isoformat()

    def track_highlighted_terms(self, terms: List[str]) -> None:
        """Track a batch of highlighted terms"""
        # Create a session entry for these terms
        session_entry = {
            'timestamp': datetime.now().isoformat(),
            'terms': terms,
            'count': len(terms),
            'dataset_source': self.dataset_source
        }
        
        # Save to analytics file
        try:
            filepath = os.path.join(self.analytics_dir, 'highlighted_terms.jsonl')
            with open(filepath, 'a') as f:
                f.write(json.dumps(session_entry) + '\n')
        except Exception as e:
            logger.error(f"Error saving highlighted terms: {str(e)}")
        
        # Save term usage stats periodically
        if sum(item['count'] for item in self.term_usage.values()) % 100 == 0:
            self.save_term_usage_stats()

    def get_medical_terms(self, text=None):
        """
        Extract medical terms from the provided text.
        If text is None, return all medical terms.
        """
        if text is None:
            return list(self.medical_terms)
        
        # Extract words from text and check if they're medical terms
        words = text.lower().split()
        found_terms = []
        
        for word in words:
            # Clean the word for term checking (remove punctuation)
            clean_word = word.strip('.,!?;:()"\'')
            if clean_word in self.medical_terms:
                found_terms.append(clean_word)
                # Track usage of this term
                self.track_term_usage(clean_word)
                
        return found_terms
    
    def save_dataset_info(self, dataset) -> None:
        """Save information about the loaded dataset"""
        try:
            filepath = os.path.join(self.analytics_dir, 'dataset_info.json')
            
            info = {
                'source': self.dataset_source,
                'term_count': len(self.medical_terms),
                'loaded_at': datetime.now().isoformat(),
                'sample_terms': list(sorted(list(self.medical_terms)))[:100],  # First 100 terms as sample
            }
            
            with open(filepath, 'w') as f:
                json.dump(info, f, indent=2)
                
            logger.info(f"Saved dataset info to {filepath}")
        except Exception as e:
            logger.error(f"Error saving dataset info: {str(e)}")
    
    def save_term_usage_stats(self) -> None:
        """Save term usage statistics"""
        try:
            filepath = os.path.join(self.analytics_dir, 'term_usage_stats.json')
            
            # Get top terms by usage
            top_terms = sorted(
                [(term, data['count']) for term, data in self.term_usage.items()],
                key=lambda x: x[1],
                reverse=True
            )[:100]  # Top 100 terms
            
            stats = {
                'timestamp': datetime.now().isoformat(),
                'dataset_source': self.dataset_source,
                'total_terms': len(self.medical_terms),
                'terms_used': len(self.term_usage),
                'total_usages': sum(data['count'] for data in self.term_usage.values()),
                'top_terms': dict(top_terms),
                'usage_percentage': len(self.term_usage) / len(self.medical_terms) * 100 if self.medical_terms else 0
            }
            
            with open(filepath, 'w') as f:
                json.dump(stats, f, indent=2)
                
            logger.info(f"Saved term usage stats to {filepath}")
        except Exception as e:
            logger.error(f"Error saving term usage stats: {str(e)}")
