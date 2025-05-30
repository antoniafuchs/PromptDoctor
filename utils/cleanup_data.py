import os
import glob
import pandas as pd
import json
import shutil
import argparse
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cleanup_data')

class DataCleanup:
    def __init__(self, base_path=None):
        if base_path is None:
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        else:
            self.base_path = base_path
            
        self.data_dir = os.path.join(self.base_path, 'data')
        self.merged_dir = os.path.join(self.base_path, 'merged_data')
        self.backup_dir = os.path.join(self.base_path, 'data_backups')
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def backup_file(self, file_path):
        """Create a backup of a file before deleting or modifying it"""
        if not os.path.exists(file_path):
            logger.warning(f"File not found for backup: {file_path}")
            return False
            
        # Create timestamped backup filename
        filename = os.path.basename(file_path)
        backup_name = f"{os.path.splitext(filename)[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(filename)[1]}"
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        # Copy the file to backup location
        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating backup of {file_path}: {str(e)}")
            return False
    
    def remove_validation_csv(self):
        """Remove validation.csv if it's empty or redundant"""
        validation_path = os.path.join(self.data_dir, 'validation.csv')
        
        if not os.path.exists(validation_path):
            logger.info("validation.csv not found, nothing to remove")
            return False
        
        # Check if file is empty (just header)
        try:
            df = pd.read_csv(validation_path, sep=';')
            if len(df) == 0:
                logger.info("validation.csv is empty (only has header row)")
                
                # Create backup before removing
                if self.backup_file(validation_path):
                    os.remove(validation_path)
                    logger.info("Removed empty validation.csv file")
                    return True
            else:
                # File has data, just log the info
                logger.info(f"validation.csv has {len(df)} rows of data, not removing")
                return False
        except Exception as e:
            logger.error(f"Error checking validation.csv: {str(e)}")
            return False
    
    def cleanup_timestamped_merged_files(self):
        """Remove timestamped merged_data files, keeping only the latest one"""
        # Look for timestamped complete_study_data files
        pattern = os.path.join(self.merged_dir, 'complete_study_data_*.csv')
        timestamped_files = glob.glob(pattern)
        
        if not timestamped_files:
            logger.info("No timestamped merged files found")
            return False
        
        # Sort files by timestamp (newest first)
        timestamped_files.sort(reverse=True)
        
        # Keep the newest file, backup and remove the rest
        newest_file = timestamped_files[0]
        logger.info(f"Keeping newest merged file: {newest_file}")
        
        removed_count = 0
        for file_path in timestamped_files[1:]:
            if self.backup_file(file_path):
                os.remove(file_path)
                removed_count += 1
                logger.info(f"Removed older merged file: {file_path}")
        
        logger.info(f"Removed {removed_count} older merged data files")
        return removed_count > 0
    
    def fix_surveys_csv(self):
        """Fix surveys.csv if it has comma delimiter instead of semicolon"""
        surveys_path = os.path.join(self.data_dir, 'surveys.csv')
        
        if not os.path.exists(surveys_path):
            logger.info("surveys.csv not found, nothing to fix")
            return False
        
        # Check the delimiter
        with open(surveys_path, 'r') as f:
            first_line = f.readline().strip()
            if ',' in first_line and ';' not in first_line:
                logger.info("surveys.csv has comma delimiter, fixing...")
                
                # Create backup before modifying
                if self.backup_file(surveys_path):
                    # Read with comma delimiter
                    df = pd.read_csv(surveys_path)
                    
                    # Save with semicolon delimiter
                    df.to_csv(surveys_path, sep=';', index=False)
                    logger.info("Fixed surveys.csv to use semicolon delimiter")
                    return True
            else:
                logger.info("surveys.csv already has correct delimiter")
                return False
    
    def check_redundant_files(self):
        """Check for and manage redundant data files"""
        redundant_files = {
            'validation.csv': {
                'alternative': 'unified_prompts.csv',
                'action_type': 'VALIDATION',
                'message': "Validation data is already stored in unified_prompts.csv"
            },
            'feedback.csv': {
                'alternative': 'interactions.csv',
                'action_type': 'FEEDBACK',
                'message': "Feedback data is already stored in interactions.csv"
            }
        }
        
        operations_performed = []
        
        for filename, info in redundant_files.items():
            filepath = os.path.join(self.data_dir, filename)
            if os.path.exists(filepath):
                # Check if file is empty (just header row)
                try:
                    df = pd.read_csv(filepath, sep=';')
                    if len(df) == 0:
                        # File is empty, back it up and delete
                        logger.info(f"{filename} is empty. {info['message']}")
                        if self.backup_file(filepath):
                            os.remove(filepath)
                            operations_performed.append(f"Removed empty {filename}")
                            logger.info(f"Removed empty {filename}")
                    else:
                        # File has data, check if data exists in alternative file
                        alt_filepath = os.path.join(self.data_dir, info['alternative'])
                        if os.path.exists(alt_filepath):
                            alt_df = pd.read_csv(alt_filepath, sep=';')
                            
                            # Check if alternative file contains all relevant data
                            if info['action_type'] in alt_df.get('action_type', alt_df.get('action', [])).values:
                                logger.info(f"{filename} data already exists in {info['alternative']}. Backing up.")
                                if self.backup_file(filepath):
                                    # Don't delete, just note that it's redundant
                                    operations_performed.append(f"Backed up {filename} (redundant with {info['alternative']})")
                except Exception as e:
                    logger.error(f"Error checking {filename}: {str(e)}")
        
        return operations_performed

    def fix_feedback_connections(self):
        """Fix feedback records that are missing connection to model outputs"""
        interactions_path = os.path.join(self.data_dir, 'interactions.csv')
        if not os.path.exists(interactions_path):
            logger.info("interactions.csv not found, nothing to fix")
            return False
        
        try:
            # Load interactions data
            df = pd.read_csv(interactions_path, sep=';')
            
            # Identify feedback entries without response_message_id
            feedback_mask = (df['action_type'] == 'FEEDBACK') & (
                (~df['response_message_id'].notna()) | (df['response_message_id'] == '')
            )
            
            feedback_entries = df[feedback_mask]
            if feedback_entries.empty:
                logger.info("No feedback entries need fixing")
                return False
            
            logger.info(f"Found {len(feedback_entries)} feedback entries without response connections")
            
            fixed_count = 0
            for idx, row in feedback_entries.iterrows():
                # Extract user_id and task_id
                user_id = row['user_id']
                message_id = row['message_id']
                
                # Extract task ID from message ID if possible
                task_id = 0
                if '_task' in message_id:
                    try:
                        task_part = message_id.split('_task')[1]
                        if '_' in task_part:
                            task_id = int(task_part.split('_')[0])
                    except:
                        pass
                
                # If task_id is in the dataframe and valid, use it
                if pd.notna(row.get('task_id')):
                    try:
                        task_id = int(row['task_id'])
                    except:
                        pass
                        
                # Generate a response message ID
                response_message_id = f"{message_id}_response"
                
                # Update the dataframe
                df.at[idx, 'response_message_id'] = response_message_id
                if task_id > 0:
                    df.at[idx, 'task_id'] = task_id
                    
                fixed_count += 1
                
            # Save the updated dataframe
            if fixed_count > 0:
                # Backup the original file
                if self.backup_file(interactions_path):
                    df.to_csv(interactions_path, sep=';', index=False)
                    logger.info(f"Fixed {fixed_count} feedback entries")
                    return True
                else:
                    logger.error("Failed to create backup before fixing feedback entries")
                    
            return False
                
        except Exception as e:
            logger.error(f"Error fixing feedback connections: {str(e)}")
            return False

    def run_cleanup(self, args):
        """Run the cleanup operations based on command line arguments"""
        operations_performed = []
        
        if args.all or args.validation:
            if self.remove_validation_csv():
                operations_performed.append("Removed empty validation.csv")
        
        if args.all or args.merged:
            if self.cleanup_timestamped_merged_files():
                operations_performed.append("Cleaned up timestamped merged data files")
        
        if args.all or args.surveys:
            if self.fix_surveys_csv():
                operations_performed.append("Fixed surveys.csv delimiter")
        
        if args.all or args.redundant:
            redundant_ops = self.check_redundant_files()
            operations_performed.extend(redundant_ops)
            
        if args.all or args.feedback:
            if self.fix_feedback_connections():
                operations_performed.append("Fixed feedback connections in interactions.csv")
        
        if operations_performed:
            logger.info("Cleanup completed successfully:")
            for op in operations_performed:
                logger.info(f"- {op}")
        else:
            logger.info("No cleanup operations were needed or performed")

def main():
    parser = argparse.ArgumentParser(description="Clean up and organize PromptDoctor data files")
    parser.add_argument('--all', action='store_true', help='Perform all cleanup operations')
    parser.add_argument('--validation', action='store_true', help='Remove empty validation.csv')
    parser.add_argument('--merged', action='store_true', help='Clean up timestamped merged data files')
    parser.add_argument('--surveys', action='store_true', help='Fix surveys.csv delimiter')
    parser.add_argument('--redundant', action='store_true', help='Check and manage redundant data files')
    parser.add_argument('--feedback', action='store_true', help='Fix feedback connections in interactions.csv')
    parser.add_argument('--path', type=str, help='Base path to PromptDoctor directory')
    
    args = parser.parse_args()
    
    # If no specific operations specified, default to --all
    if not (args.all or args.validation or args.merged or args.surveys or args.redundant or args.feedback):
        args.all = True
    
    cleanup = DataCleanup(args.path)
    cleanup.run_cleanup(args)

if __name__ == "__main__":
    main()
