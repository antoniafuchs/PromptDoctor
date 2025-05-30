import pandas as pd
import os
from datetime import datetime
from typing import Dict, Any
import glob
import json

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

    def collect_chat_history(self):
        """Collect and standardize the complete chat history for all users"""
        try:
            # Base path for data
            data_dir = os.path.join(self.base_path, 'data')
            
            # Read interactions.csv which contains chat data
            interactions_path = os.path.join(data_dir, 'interactions.csv')
            if not os.path.exists(interactions_path):
                print(f"Interactions file not found: {interactions_path}")
                return None
                
            # Read the interactions CSV
            interactions = pd.read_csv(interactions_path, sep=';')
            
            # Filter for chat-related interactions
            chat_actions = ['CHAT', 'MODEL_OUTPUT', 'VALIDATION_VIEW', 'VALIDATION_ACCEPT_CLICK', 
                            'EDIT_UPDATE', 'EDIT_CLICK', 'ACCEPT_CLICK']
            
            chat_interactions = interactions[
                interactions['action_type'].isin(chat_actions) | 
                interactions['action'].isin(chat_actions)
            ].copy()
            
            if chat_interactions.empty:
                print("No chat interactions found")
                return None
                
            # Ensure we have the necessary columns
            required_columns = ['user_id', 'task_id', 'timestamp', 'original_prompt', 'model_response']
            for col in required_columns:
                if col not in chat_interactions.columns:
                    if col == 'model_response' and 'model_output' in chat_interactions.columns:
                        chat_interactions['model_response'] = chat_interactions['model_output']
                    else:
                        chat_interactions[col] = ""
            
            # Sort by user, task, and timestamp to get chronological chat history
            chat_interactions = chat_interactions.sort_values(['user_id', 'task_id', 'timestamp'])
            
            # Create a better structured chat history
            chat_history = []
            
            # Group by user and task
            for (user_id, task_id), group in chat_interactions.groupby(['user_id', 'task_id']):
                # Initialize chat thread
                thread = {
                    'user_id': user_id,
                    'task_id': task_id,
                    'messages': []
                }
                
                # Add each message in chronological order
                for idx, row in group.iterrows():
                    # User messages (prompts)
                    if pd.notna(row.get('original_prompt')) and row['original_prompt']:
                        thread['messages'].append({
                            'role': 'user',
                            'content': row['original_prompt'],
                            'timestamp': row['timestamp'],
                            'action_type': row.get('action_type', row.get('action', 'CHAT'))
                        })
                    
                    # Model responses
                    if pd.notna(row.get('model_response')) and row['model_response']:
                        thread['messages'].append({
                            'role': 'assistant',
                            'content': row['model_response'],
                            'timestamp': row['timestamp']
                        })
                    
                    # Also check for modified_prompt if it's an edit
                    if pd.notna(row.get('modified_prompt')) and row['modified_prompt']:
                        if row.get('action_type') == 'EDIT_UPDATE' or row.get('action') == 'EDIT_UPDATE':
                            thread['messages'].append({
                                'role': 'user_edit',
                                'original': row.get('original_prompt', ''),
                                'edited': row['modified_prompt'],
                                'timestamp': row['timestamp']
                            })
                
                chat_history.append(thread)
            
            # Save to a standardized chat_history.json file
            output_file = os.path.join(self.base_path, 'merged_data', 'chat_history.json')
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(chat_history, f, indent=2)
                
            print(f"Chat history saved to {output_file}")
            print(f"Collected {len(chat_history)} chat threads")
            
            # Also save as CSV for easier analysis
            chat_rows = []
            for thread in chat_history:
                user_id = thread['user_id']
                task_id = thread['task_id']
                
                for i, msg in enumerate(thread['messages']):
                    chat_rows.append({
                        'user_id': user_id,
                        'task_id': task_id,
                        'message_number': i + 1,
                        'role': msg['role'],
                        'content': msg['content'] if 'content' in msg else f"Edited: {msg.get('edited', '')}",
                        'timestamp': msg['timestamp'],
                        'action_type': msg.get('action_type', '')
                    })
            
            # Convert to DataFrame and save
            if chat_rows:
                chat_df = pd.DataFrame(chat_rows)
                csv_path = os.path.join(self.base_path, 'merged_data', 'chat_history.csv')
                chat_df.to_csv(csv_path, index=False, sep=';')
                print(f"Chat history CSV saved to {csv_path}")
                
            return output_file
        except Exception as e:
            print(f"Error collecting chat history: {str(e)}")
            return None

    def merge_all_data(self):
        """Merge all data sources into one CSV file"""
        try:
            # Collect files to merge
            data_files = {
                'users': os.path.join(self.base_path, 'data', 'users.csv'),
                'tasks': os.path.join(self.base_path, 'data', 'tasks.csv'),
                'interactions': os.path.join(self.base_path, 'data', 'interactions.csv'),
                'prompt_metrics': os.path.join(self.base_path, 'data', 'prompt_metrics.csv'),
                'unified_prompts': os.path.join(self.base_path, 'data', 'unified_prompts.csv'),
                'surveys': os.path.join(self.base_path, 'data', 'surveys.csv')
            }
            
            # Create a directory for merged data
            os.makedirs(os.path.join(self.base_path, 'merged_data'), exist_ok=True)
            
            # First, collect full chat history
            chat_history_file = self.collect_chat_history()
            
            # Check which files exist
            available_files = {}
            for name, path in data_files.items():
                if os.path.exists(path):
                    try:
                        df = pd.read_csv(path, sep=';')
                        available_files[name] = df
                        print(f"Loaded {name}.csv with {len(df)} rows")
                    except Exception as e:
                        print(f"Error reading {name}.csv: {str(e)}")
            
            if not available_files:
                print("No data files found to merge")
                return None
            
            # Start with users data
            if 'users' in available_files:
                merged_df = available_files['users'].copy()
                
                # Merge with tasks data
                if 'tasks' in available_files:
                    tasks_df = available_files['tasks']
                    merged_df = pd.merge(merged_df, tasks_df, on='user_id', how='outer')
                
                # Check if we should merge with prompt_metrics
                if 'prompt_metrics' in available_files:
                    metrics_df = available_files['prompt_metrics']
                    merged_df = pd.merge(
                        merged_df, 
                        metrics_df, 
                        on=['user_id', 'task_id'], 
                        how='outer',
                        suffixes=('', '_metrics')
                    )
                
                # Merge with survey data if available
                if 'surveys' in available_files:
                    surveys_df = available_files['surveys']
                    # Surveys might not have task_id, so merge only on user_id
                    merged_df = pd.merge(
                        merged_df, 
                        surveys_df, 
                        on='user_id', 
                        how='outer',
                        suffixes=('', '_survey')
                    )
                
                # Save the merged dataset
                output_file = os.path.join(self.base_path, 'merged_data', 'complete_study_data.csv')
                merged_df.to_csv(output_file, index=False, sep=';')
                print(f"Merged data saved to {output_file}")
                
                # Also create a more focused analysis dataset with just key metrics
                try:
                    analysis_df = self.create_analysis_dataset(available_files)
                    analysis_file = os.path.join(self.base_path, 'merged_data', 'analysis_dataset.csv')
                    analysis_df.to_csv(analysis_file, index=False, sep=';')
                    print(f"Analysis dataset saved to {analysis_file}")
                except Exception as e:
                    print(f"Error creating analysis dataset: {str(e)}")
                
                return output_file
            else:
                print("Users data file not found, cannot create merged dataset")
                return None
        except Exception as e:
            print(f"Error merging data: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def create_analysis_dataset(self, available_files):
        """Create a focused analysis dataset with key metrics"""
        # Start with empty DataFrame
        analysis_df = pd.DataFrame()
        
        # If we have users data, start with that
        if 'users' in available_files:
            users_df = available_files['users']
            
            # Select just the user ID, group, and demographic info
            user_cols = ['user_id', 'group', 'age', 'gender', 'training_level', 
                         'gen_ai_familiarity', 'prompt_eng_familiarity', 'cds_familiarity']
            user_cols = [col for col in user_cols if col in users_df.columns]
            analysis_df = users_df[user_cols].copy()
        else:
            # Create a minimal DataFrame with user IDs from tasks
            if 'tasks' in available_files:
                user_ids = available_files['tasks']['user_id'].unique()
                analysis_df = pd.DataFrame({'user_id': user_ids})
        
        # If we have task data, extract performance metrics
        if 'tasks' in available_files:
            tasks_df = available_files['tasks']
            
            # Group by user_id to get task completion metrics
            task_metrics = tasks_df.groupby('user_id').agg({
                'task_id': 'count',
                'task_duration': 'mean',
                'prompt_count': 'mean'
            }).reset_index()
            
            # Rename columns for clarity
            task_metrics = task_metrics.rename(columns={
                'task_id': 'completed_tasks',
                'task_duration': 'avg_task_duration',
                'prompt_count': 'avg_prompts_per_task'
            })
            
            # Merge with analysis dataframe
            if not analysis_df.empty:
                analysis_df = pd.merge(analysis_df, task_metrics, on='user_id', how='outer')
            else:
                analysis_df = task_metrics
        
        # If we have prompt metrics, add them
        if 'prompt_metrics' in available_files:
            metrics_df = available_files['prompt_metrics']
            
            # Calculate avg word count, edit distance per user
            prompt_metrics = metrics_df.groupby('user_id').agg({
                'word_count': 'mean',
                'levenshtein_distance': 'mean',
                'prompt_count': 'mean'
            }).reset_index()
            
            # Rename columns
            prompt_metrics = prompt_metrics.rename(columns={
                'word_count': 'avg_word_count',
                'levenshtein_distance': 'avg_edit_distance',
                'prompt_count': 'avg_prompt_count_metrics'
            })
            
            # Merge with analysis dataframe
            if not analysis_df.empty:
                analysis_df = pd.merge(analysis_df, prompt_metrics, on='user_id', how='outer')
            else:
                analysis_df = prompt_metrics
        
        # If we have survey data, add key metrics
        if 'surveys' in available_files:
            surveys_df = available_files['surveys']
            
            # Identify key survey columns to include
            key_survey_cols = ['user_id']
            
            # Add usability questions if they exist
            usability_cols = [col for col in surveys_df.columns if col.startswith(('US_', 'TR_'))]
            key_survey_cols.extend(usability_cols)
            
            # Filter survey data to only include these columns
            survey_cols = [col for col in key_survey_cols if col in surveys_df.columns]
            
            if len(survey_cols) > 1:  # Make sure we have more than just user_id
                survey_metrics = surveys_df[survey_cols].copy()
                
                # Merge with analysis dataframe
                if not analysis_df.empty:
                    analysis_df = pd.merge(analysis_df, survey_metrics, on='user_id', how='outer')
                else:
                    analysis_df = survey_metrics
        
        # Fill missing values with appropriate defaults
        numeric_cols = analysis_df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            analysis_df[col] = analysis_df[col].fillna(0)
        
        # Add a summary column for overall prompt efficiency
        if 'avg_task_duration' in analysis_df.columns and 'avg_prompts_per_task' in analysis_df.columns:
            # Lower is better - less time and fewer prompts
            analysis_df['prompt_efficiency'] = 1 / (
                analysis_df['avg_task_duration'] * analysis_df['avg_prompts_per_task']
            )
            
            # Replace infinity (if division by 0) with 0
            analysis_df['prompt_efficiency'] = analysis_df['prompt_efficiency'].replace([float('inf')], 0)
        
        return analysis_df
    
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
    
    def export_analysis_dataset(self, output_dir='analysis_data'):
        """Create analysis-ready datasets for statistical processing"""
        try:
            # Create output directory
            output_dir = os.path.join(self.base_path, output_dir)
            os.makedirs(output_dir, exist_ok=True)
            
            # 1. User journey dataset
            users = pd.read_csv(os.path.join(self.base_path, 'data', 'users.csv'), sep=';')
            interactions = pd.read_csv(os.path.join(self.base_path, 'data', 'interactions.csv'), sep=';')
            
            user_journey = pd.merge(
                users,
                interactions,
                on='user_id',
                how='left'
            )
            user_journey.to_csv(os.path.join(output_dir, 'user_journey.csv'), index=False, sep=';')
            
            # 2. Task performance dataset
            try:
                prompt_data = pd.read_csv(os.path.join(self.base_path, 'data', 'unified_prompts.csv'), sep=';')
            except:
                prompt_data = pd.DataFrame()
                
            try:
                surveys = pd.read_csv(os.path.join(self.base_path, 'data', 'surveys.csv'), sep=';')
            except:
                surveys = pd.DataFrame()
                
            # Only merge if both dataframes have data
            if not prompt_data.empty and not surveys.empty:
                task_performance = pd.merge(
                    prompt_data,
                    surveys,
                    on=['user_id', 'task_id'],
                    how='outer'
                )
                task_performance.to_csv(os.path.join(output_dir, 'task_performance.csv'), index=False, sep=';')
            
            # 3. Create a standardized prompt dataset
            self.create_standardized_prompt_data(output_dir)
            
            # 4. Create a standardized survey dataset with consistent column names
            self.create_standardized_survey_data(output_dir)
            
            print(f"Analysis datasets exported to {output_dir}")
            return True
            
        except Exception as e:
            print(f"Error exporting analysis datasets: {str(e)}")
            return False
    
    def create_standardized_prompt_data(self, output_dir):
        """Create a standardized prompt dataset with consistent column names"""
        try:
            # Load data from unified_prompts.csv and prompt_metrics.csv
            unified_prompts_path = os.path.join(self.base_path, 'data', 'unified_prompts.csv')
            prompt_metrics_path = os.path.join(self.base_path, 'data', 'prompt_metrics.csv')
            
            # Create standardized schema
            standard_columns = [
                'user_id', 'task_id', 'group', 'timestamp', 'action_type',
                'original_prompt', 'modified_prompt', 'highlighted_terms',
                'prompt_count', 'edit_distance', 'diff_type', 'model_type',
                'medical_term_count', 'word_count'
            ]
            
            # Initialize standardized DataFrame
            prompt_data = pd.DataFrame(columns=standard_columns)
            
            # Add data from unified_prompts
            if os.path.exists(unified_prompts_path):
                unified_df = pd.read_csv(unified_prompts_path, sep=';')
                # Select and rename columns to match standard schema
                unified_df = unified_df.rename(columns={
                    'action': 'action_type',
                    'last_prompt': 'modified_prompt'
                })
                prompt_data = pd.concat([prompt_data, unified_df[unified_df.columns.intersection(standard_columns)]])
            
            # Add data from prompt_metrics
            if os.path.exists(prompt_metrics_path):
                metrics_df = pd.read_csv(prompt_metrics_path, sep=';')
                # Map columns to standard schema
                metrics_df = metrics_df.rename(columns={
                    'first_prompt': 'original_prompt',
                    'last_prompt': 'modified_prompt',
                    'levenshtein_distance': 'edit_distance',
                    'word_count': 'word_count'
                })
                metrics_df['action_type'] = 'PROMPT_METRICS'
                prompt_data = pd.concat([prompt_data, metrics_df[metrics_df.columns.intersection(standard_columns)]])
            
            # Save standardized dataset
            prompt_data = prompt_data.drop_duplicates(subset=['user_id', 'task_id', 'timestamp', 'action_type'])
            prompt_data.to_csv(os.path.join(output_dir, 'prompt_data_standardized.csv'), index=False, sep=';')
            
            return True
        except Exception as e:
            print(f"Error creating standardized prompt data: {str(e)}")
            return False
    
    def create_standardized_survey_data(self, output_dir):
        """Create a standardized survey dataset with consistent column names"""
        try:
            # Load data from surveys.csv and tasks.csv
            surveys_path = os.path.join(self.base_path, 'data', 'surveys.csv')
            tasks_path = os.path.join(self.base_path, 'data', 'tasks.csv')
            
            # Define column mappings for standardization
            standardized_names = {
                'difficulty': 'task_difficulty',
                'PE_difficulty': 'task_difficulty',
                'mental_demand': 'mental_demand',
                'CL_mental': 'mental_demand',
                'frustration': 'frustration_level',
                'CL_frustration': 'frustration_level',
                'accuracy': 'perceived_accuracy',
                'MQ_accuracy': 'perceived_accuracy',
                'task_accomplishment': 'task_accomplishment',
                'CL_performance': 'task_accomplishment',
                'expectation_match': 'expectation_match',
                'PE_understanding': 'expectation_match',
                'clinical_usefulness': 'clinical_usefulness',
                'MQ_usefulness': 'clinical_usefulness'
            }
            
            # Load surveys if exists
            survey_data = pd.DataFrame()
            if os.path.exists(surveys_path):
                try:
                    survey_data = pd.read_csv(surveys_path, sep=';')
                except:
                    # Try with comma delimiter as fallback
                    try:
                        survey_data = pd.read_csv(surveys_path, sep=',')
                    except:
                        print("Warning: Could not read surveys.csv with either delimiter")
            
            # Load tasks if exists
            task_data = pd.DataFrame()
            if os.path.exists(tasks_path):
                task_data = pd.read_csv(tasks_path, sep=';')
            
            # Initialize standardized DataFrame
            standard_columns = [
                'user_id', 'task_id', 'timestamp', 'group', 'task_difficulty',
                'mental_demand', 'frustration_level', 'perceived_accuracy',
                'task_accomplishment', 'expectation_match', 'clinical_usefulness',
                'medical_inaccuracies', 'prompt_count', 'task_duration'
            ]
            standardized_survey = pd.DataFrame(columns=standard_columns)
            
            # Process survey data
            if not survey_data.empty:
                # Rename columns according to mapping
                for old_col, new_col in standardized_names.items():
                    if old_col in survey_data.columns:
                        survey_data[new_col] = survey_data[old_col]
                
                # Add categorical columns for analysis
                if 'task_difficulty' in survey_data.columns:
                    survey_data['difficulty_level'] = survey_data['task_difficulty'].apply(
                        lambda x: 'Low' if int(float(x)) <= 2 else 'Medium' if int(float(x)) <= 4 else 'High'
                    )
                
                standardized_survey = pd.concat([standardized_survey, survey_data])
            
            # Process task data
            if not task_data.empty:
                # Extract survey data from tasks.csv
                for old_col, new_col in standardized_names.items():
                    if old_col in task_data.columns:
                        task_data[new_col] = task_data[old_col]
                
                # Add task data that's not in surveys
                task_data_subset = task_data[task_data.columns.intersection(standard_columns)]
                standardized_survey = pd.concat([standardized_survey, task_data_subset])
            
            # Save standardized dataset
            standardized_survey = standardized_survey.drop_duplicates(subset=['user_id', 'task_id'])
            standardized_survey.to_csv(os.path.join(output_dir, 'survey_data_standardized.csv'), index=False, sep=';')
            
            return True
        except Exception as e:
            print(f"Error creating standardized survey data: {str(e)}")
            return False
