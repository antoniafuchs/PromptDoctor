from typing import List, Set
from dataclasses import dataclass, field
from datetime import datetime
import logging
import re
import Levenshtein
from .highlight_metrics import HighlightMetrics

# Configure logging
logger = logging.getLogger(__name__)

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
    highlighted_terms: List[str] = field(default_factory=list)
    coverage_percentage: float = 0.0
    highlight_type: str = None

class PromptMetrics:
    """Calculate and track metrics for user prompts"""
    
    def __init__(self):
        self.highlight_metrics = HighlightMetrics()
    
    def calculate_metrics(self, prompts: List[str], task_id: int = None, 
                         user_id: str = None, group: str = None) -> PromptMetricsData:
        """Calculate metrics for a list of prompts"""
        try:
            if not prompts:
                logger.warning("Empty prompts list provided for metrics calculation")
                return PromptMetricsData(
                    prompt_count=0,
                    first_prompt="",
                    last_prompt="",
                    levenshtein_distance=0,
                    word_count=0,
                    timestamp=datetime.now(),
                    task_id=task_id,
                    user_id=user_id,
                    group=group
                )
                
            # Basic metrics
            prompt_count = len(prompts)
            first_prompt = prompts[0]
            last_prompt = prompts[-1]
            
            # Calculate Levenshtein distance between first and last prompts
            if prompt_count > 1:
                lev_distance = Levenshtein.distance(first_prompt, last_prompt)
                # Normalize by the length of the longer string
                max_len = max(len(first_prompt), len(last_prompt))
                lev_distance_normalized = lev_distance / max_len if max_len > 0 else 0
            else:
                lev_distance_normalized = 0
                
            # Calculate word count of the last prompt
            word_count = len(re.findall(r'\b\w+\b', last_prompt))
            
            # Calculate edit distance (relative change in length)
            if prompt_count > 1 and len(first_prompt) > 0:
                length_change = abs(len(last_prompt) - len(first_prompt))
                edit_distance = length_change / len(first_prompt)
                
                # Determine diff type
                if len(last_prompt) > len(first_prompt):
                    diff_type = "expansion"
                elif len(last_prompt) < len(first_prompt):
                    diff_type = "reduction"
                else:
                    diff_type = "modification"
            else:
                edit_distance = 0
                diff_type = "initial"
                
            # Calculate highlighted terms coverage if task_id is provided
            highlight_data = {}
            if task_id is not None:
                highlight_data = self.highlight_metrics.calculate_coverage(task_id, last_prompt)
                
            metrics = PromptMetricsData(
                prompt_count=prompt_count,
                first_prompt=first_prompt,
                last_prompt=last_prompt,
                levenshtein_distance=lev_distance_normalized,
                word_count=word_count,
                timestamp=datetime.now(),
                task_id=task_id,
                user_id=user_id,
                group=group,
                edit_distance=edit_distance,
                diff_type=diff_type,
                medical_term_count=highlight_data.get('total_terms', 0),
                highlighted_terms=highlight_data.get('matched_terms', []),
                coverage_percentage=highlight_data.get('coverage_percentage', 0),
                highlight_type=highlight_data.get('highlight_type', None)
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating prompt metrics: {str(e)}")
            # Return basic metrics data with timestamp
            return PromptMetricsData(
                prompt_count=len(prompts) if prompts else 0,
                first_prompt=prompts[0] if prompts else "",
                last_prompt=prompts[-1] if prompts else "",
                levenshtein_distance=0,
                word_count=0,
                timestamp=datetime.now(),
                task_id=task_id,
                user_id=user_id,
                group=group
            )
