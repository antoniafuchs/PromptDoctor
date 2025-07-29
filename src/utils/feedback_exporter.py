"""
feedback_exporter.py
This file exports user feedback data from the PromptDoctor application, providing utilities for formatting and saving feedback for analysis.
"""

import os
import pandas as pd
import json
import datetime
import logging
from typing import Dict, List, Optional, Any

# Configure logging
logger = logging.getLogger('feedback_exporter')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class FeedbackExporter:
    """Utility class for exporting feedback data from all sources"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.feedback_dir = os.path.join(self.base_dir, 'feedback')
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        self.export_dir = os.path.join(self.base_dir, 'exports')
        
        # Ensure all directories exist
        for directory in [self.data_dir, self.feedback_dir, self.logs_dir, self.export_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def collect_feedback_from_interactions(self) -> pd.DataFrame:
        """Collect feedback data from interactions.csv"""
        interactions_file = os.path.join(self.data_dir, 'interactions.csv')
        if not os.path.exists(interactions_file):
            logger.warning(f"interactions.csv not found at {interactions_file}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(interactions_file, sep=';')
            # Filter to only include feedback entries
            feedback_df = df[df['action_type'] == 'FEEDBACK']
            
            # Check if there's any feedback data
            if feedback_df.empty:
                logger.info("No feedback entries found in interactions.csv")
                return pd.DataFrame()
            
            logger.info(f"Found {len(feedback_df)} feedback entries in interactions.csv")
            return feedback_df
        except Exception as e:
            logger.error(f"Error reading interactions.csv: {str(e)}")
            return pd.DataFrame()
    
    def collect_feedback_from_chat_history(self) -> pd.DataFrame:
        """Collect feedback data from chat history JSON files"""
        chat_history_dir = os.path.join(self.data_dir, 'chat_history')
        if not os.path.exists(chat_history_dir):
            logger.warning(f"Chat history directory not found at {chat_history_dir}")
            return pd.DataFrame()
        
        feedback_data = []
        
        try:
            # List all JSON files in the chat history directory
            json_files = [f for f in os.listdir(chat_history_dir) if f.endswith('.json')]
            
            for file_name in json_files:
                file_path = os.path.join(chat_history_dir, file_name)
                try:
                    with open(file_path, 'r') as f:
                        chat_data = json.load(f)
                    
                    user_id = chat_data.get('user_id', '')
                    task_id = chat_data.get('task_id', '')
                    
                    # Look for feedback in messages
                    for msg in chat_data.get('messages', []):
                        if msg.get('role') == 'assistant' and 'feedback' in msg:
                            feedback_data.append({
                                'user_id': user_id,
                                'task_id': task_id,
                                'message_id': msg.get('message_id', ''),
                                'feedback': msg.get('feedback'),
                                'timestamp': msg.get('timestamp', ''),
                                'content': msg.get('content', '')[:100] + '...' if len(msg.get('content', '')) > 100 else msg.get('content', '')
                            })
                except Exception as e:
                    logger.error(f"Error processing chat history file {file_name}: {str(e)}")
            
            # Convert to DataFrame
            if feedback_data:
                logger.info(f"Found {len(feedback_data)} feedback entries in chat history files")
                return pd.DataFrame(feedback_data)
            else:
                logger.info("No feedback entries found in chat history files")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error processing chat history directory: {str(e)}")
            return pd.DataFrame()
    
    def collect_feedback_from_feedback_csv(self) -> pd.DataFrame:
        """Collect feedback data from feedback.csv if it exists"""
        feedback_file = os.path.join(self.data_dir, 'feedback.csv')
        if not os.path.exists(feedback_file):
            logger.warning(f"feedback.csv not found at {feedback_file}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(feedback_file, sep=';')
            if df.empty:
                logger.info("No entries found in feedback.csv")
                return pd.DataFrame()
            
            logger.info(f"Found {len(df)} feedback entries in feedback.csv")
            return df
        except Exception as e:
            logger.error(f"Error reading feedback.csv: {str(e)}")
            return pd.DataFrame()
    
    def collect_all_feedback(self) -> pd.DataFrame:
        """Collect feedback from all sources and merge into a single DataFrame"""
        feedback_dfs = []
        
        # Collect from each source
        interactions_df = self.collect_feedback_from_interactions()
        if not interactions_df.empty:
            feedback_dfs.append(interactions_df)
        
        chat_history_df = self.collect_feedback_from_chat_history()
        if not chat_history_df.empty:
            feedback_dfs.append(chat_history_df)
        
        feedback_csv_df = self.collect_feedback_from_feedback_csv()
        if not feedback_csv_df.empty:
            feedback_dfs.append(feedback_csv_df)
        
        # If no feedback found in any source
        if not feedback_dfs:
            logger.warning("No feedback found in any source")
            return pd.DataFrame()
        
        # Merge all DataFrames
        if len(feedback_dfs) == 1:
            return feedback_dfs[0]
        
        # Try to merge by common columns, but just concatenate if needed
        try:
            # Identify common columns for merging
            common_cols = set.intersection(*[set(df.columns) for df in feedback_dfs])
            
            # If we have user_id and message_id, use them as merge keys
            if 'user_id' in common_cols and 'message_id' in common_cols:
                merged_df = feedback_dfs[0]
                for df in feedback_dfs[1:]:
                    merged_df = pd.merge(
                        merged_df, df,
                        on=['user_id', 'message_id'],
                        how='outer',
                        suffixes=('', '_additional')
                    )
                
                # Clean up by removing duplicate columns
                cols_to_keep = [col for col in merged_df.columns if not col.endswith('_additional')]
                merged_df = merged_df[cols_to_keep]
                
                logger.info(f"Successfully merged {len(feedback_dfs)} feedback sources using common columns")
                return merged_df
            else:
                # Just concatenate if we don't have good merge keys
                logger.info(f"Concatenating {len(feedback_dfs)} feedback sources")
                return pd.concat(feedback_dfs, ignore_index=True)
        except Exception as e:
            logger.error(f"Error merging feedback data: {str(e)}")
            # Fall back to concatenation
            logger.info(f"Falling back to concatenation for {len(feedback_dfs)} feedback sources")
            return pd.concat(feedback_dfs, ignore_index=True)
    
    def export_feedback(self, format='csv') -> str:
        """Export all feedback to a file"""
        # Collect all feedback
        df = self.collect_all_feedback()
        
        if df.empty:
            logger.warning("No feedback data to export")
            return None
        
        # Create timestamp for filename
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export based on format
        if format.lower() == 'csv':
            output_path = os.path.join(self.export_dir, f"feedback_export_{timestamp}.csv")
            df.to_csv(output_path, index=False, sep=';')
        elif format.lower() == 'json':
            output_path = os.path.join(self.export_dir, f"feedback_export_{timestamp}.json")
            df.to_json(output_path, orient='records', indent=2)
        elif format.lower() == 'excel':
            output_path = os.path.join(self.export_dir, f"feedback_export_{timestamp}.xlsx")
            df.to_excel(output_path, index=False)
        else:
            logger.error(f"Unsupported export format: {format}")
            return None
        
        logger.info(f"Exported {len(df)} feedback records to {output_path}")
        return output_path

# Example usage
if __name__ == "__main__":
    exporter = FeedbackExporter()
    output_file = exporter.export_feedback(format='csv')
    if output_file:
        print(f"Feedback exported to: {output_file}")
    else:
        print("No feedback data to export")
