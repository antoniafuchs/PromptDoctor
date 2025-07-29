"""
feedback_collector.py
This file collects user feedback in PromptDoctor, providing utilities for gathering and storing feedback data.
"""

import os
import pandas as pd
import json
import datetime
import logging
from typing import Dict, List, Optional, Any

# Configure logging
logger = logging.getLogger('feedback_collector')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class FeedbackCollector:
    """Utility class for collecting and analyzing feedback data"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.feedback_dir = os.path.join(self.base_dir, 'feedback')
        self.merged_dir = os.path.join(self.base_dir, 'merged_data')
        
        # Ensure all directories exist
        for directory in [self.data_dir, self.feedback_dir, self.merged_dir]:
            os.makedirs(directory, exist_ok=True)
            
    def collect_all_feedback(self) -> pd.DataFrame:
        """Collect feedback from all possible sources into a single DataFrame"""
        all_feedback = []
        
        # 1. Try to get feedback from feedback.csv
        feedback_csv = os.path.join(self.data_dir, 'feedback.csv')
        if os.path.exists(feedback_csv):
            try:
                df = pd.read_csv(feedback_csv, sep=';')
                logger.info(f"Loaded {len(df)} feedback entries from feedback.csv")
                all_feedback.append(df)
            except Exception as e:
                logger.error(f"Error loading feedback.csv: {str(e)}")
        
        # 2. Try to get feedback from interactions.csv (action_type='FEEDBACK')
        interactions_csv = os.path.join(self.data_dir, 'interactions.csv')
        if os.path.exists(interactions_csv):
            try:
                df = pd.read_csv(interactions_csv, sep=';')
                
                # Check for both action_type and action columns for flexibility
                action_col = 'action_type' if 'action_type' in df.columns else 'action'
                
                if action_col in df.columns:
                    feedback_df = df[df[action_col] == 'FEEDBACK'].copy()
                    if not feedback_df.empty:
                        # Map columns to consistent names
                        if 'feedback' in feedback_df.columns and 'feedback_value' not in feedback_df.columns:
                            feedback_df['feedback_value'] = feedback_df['feedback']
                        logger.info(f"Loaded {len(feedback_df)} feedback entries from interactions.csv")
                        all_feedback.append(feedback_df)
            except Exception as e:
                logger.error(f"Error loading interactions.csv: {str(e)}")
        
        # 3. Try to get feedback from individual JSON files in feedback directory
        json_files = []
        for root, _, files in os.walk(self.feedback_dir):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
        
        if json_files:
            json_data = []
            for file_path in json_files:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        json_data.append(data)
                except Exception as e:
                    logger.error(f"Error reading JSON file {file_path}: {str(e)}")
            
            if json_data:
                try:
                    json_df = pd.DataFrame(json_data)
                    logger.info(f"Loaded {len(json_df)} feedback entries from JSON files")
                    all_feedback.append(json_df)
                except Exception as e:
                    logger.error(f"Error converting JSON data to DataFrame: {str(e)}")
        
        # 4. Check for feedback in chat history
        chat_history_dir = os.path.join(self.data_dir, 'chat_history')
        if os.path.exists(chat_history_dir):
            try:
                # Find all chat history JSON files
                chat_files = [
                    os.path.join(chat_history_dir, f)
                    for f in os.listdir(chat_history_dir)
                    if f.endswith('.json')
                ]
                
                chat_feedback = []
                for chat_file in chat_files:
                    try:
                        with open(chat_file, 'r') as f:
                            chat_data = json.load(f)
                            if 'messages' in chat_data:
                                for msg in chat_data['messages']:
                                    # Extract feedback if available
                                    if 'feedback' in msg and msg['feedback'] is not None:
                                        feedback_entry = {
                                            'user_id': chat_data.get('user_id', ''),
                                            'task_id': chat_data.get('task_id', ''),
                                            'message_id': msg.get('message_id', ''),
                                            'feedback_value': msg.get('feedback', ''),
                                            'timestamp': msg.get('timestamp', ''),
                                            'response_message_id': msg.get('message_id', ''),
                                            'content': msg.get('content', '')[:100]  # Truncate content
                                        }
                                        chat_feedback.append(feedback_entry)
                    except Exception as e:
                        logger.error(f"Error processing chat file {chat_file}: {str(e)}")
                
                if chat_feedback:
                    chat_df = pd.DataFrame(chat_feedback)
                    logger.info(f"Loaded {len(chat_df)} feedback entries from chat history files")
                    all_feedback.append(chat_df)
            except Exception as e:
                logger.error(f"Error processing chat history directory: {str(e)}")
        
        # Merge all sources if we have any
        if not all_feedback:
            logger.warning("No feedback data found in any source")
            return pd.DataFrame()
        
        # Create a merged DataFrame
        if len(all_feedback) == 1:
            return all_feedback[0]
        
        # Attempt to merge DataFrames with common columns
        try:
            # Identify common columns across all DataFrames
            common_columns = set.intersection(*[set(df.columns) for df in all_feedback])
            if not common_columns:
                logger.warning("No common columns across feedback sources for clean merge")
                # Just concatenate and use all columns
                return pd.concat(all_feedback, ignore_index=True, sort=False)
            
            # Use user_id, message_id as merge keys if available, otherwise just concatenate
            if 'user_id' in common_columns and 'message_id' in common_columns:
                # Start with first DataFrame
                merged_df = all_feedback[0]
                
                # Merge with remaining DataFrames
                for df in all_feedback[1:]:
                    merged_df = pd.merge(
                        merged_df, df, 
                        on=['user_id', 'message_id'], 
                        how='outer',
                        suffixes=('', '_additional')
                    )
                
                return merged_df
            else:
                # Just concatenate if we don't have good merge keys
                return pd.concat(all_feedback, ignore_index=True, sort=False)
        except Exception as e:
            logger.error(f"Error merging feedback data: {str(e)}")
            # Return the first DataFrame as fallback
            return all_feedback[0]
    
    def export_feedback_report(self, format='csv'):
        """Export feedback data to a file for analysis"""
        feedback_df = self.collect_all_feedback()
        
        if feedback_df.empty:
            logger.warning("No feedback data to export")
            return None
        
        # Generate timestamp for filename
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Determine output path based on format
        if format.lower() == 'csv':
            output_path = os.path.join(self.merged_dir, f"feedback_export_{timestamp}.csv")
            feedback_df.to_csv(output_path, index=False, sep=';')
        elif format.lower() == 'json':
            output_path = os.path.join(self.merged_dir, f"feedback_export_{timestamp}.json")
            feedback_df.to_json(output_path, orient='records', indent=2)
        elif format.lower() == 'excel':
            output_path = os.path.join(self.merged_dir, f"feedback_export_{timestamp}.xlsx")
            feedback_df.to_excel(output_path, index=False)
        else:
            logger.error(f"Unsupported export format: {format}")
            return None
        
        logger.info(f"Exported {len(feedback_df)} feedback records to {output_path}")
        return output_path
    
    def generate_feedback_summary(self):
        """Generate a summary of feedback data for analysis"""
        feedback_df = self.collect_all_feedback()
        
        if feedback_df.empty:
            logger.warning("No feedback data to summarize")
            return {"error": "No feedback data available"}
        
        # Determine which column contains the feedback value
        feedback_col = None
        for col in ['feedback_value', 'feedback']:
            if col in feedback_df.columns:
                feedback_col = col
                break
        
        if not feedback_col:
            logger.warning("No feedback value column found in data")
            return {"error": "No feedback value column found"}
        
        # Make sure feedback values are numeric
        try:
            feedback_df[feedback_col] = pd.to_numeric(feedback_df[feedback_col], errors='coerce')
        except Exception as e:
            logger.error(f"Error converting feedback to numeric: {str(e)}")
            return {"error": f"Error processing feedback values: {str(e)}"}
        
        # Calculate summary statistics
        summary = {
            "total_entries": len(feedback_df),
            "positive_feedback": int(sum(feedback_df[feedback_col] > 0)),
            "negative_feedback": int(sum(feedback_df[feedback_col] < 0)),
            "neutral_feedback": int(sum(feedback_df[feedback_col] == 0)),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Calculate percentages
        if summary["total_entries"] > 0:
            summary["positive_percentage"] = round(summary["positive_feedback"] / summary["total_entries"] * 100, 1)
            summary["negative_percentage"] = round(summary["negative_feedback"] / summary["total_entries"] * 100, 1)
            summary["neutral_percentage"] = round(summary["neutral_feedback"] / summary["total_entries"] * 100, 1)
        
        # Add feedback by task if available
        if 'task_id' in feedback_df.columns:
            task_feedback = {}
            
            # Group by task_id and calculate stats
            task_stats = feedback_df.groupby('task_id')[feedback_col].agg(['count', 'mean']).reset_index()
            for _, row in task_stats.iterrows():
                task_id = row['task_id']
                task_feedback[str(task_id)] = {
                    "count": int(row['count']),
                    "average_rating": round(float(row['mean']), 2)
                }
            
            summary["feedback_by_task"] = task_feedback
        
        # Add feedback by user if available
        if 'user_id' in feedback_df.columns:
            user_feedback = {}
            
            # Group by user_id and calculate stats
            user_stats = feedback_df.groupby('user_id')[feedback_col].agg(['count', 'mean']).reset_index()
            for _, row in user_stats.iterrows():
                user_id = row['user_id']
                user_feedback[str(user_id)] = {
                    "count": int(row['count']),
                    "average_rating": round(float(row['mean']), 2)
                }
            
            summary["feedback_by_user"] = user_feedback
        
        return summary

# Simple command-line interface if run directly
if __name__ == "__main__":
    collector = FeedbackCollector()
    
    print("Feedback Data Summary:")
    summary = collector.generate_feedback_summary()
    
    if "error" in summary:
        print(f"Error: {summary['error']}")
    else:
        print(f"Total feedback entries: {summary['total_entries']}")
        print(f"Positive feedback: {summary['positive_feedback']} ({summary['positive_percentage']}%)")
        print(f"Negative feedback: {summary['negative_feedback']} ({summary['negative_percentage']}%)")
        print(f"Neutral feedback: {summary['neutral_feedback']} ({summary['neutral_percentage']}%)")
        
        if "feedback_by_task" in summary:
            print("\nFeedback by Task:")
            for task_id, stats in summary["feedback_by_task"].items():
                print(f"  Task {task_id}: {stats['count']} entries, avg rating: {stats['average_rating']}")
    
    # Export data
    print("\nExporting feedback data...")
    export_path = collector.export_feedback_report()
    if export_path:
        print(f"Data exported to: {export_path}")
