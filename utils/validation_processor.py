import pandas as pd
import os
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ValidationProcessor:
    """Process and analyze validation data from multiple sources."""
    
    def __init__(self, data_dir: str):
        """Initialize with the data directory path."""
        self.data_dir = data_dir
        
    def load_validation_data(self) -> pd.DataFrame:
        """Load validation data from validation.csv"""
        validation_path = os.path.join(self.data_dir, 'validation.csv')
        if not os.path.exists(validation_path):
            logger.warning(f"Validation file not found: {validation_path}")
            return pd.DataFrame()
            
        try:
            df = pd.read_csv(validation_path, sep=';')
            logger.info(f"Loaded {len(df)} validation records")
            return df
        except Exception as e:
            logger.error(f"Error loading validation data: {str(e)}")
            return pd.DataFrame()
    
    def get_validation_metrics(self) -> Dict:
        """Calculate key validation metrics"""
        df = self.load_validation_data()
        if df.empty:
            return {
                "total_validations": 0,
                "accept_rate": 0,
                "edit_rate": 0,
                "avg_medical_terms": 0
            }
        
        metrics = {
            "total_validations": len(df),
            "unique_users": df['user_id'].nunique(),
            "unique_tasks": df['task_id'].nunique()
        }
        
        # Calculate action type distribution
        if 'action_type' in df.columns:
            action_counts = df['action_type'].value_counts(normalize=True) * 100
            for action, pct in action_counts.items():
                metrics[f"pct_{action.lower()}"] = round(pct, 1)
            
            # Calculate acceptance vs edit rates
            accepts = df[df['action_type'] == 'ACCEPT_CLICK']
            metrics["accept_count"] = len(accepts)
            metrics["accept_rate"] = round(len(accepts) / len(df) * 100, 1) if len(df) > 0 else 0
        
        # Medical term metrics
        if 'medical_term_count' in df.columns:
            df['medical_term_count'] = pd.to_numeric(df['medical_term_count'], errors='coerce')
            metrics["avg_medical_terms"] = round(df['medical_term_count'].mean(), 2)
            metrics["max_medical_terms"] = int(df['medical_term_count'].max())
        
        # Edit distance metrics
        if 'edit_distance' in df.columns:
            df['edit_distance'] = pd.to_numeric(df['edit_distance'], errors='coerce')
            metrics["avg_edit_distance"] = round(df['edit_distance'].mean(), 3)
        
        # Group metrics
        if 'group' in df.columns:
            for group in df['group'].unique():
                group_df = df[df['group'] == group]
                metrics[f"group_{group}_count"] = len(group_df)
                
                if 'medical_term_count' in group_df.columns:
                    metrics[f"group_{group}_avg_terms"] = round(
                        group_df['medical_term_count'].mean(), 2)
                
                if 'edit_distance' in group_df.columns:
                    metrics[f"group_{group}_avg_edit"] = round(
                        group_df['edit_distance'].mean(), 3)
        
        return metrics
    
    def get_validation_by_task(self) -> pd.DataFrame:
        """Get validation metrics grouped by task"""
        df = self.load_validation_data()
        if df.empty or 'task_id' not in df.columns:
            return pd.DataFrame()
        
        # Ensure numeric columns are properly typed
        for col in ['medical_term_count', 'edit_distance']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Group by task and calculate metrics
        task_metrics = df.groupby('task_id').agg({
            'user_id': 'nunique',
            'action_type': 'count',
            'medical_term_count': 'mean',
            'edit_distance': 'mean'
        }).reset_index()
        
        # Rename columns
        task_metrics.columns = [
            'Task ID', 'Unique Users', 'Validation Events', 
            'Avg Medical Terms', 'Avg Edit Distance'
        ]
        
        # Round numeric columns
        task_metrics['Avg Medical Terms'] = task_metrics['Avg Medical Terms'].round(2)
        task_metrics['Avg Edit Distance'] = task_metrics['Avg Edit Distance'].round(3)
        
        return task_metrics
    
    def get_top_medical_terms(self, limit: int = 20) -> pd.DataFrame:
        """Get the most frequently highlighted medical terms"""
        df = self.load_validation_data()
        if df.empty or 'highlighted_terms' not in df.columns:
            return pd.DataFrame()
        
        # Extract all terms from the highlighted_terms column
        all_terms = []
        for terms_str in df['highlighted_terms'].dropna():
            if isinstance(terms_str, str) and terms_str.strip():
                terms = [term.strip() for term in terms_str.split(',')]
                all_terms.extend([term for term in terms if term])
        
        # Count term frequencies
        term_counts = {}
        for term in all_terms:
            term_counts[term] = term_counts.get(term, 0) + 1
        
        # Convert to DataFrame and sort
        terms_df = pd.DataFrame({
            'Term': list(term_counts.keys()),
            'Count': list(term_counts.values())
        })
        
        return terms_df.sort_values('Count', ascending=False).head(limit)
    
    def get_diff_type_distribution(self) -> pd.DataFrame:
        """Get distribution of diff types (how prompts were modified)"""
        df = self.load_validation_data()
        if df.empty or 'diff_type' not in df.columns:
            return pd.DataFrame()
        
        # Count by diff_type
        diff_counts = df['diff_type'].value_counts().reset_index()
        diff_counts.columns = ['Diff Type', 'Count']
        
        # Calculate percentages
        diff_counts['Percentage'] = (diff_counts['Count'] / diff_counts['Count'].sum() * 100).round(1)
        
        return diff_counts
    
    def merge_with_interactions(self) -> pd.DataFrame:
        """Merge validation data with interaction data for richer analysis"""
        validation_df = self.load_validation_data()
        interactions_path = os.path.join(self.data_dir, 'interactions.csv')
        
        if validation_df.empty or not os.path.exists(interactions_path):
            return validation_df
        
        try:
            interactions_df = pd.read_csv(interactions_path, sep=';')
            
            # Filter to relevant interactions
            prompt_interactions = interactions_df[
                interactions_df['action_type'].isin(['CHAT', 'VALIDATION_VIEW', 'ACCEPT_CLICK'])
            ]
            
            # Join on message_id if available
            if 'message_id' in validation_df.columns and 'message_id' in prompt_interactions.columns:
                merged_df = pd.merge(
                    validation_df, 
                    prompt_interactions,
                    on=['user_id', 'message_id'],
                    how='left',
                    suffixes=('', '_interaction')
                )
                return merged_df
                
        except Exception as e:
            logger.error(f"Error merging with interactions: {str(e)}")
        
        return validation_df
