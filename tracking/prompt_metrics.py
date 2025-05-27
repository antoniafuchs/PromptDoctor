from typing import List, Set
from dataclasses import dataclass
from datetime import datetime

try:
    from Levenshtein import distance as levenshtein_distance
except ImportError:
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Simple Levenshtein distance implementation as fallback"""
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

@dataclass
class PromptMetricsData:
    prompt_count: int
    first_prompt: str
    last_prompt: str
    levenshtein_distance: float
    word_count: int
    timestamp: datetime
    task_id: int = None
    user_id: str = None
    group: str = None
    edit_distance: float = 0.0
    diff_type: str = None
    medical_term_count: int = 0
    highlighted_terms: List[str] = None

class PromptMetrics:
    def calculate_normalized_levenshtein(self, s1: str, s2: str) -> float:
        """Calculate normalized Levenshtein distance between two strings"""
        if not s1 or not s2:
            return 0.0
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 0.0
        return levenshtein_distance(s1, s2) / max_len

    def count_words(self, text: str) -> int:
        """Count words in a text string"""
        return len(text.split())

    def analyze_prompts(self, prompts: List[str], task_id: int = None, user_id: str = None, group: str = None) -> PromptMetricsData:
        """Analyze a list of prompts and return metrics"""
        if not prompts:
            return PromptMetricsData(0, "", "", 0.0, 0, datetime.now(), task_id, user_id, group)

        first_prompt = prompts[0]
        last_prompt = prompts[-1]
        
        # Calculate additional metrics for enhanced tracking
        medical_terms = self._extract_medical_terms(last_prompt)
        
        return PromptMetricsData(
            prompt_count=len(prompts),
            first_prompt=first_prompt,
            last_prompt=last_prompt,
            levenshtein_distance=self.calculate_normalized_levenshtein(first_prompt, last_prompt),
            word_count=self.count_words(last_prompt),
            timestamp=datetime.now(),
            task_id=task_id,
            user_id=user_id,
            group=group,
            edit_distance=self.calculate_normalized_levenshtein(first_prompt, last_prompt),
            diff_type=self._determine_diff_type(first_prompt, last_prompt),
            medical_term_count=len(medical_terms),
            highlighted_terms=list(medical_terms)
        )

    def _extract_medical_terms(self, text: str) -> Set[str]:
        """Extract medical terms from text using the medical processor"""
        from utils.medical_processor import MedicalTermProcessor
        processor = MedicalTermProcessor()
        words = text.lower().split()
        return {word for word in words if word in processor.medical_terms}

    def _determine_diff_type(self, first: str, last: str) -> str:
        """Determine the type of difference between original and modified text"""
        if first == last:
            return "unchanged"
            
        # Calculate word counts
        first_words = set(first.lower().split())
        last_words = set(last.lower().split())
        
        added = last_words - first_words
        removed = first_words - last_words
        
        if added and removed:
            return "substitution"
        elif added:
            return "addition"
        elif removed:
            return "deletion"
        else:
            return "reformulation"  # Same words but different structure
