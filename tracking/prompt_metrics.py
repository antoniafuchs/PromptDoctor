from typing import List
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

class PromptMetrics:
    def calculate_normalized_levenshtein(self, s1: str, s2: str) -> float:
        """Calculate normalized Levenshtein distance between two strings"""
        if not s1 or not s2:
            return 0.0
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 0.0
        return distance(s1, s2) / max_len

    def count_words(self, text: str) -> int:
        """Count words in a text string"""
        return len(text.split())

    def analyze_prompts(self, prompts: List[str]) -> PromptMetricsData:
        """Analyze a list of prompts and return metrics"""
        if not prompts:
            return PromptMetricsData(0, "", "", 0.0, 0, datetime.now())

        first_prompt = prompts[0]
        last_prompt = prompts[-1]
        
        return PromptMetricsData(
            prompt_count=len(prompts),
            first_prompt=first_prompt,
            last_prompt=last_prompt,
            levenshtein_distance=self.calculate_normalized_levenshtein(first_prompt, last_prompt),
            word_count=self.count_words(last_prompt),
            timestamp=datetime.now()
        )
