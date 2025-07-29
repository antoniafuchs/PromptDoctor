"""
highlight_metrics.py
This file defines metrics and evaluation logic for highlighted terms in PromptDoctor, supporting analysis and reporting of term highlighting performance.
"""

from typing import Dict, List, Set
from src.medical.medical_processor import MedicalTermProcessor
import re
import logging
from collections import Counter
from datetime import datetime
import os
import json

# Configure logging
logger = logging.getLogger(__name__)

class HighlightMetrics:
    def __init__(self):
        self.medical_processor = MedicalTermProcessor()
        
        # Track highlighted terms usage
        self.highlighted_terms_history = []
        self.terms_counter = Counter()
        self.prompt_counter = Counter()
        
        # Specific tracking for LIME terms in Task 3 Group B
        self.lime_term_usage = {term: 0 for term in self.LIME_HIGHLIGHTS}
        self.task3_group_b_prompts = []
        
        # Storage for analytics
        self.analytics_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'highlights')
        os.makedirs(self.analytics_dir, exist_ok=True)
        
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

    def calculate_coverage(self, task_number: int, prompt: str, group: str = None) -> Dict:
        """Calculate term coverage based on task number"""
        # Track this prompt for analytics
        self.track_prompt(prompt, task_number, group)
        
        if task_number in [1, 2]:
            # Get medical terms from both clinical note and prompt
            note_terms = self.get_medical_terms(self.CLINICAL_NOTES[task_number])
            prompt_terms = self.get_medical_terms(prompt)
            
            # Track these medical terms for analytics
            self.track_highlighted_terms(prompt_terms, task_number, group)
            
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
            
            # Track LIME terms for analytics
            self.track_highlighted_terms(matches, task_number, group)
            
            # For Task 3 Group B, track LIME term usage specifically
            if task_number == 3 and group == 'B':
                self.track_lime_terms_usage(prompt, matches)
            
            return {
                'highlight_type': 'lime',
                'matched_terms': list(matches),
                'total_terms': len(self.LIME_HIGHLIGHTS),
                'coverage_percentage': len(matches) / len(self.LIME_HIGHLIGHTS) * 100
            }
        
        # Default return for unknown task
        return {
            'highlight_type': 'unknown',
            'matched_terms': [],
            'total_terms': 0,
            'coverage_percentage': 0
        }
        
    def track_highlighted_terms(self, terms: Set[str], task_number: int, group: str = None) -> None:
        """
        Track highlighted terms for analytics
        
        Args:
            terms: Set of highlighted terms
            task_number: The task number these terms are associated with
            group: The user group (A or B)
        """
        if not terms:
            return
            
        # Add to history
        entry = {
            'terms': list(terms),
            'count': len(terms),
            'task': task_number,
            'group': group,
            'timestamp': datetime.now().isoformat(),
            'from_wiki_medical': sum(1 for term in terms if term in self.medical_processor.medical_terms)
        }
        self.highlighted_terms_history.append(entry)
        
        # Update counter
        self.terms_counter.update(terms)
        
        # Log this tracking event
        logger.debug(f"Tracked {len(terms)} highlighted terms for task {task_number}, group {group}")
        
        # Save analytics periodically (every 10 entries)
        if len(self.highlighted_terms_history) % 10 == 0:
            self.save_highlight_analytics()
    
    def track_prompt(self, prompt: str, task_number: int, group: str = None) -> None:
        """
        Track user prompts for analytics
        
        Args:
            prompt: The user prompt
            task_number: The task number this prompt is associated with
            group: The user group (A or B)
        """
        if not prompt:
            return
            
        # Extract key statistics
        term_count = len(self.get_medical_terms(prompt))
        word_count = len(prompt.split())
        
        # Add to counter with task-specific tracking
        self.prompt_counter.update([f"task_{task_number}_prompt"])
        if group:
            self.prompt_counter.update([f"task_{task_number}_group_{group}_prompt"])
        
        # Track this prompt
        entry = {
            'task': task_number,
            'group': group,
            'word_count': word_count,
            'term_count': term_count,
            'timestamp': datetime.now().isoformat(),
            'prompt_excerpt': prompt[:100] if len(prompt) > 100 else prompt
        }
        
        # Add task 3 group B prompt to special tracking
        if task_number == 3 and group == 'B':
            lime_coverage = self.calculate_lime_coverage(prompt)
            entry['lime_coverage'] = lime_coverage
            self.task3_group_b_prompts.append(entry)
        
        # Log this tracking event
        logger.debug(f"Tracked prompt with {term_count} medical terms for task {task_number}, group {group}")
        
        # Save prompt analytics
        self.save_prompt_analytics(entry)

    def track_lime_terms_usage(self, prompt: str, matched_terms: Set[str] = None) -> None:
        """
        Track LIME terms usage in Task 3 Group B prompts
        
        Args:
            prompt: The user prompt
            matched_terms: Pre-matched LIME terms (optional)
        """
        prompt_lower = prompt.lower()
        
        # Use pre-matched terms if provided, otherwise calculate
        if matched_terms is None:
            matched_terms = {term for term in self.LIME_HIGHLIGHTS if term in prompt_lower}
        
        # Update usage counter for each LIME term
        for term in matched_terms:
            if term in self.lime_term_usage:
                self.lime_term_usage[term] += 1
        
        # Save LIME term usage analytics
        self.save_lime_term_analytics()

    def calculate_lime_coverage(self, prompt: str) -> Dict:
        """
        Calculate LIME term coverage in a prompt
        
        Args:
            prompt: The user prompt to analyze
            
        Returns:
            Dictionary with LIME term coverage statistics
        """
        if not prompt:
            return {
                'coverage_percentage': 0,
                'matched_terms': [],
                'total_terms': len(self.LIME_HIGHLIGHTS)
            }
        
        prompt_lower = prompt.lower()
        matched_terms = [term for term in self.LIME_HIGHLIGHTS if term in prompt_lower]
        
        return {
            'coverage_percentage': len(matched_terms) / len(self.LIME_HIGHLIGHTS) * 100,
            'matched_terms': matched_terms,
            'total_terms': len(self.LIME_HIGHLIGHTS),
            'term_counts': {term: 1 if term in matched_terms else 0 for term in self.LIME_HIGHLIGHTS}
        }
    
    def get_highlight_statistics(self) -> Dict:
        """Get statistics about highlighted terms"""
        total_highlights = sum(entry['count'] for entry in self.highlighted_terms_history)
        
        # Calculate how many terms are from the gamino/wiki_medical_terms dataset
        wiki_medical_terms = sum(entry['from_wiki_medical'] for entry in self.highlighted_terms_history)
        
        # Get LIME term statistics for Task 3 Group B
        lime_stats = {
            'total_usage': sum(self.lime_term_usage.values()),
            'term_usage': dict(self.lime_term_usage),
            'most_used': sorted(self.lime_term_usage.items(), key=lambda x: x[1], reverse=True),
            'group_b_prompts_count': len(self.task3_group_b_prompts)
        }
        
        return {
            'total_highlights': total_highlights,
            'unique_terms': len(self.terms_counter),
            'most_common_terms': self.terms_counter.most_common(10),
            'wiki_medical_terms': wiki_medical_terms,
            'wiki_medical_percentage': (wiki_medical_terms / total_highlights * 100) if total_highlights else 0,
            'highlight_sessions': len(self.highlighted_terms_history),
            'prompts_by_task': dict(self.prompt_counter),
            'lime_term_stats': lime_stats
        }
    
    def save_highlight_analytics(self) -> None:
        """Save highlight analytics to file"""
        try:
            # Create analytics file path
            filepath = os.path.join(self.analytics_dir, 'highlight_analytics.json')
            
            # Get current statistics
            stats = self.get_highlight_statistics()
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump({
                    'statistics': stats,
                    'last_updated': datetime.now().isoformat(),
                    'history': self.highlighted_terms_history[-50:]  # Save last 50 entries to avoid file growth
                }, f, indent=2)
                
            logger.info(f"Saved highlight analytics to {filepath}")
        except Exception as e:
            logger.error(f"Error saving highlight analytics: {str(e)}")
    
    def save_prompt_analytics(self, entry: Dict) -> None:
        """Save prompt analytics to file"""
        try:
            # Create analytics file path
            filepath = os.path.join(self.analytics_dir, f'prompt_analytics_task_{entry["task"]}.jsonl')
            
            # Append entry to file
            with open(filepath, 'a') as f:
                f.write(json.dumps(entry) + '\n')
                
            logger.debug(f"Saved prompt analytics entry for task {entry['task']}")
        except Exception as e:
            logger.error(f"Error saving prompt analytics: {str(e)}")
    
    def save_lime_term_analytics(self) -> None:
        """Save LIME term usage analytics for Task 3 Group B"""
        try:
            # Create analytics file path
            filepath = os.path.join(self.analytics_dir, 'lime_term_usage.json')
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump({
                    'term_usage': dict(self.lime_term_usage),
                    'prompts': self.task3_group_b_prompts[-20:],  # Save last 20 prompts
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
                
            logger.info(f"Saved LIME term analytics to {filepath}")
        except Exception as e:
            logger.error(f"Error saving LIME term analytics: {str(e)}")

    def get_wiki_medical_terms_coverage(self, prompt: str) -> Dict:
        """
        Calculate what percentage of terms in the prompt are from the gamino/wiki_medical_terms dataset
        
        Args:
            prompt: The user prompt to analyze
            
        Returns:
            Dictionary with coverage statistics
        """
        if not prompt:
            return {
                'coverage_percentage': 0,
                'matched_terms': [],
                'total_terms': 0
            }
            
        # Get all terms in the prompt
        all_terms = set(prompt.lower().split())
        
        # Find intersection with medical terms from the wiki dataset
        wiki_terms = {term for term in all_terms if term in self.medical_processor.medical_terms}
        
        # Calculate coverage
        coverage = len(wiki_terms) / len(all_terms) * 100 if all_terms else 0
        
        return {
            'coverage_percentage': coverage,
            'matched_terms': list(wiki_terms),
            'total_terms': len(all_terms),
            'medical_term_percentage': len(wiki_terms) / len(self.medical_processor.medical_terms) * 100 if self.medical_processor.medical_terms else 0
        }
