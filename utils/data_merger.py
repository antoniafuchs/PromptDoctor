import pandas as pd
import os
from datetime import datetime
from typing import Dict, Any
import glob

class DataMerger:
    def __init__(self, base_path: str = "."):
        self.base_path = base_path
        self.survey_path = os.path.join(base_path, "survey_data")
        self.logs_path = os.path.join(base_path, "user_logs")
        self.output_path = os.path.join(base_path, "merged_data")
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories"""
        os.makedirs(self.output_path, exist_ok=True)

    def convert_logs_to_csv(self):
        """Convert log files to CSV format"""
        log_data = []
        
        for log_file in glob.glob(os.path.join(self.logs_path, "*.log")):
            user_id = os.path.splitext(os.path.basename(log_file))[0]
            current_interaction = None
            
            with open(log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if "===" in line:  # New interaction block
                        if current_interaction:  # Save previous interaction if exists
                            log_data.append(current_interaction)
                        current_interaction = {"user_id": user_id}
                    elif ":" in line and "===" not in line:
                        if current_interaction is not None:  # Only process if in an interaction
                            try:
                                key, value = line.split(":", 1)
                                current_interaction[key.strip()] = value.strip()
                            except ValueError:
                                continue  # Skip malformed lines
                    elif line == "="*50:  # End of interaction block
                        if current_interaction:
                            log_data.append(current_interaction)
                            current_interaction = None
                            
                # Add final interaction if exists
                if current_interaction:
                    log_data.append(current_interaction)

        # Convert to DataFrame and save
        if log_data:
            df = pd.DataFrame(log_data)
            output_file = os.path.join(self.output_path, "interaction_logs.csv")
            df.to_csv(output_file, index=False)
            return output_file
        return None

    def merge_all_data(self):
        """Merge all data sources into one CSV file"""
        try:
            # Read tasks directly instead of task_surveys.csv
            tasks = pd.read_csv(os.path.join(self.base_path, 'data', 'tasks.csv'), sep=';')
            
            # Read users data
            users = pd.read_csv(os.path.join(self.base_path, 'data', 'users.csv'), sep=';')
            
            # Read other data files as needed
            interactions = pd.read_csv(os.path.join(self.base_path, 'data', 'interactions.csv'), sep=';')
            
            # Merge based on user_id and task_id
            merged_df = pd.merge(users, tasks, on='user_id', how='outer')
            
            # Optionally merge with interactions
            # merged_df = pd.merge(merged_df, interactions, on=['user_id', 'task_id'], how='outer')
            
            # Save merged data with semicolon delimiter
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(self.base_path, 'merged_data', f'complete_study_data_{timestamp}.csv')
            merged_df.to_csv(output_file, sep=';', index=False)
            
            return output_file
        except Exception as e:
            print(f"Error merging data: {str(e)}")
            return None

    def generate_summary_stats(self, file_path: str) -> dict:
        """Generate summary statistics from merged data"""
        try:
            df = pd.read_csv(file_path, sep=';')
            
            # Initialize stats dictionary with default values
            stats = {
                "total_users": 0,
                "avg_satisfaction": 0.0,
                "avg_tasks_completed": 0.0,
                "avg_duration": 0.0
            }
            
            # Get basic stats that don't depend on specific columns
            stats["total_users"] = len(df['user_id'].unique()) if 'user_id' in df.columns else 0
            
            # Safely get column statistics
            if 'satisfaction' in df.columns:
                stats["avg_satisfaction"] = float(df["satisfaction"].mean())
            
            if 'tasks_completed' in df.columns:
                stats["avg_tasks_completed"] = float(df["tasks_completed"].mean())
            
            if 'survey_duration_seconds' in df.columns:
                stats["avg_duration"] = float(df["survey_duration_seconds"].mean())
            
            return stats
            
        except Exception as e:
            print(f"Error generating stats: {str(e)}")
            return {
                "total_users": 0,
                "avg_satisfaction": 0.0,
                "avg_tasks_completed": 0.0,
                "avg_duration": 0.0
            }
