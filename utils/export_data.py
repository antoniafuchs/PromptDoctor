import os
import pandas as pd
import numpy as np
import json
from datetime import datetime
import logging
from typing import Dict, List, Optional, Union

# Configure logging
logger = logging.getLogger('export_data')
logger.setLevel(logging.INFO)

class DataExporter:
    """
    Class for exporting study data into analysis-ready formats
    """
    def __init__(self, base_path=None):
        if base_path is None:
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        else:
            self.base_path = base_path
            
        self.data_dir = os.path.join(self.base_path, 'data')
        self.export_dir = os.path.join(self.base_path, 'analysis_data')
        os.makedirs(self.export_dir, exist_ok=True)
        
    def export_all_data(self):
        """Export all datasets for analysis"""
        try:
            # Export standardized datasets
            self.export_standardized_prompt_data()
            self.export_standardized_survey_data()
            self.export_user_journey()
            self.export_task_performance()
            
            # Create specialized analysis datasets
            self.export_prompt_efficiency_metrics()
            self.export_highlight_analysis()
            
            logger.info(f"All data exported successfully to {self.export_dir}")
            return True
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return False
    
    def export_standardized_prompt_data(self):
        """Export standardized prompt data"""
        try:
            # Define source files
            source_files = {
                'unified_prompts': os.path.join(self.data_dir, 'unified_prompts.csv'),
                'prompt_metrics': os.path.join(self.data_dir, 'prompt_metrics.csv')
            }
            
            # Define standardized schema
            standard_columns = [
                'user_id', 'task_id', 'group', 'timestamp', 'action_type',
                'original_prompt', 'modified_prompt', 'highlighted_terms',
                'prompt_count', 'edit_distance', 'diff_type', 'model_type',
                'medical_term_count', 'word_count', 'data_source'
            ]
            
            # Initialize standardized DataFrame
            prompt_data = pd.DataFrame(columns=standard_columns)
            
            # Process each source file
            for source_name, file_path in source_files.items():
                if os.path.exists(file_path):
                    try:
                        df = pd.read_csv(file_path, sep=';')
                        df['data_source'] = source_name
                        
                        # Map columns to standard schema
                        column_mapping = {
                            'action': 'action_type',
                            'first_prompt': 'original_prompt',
                            'last_prompt': 'modified_prompt',
                            'levenshtein_distance': 'edit_distance'
                        }
                        
                        for old_col, new_col in column_mapping.items():
                            if old_col in df.columns and new_col not in df.columns:
                                df[new_col] = df[old_col]
                        
                        # Ensure all standard columns exist
                        for col in standard_columns:
                            if col not in df.columns:
                                df[col] = None
                        
                        # Select only standard columns that exist in the dataframe
                        prompt_data = pd.concat([
                            prompt_data,
                            df[df.columns.intersection(standard_columns)]
                        ])
                    except Exception as e:
                        logger.error(f"Error processing {source_name}: {str(e)}")
            
            # Add derived metrics
            if not prompt_data.empty:
                # Calculate word counts for prompts if not already present
                if 'word_count' not in prompt_data.columns or prompt_data['word_count'].isna().all():
                    prompt_data['word_count'] = prompt_data['original_prompt'].apply(
                        lambda x: len(str(x).split()) if pd.notna(x) else 0
                    )
                
                # Calculate medical term ratio
                prompt_data['medical_term_ratio'] = prompt_data.apply(
                    lambda row: row['medical_term_count'] / row['word_count'] if row['word_count'] > 0 else 0,
                    axis=1
                )
                
                # Add categorical variables for analysis
                prompt_data['edit_level'] = prompt_data['edit_distance'].apply(
                    lambda x: 'None' if pd.isna(x) or x == 0 else 
                             'Minor' if x < 0.3 else 
                             'Moderate' if x < 0.7 else 
                             'Major'
                )
                
                # Deduplicate based on user_id, task_id, timestamp, action_type
                prompt_data = prompt_data.drop_duplicates(
                    subset=['user_id', 'task_id', 'timestamp', 'action_type']
                )
                
                # Save to CSV
                output_path = os.path.join(self.export_dir, 'prompt_data_standardized.csv')
                prompt_data.to_csv(output_path, index=False, sep=';')
                logger.info(f"Exported standardized prompt data: {output_path}")
                
                return output_path
            else:
                logger.warning("No prompt data found to export")
                return None
        except Exception as e:
            logger.error(f"Error exporting standardized prompt data: {str(e)}")
            return None
    
    def export_standardized_survey_data(self):
        """Export standardized survey data"""
        try:
            # Define source files
            source_files = {
                'surveys': os.path.join(self.data_dir, 'surveys.csv'),
                'tasks': os.path.join(self.data_dir, 'tasks.csv')
            }
            
            # Define column mappings
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
            
            # Initialize standardized DataFrame
            standard_columns = [
                'user_id', 'task_id', 'timestamp', 'group', 'task_difficulty',
                'mental_demand', 'frustration_level', 'perceived_accuracy',
                'task_accomplishment', 'expectation_match', 'clinical_usefulness',
                'medical_inaccuracies', 'prompt_count', 'task_duration',
                'data_source'
            ]
            standardized_survey = pd.DataFrame(columns=standard_columns)
            
            # Process each source file
            for source_name, file_path in source_files.items():
                if os.path.exists(file_path):
                    try:
                        # Try different delimiters
                        try:
                            df = pd.read_csv(file_path, sep=';')
                        except:
                            try:
                                df = pd.read_csv(file_path, sep=',')
                            except:
                                logger.warning(f"Could not read {source_name} with either delimiter")
                                continue
                        
                        df['data_source'] = source_name
                        
                        # Map columns to standard schema
                        for old_col, new_col in standardized_names.items():
                            if old_col in df.columns:
                                df[new_col] = df[old_col]
                        
                        # Extract survey data from JSON if needed (for tasks.csv)
                        if 'survey_data' in df.columns:
                            df_with_survey = pd.DataFrame()
                            for idx, row in df.iterrows():
                                survey_data = row['survey_data']
                                if isinstance(survey_data, str) and survey_data.strip():
                                    try:
                                        # Parse JSON string
                                        survey_dict = json.loads(survey_data)
                                        # Create a new row with survey data
                                        survey_row = row.copy()
                                        for k, v in survey_dict.items():
                                            survey_row[k] = v
                                            # Map to standardized names
                                            if k in standardized_names:
                                                survey_row[standardized_names[k]] = v
                                        df_with_survey = pd.concat([df_with_survey, pd.DataFrame([survey_row])])
                                    except:
                                        # If JSON parsing fails, keep original row
                                        df_with_survey = pd.concat([df_with_survey, pd.DataFrame([row])])
                                else:
                                    # If no survey data, keep original row
                                    df_with_survey = pd.concat([df_with_survey, pd.DataFrame([row])])
                            
                            # Replace original dataframe if we successfully extracted survey data
                            if not df_with_survey.empty:
                                df = df_with_survey
                        
                        # Ensure all standard columns exist
                        for col in standard_columns:
                            if col not in df.columns:
                                df[col] = None
                        
                        # Select only standard columns that exist in the dataframe
                        standardized_survey = pd.concat([
                            standardized_survey,
                            df[df.columns.intersection(standard_columns)]
                        ])
                    except Exception as e:
                        logger.error(f"Error processing {source_name}: {str(e)}")
            
            # Add derived metrics
            if not standardized_survey.empty:
                # Convert numeric fields
                numeric_columns = [
                    'task_difficulty', 'mental_demand', 'frustration_level', 
                    'perceived_accuracy', 'task_accomplishment', 'expectation_match', 
                    'clinical_usefulness', 'prompt_count', 'task_duration'
                ]
                
                for col in numeric_columns:
                    if col in standardized_survey.columns:
                        standardized_survey[col] = pd.to_numeric(standardized_survey[col], errors='coerce')
                
                # Add categorical variables for analysis
                if 'task_difficulty' in standardized_survey.columns:
                    standardized_survey['difficulty_level'] = standardized_survey['task_difficulty'].apply(
                        lambda x: 'Low' if pd.isna(x) or x <= 2 else 
                                 'Medium' if x <= 4 else 
                                 'High'
                    )
                
                # Deduplicate based on user_id, task_id
                standardized_survey = standardized_survey.drop_duplicates(
                    subset=['user_id', 'task_id']
                )
                
                # Save to CSV
                output_path = os.path.join(self.export_dir, 'survey_data_standardized.csv')
                standardized_survey.to_csv(output_path, index=False, sep=';')
                logger.info(f"Exported standardized survey data: {output_path}")
                
                return output_path
            else:
                logger.warning("No survey data found to export")
                return None
        except Exception as e:
            logger.error(f"Error exporting standardized survey data: {str(e)}")
            return None
    
    def export_user_journey(self):
        """Export user journey dataset for analysis"""
        try:
            # Load users.csv and interactions.csv
            users_path = os.path.join(self.data_dir, 'users.csv')
            interactions_path = os.path.join(self.data_dir, 'interactions.csv')
            
            if not os.path.exists(users_path) or not os.path.exists(interactions_path):
                logger.warning("Missing users.csv or interactions.csv for user journey export")
                return None
            
            # Load data
            users = pd.read_csv(users_path, sep=';')
            interactions = pd.read_csv(interactions_path, sep=';')
            
            # Create user journey dataset
            user_journey = pd.merge(
                users,
                interactions,
                on='user_id',
                how='left'
            )
            
            # Add event sequence numbers
            user_journey['event_seq'] = user_journey.groupby(['user_id', 'task_id']).cumcount() + 1
            
            # Calculate time differences between events
            user_journey['timestamp'] = pd.to_datetime(user_journey['timestamp'], errors='coerce')
            user_journey = user_journey.sort_values(['user_id', 'task_id', 'timestamp'])
            
            # Calculate time since task start for each event
            user_journey['time_since_prev_event'] = user_journey.groupby(['user_id', 'task_id'])['timestamp'].diff().dt.total_seconds()
            
            # Save to CSV
            output_path = os.path.join(self.export_dir, 'user_journey.csv')
            user_journey.to_csv(output_path, index=False, sep=';')
            logger.info(f"Exported user journey data: {output_path}")
            
            return output_path
        except Exception as e:
            logger.error(f"Error exporting user journey: {str(e)}")
            return None
    
    def export_task_performance(self):
        """Export task performance dataset for analysis"""
        try:
            # First load standardized datasets if they exist
            prompt_path = os.path.join(self.export_dir, 'prompt_data_standardized.csv')
            survey_path = os.path.join(self.export_dir, 'survey_data_standardized.csv')
            
            # If standardized files don't exist, create them
            if not os.path.exists(prompt_path):
                prompt_path = self.export_standardized_prompt_data()
            if not os.path.exists(survey_path):
                survey_path = self.export_standardized_survey_data()
            
            if not prompt_path or not survey_path:
                logger.warning("Missing prompt or survey data for task performance export")
                return None
            
            # Load data
            try:
                prompt_data = pd.read_csv(prompt_path, sep=';')
                survey_data = pd.read_csv(survey_path, sep=';')
                
                # Get prompt count per task
                prompt_counts = prompt_data.groupby(['user_id', 'task_id'])['prompt_count'].max().reset_index()
                
                # Merge prompt counts with survey data
                task_performance = pd.merge(
                    survey_data,
                    prompt_counts,
                    on=['user_id', 'task_id'],
                    how='left',
                    suffixes=('', '_max')
                )
                
                # Use prompt_count from prompt data if available
                task_performance['prompt_count'] = task_performance['prompt_count_max'].fillna(task_performance['prompt_count'])
                task_performance = task_performance.drop(columns=['prompt_count_max'])
                
                # Add task efficiency metrics
                task_performance['task_efficiency'] = task_performance.apply(
                    lambda row: row['perceived_accuracy'] / row['prompt_count'] if pd.notna(row['perceived_accuracy']) and pd.notna(row['prompt_count']) and row['prompt_count'] > 0 else np.nan,
                    axis=1
                )
                
                # Add cognitive load index
                cognitive_load_cols = ['mental_demand', 'frustration_level']
                task_performance['cognitive_load_index'] = task_performance[cognitive_load_cols].mean(axis=1)
                
                # Add user expertise level based on gen_ai_familiarity if available
                if 'gen_ai_familiarity' in task_performance.columns:
                    task_performance['expertise_level'] = task_performance['gen_ai_familiarity'].apply(
                        lambda x: 'Novice' if pd.isna(x) or x <= 2 else 
                                'Intermediate' if x <= 4 else 
                                'Expert'
                    )
                
                # Save to CSV
                output_path = os.path.join(self.export_dir, 'task_performance.csv')
                task_performance.to_csv(output_path, index=False, sep=';')
                logger.info(f"Exported task performance data: {output_path}")
                
                return output_path
            except Exception as e:
                logger.error(f"Error processing data for task performance: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"Error exporting task performance: {str(e)}")
            return None
    
    def export_prompt_efficiency_metrics(self):
        """Export specialized dataset for prompt efficiency analysis"""
        try:
            # Get prompt data
            prompt_path = os.path.join(self.export_dir, 'prompt_data_standardized.csv')
            if not os.path.exists(prompt_path):
                prompt_path = self.export_standardized_prompt_data()
            
            if not prompt_path:
                logger.warning("Missing prompt data for efficiency metrics export")
                return None
            
            prompt_data = pd.read_csv(prompt_path, sep=';')
            
            # Filter to get only the PROMPT_METRICS actions which contain the final prompts
            metrics_data = prompt_data[prompt_data['action_type'] == 'PROMPT_METRICS'].copy()
            
            if metrics_data.empty:
                logger.warning("No PROMPT_METRICS data found for efficiency analysis")
                return None
            
            # Calculate additional metrics
            metrics_data['prompt_length'] = metrics_data['original_prompt'].apply(
                lambda x: len(str(x)) if pd.notna(x) else 0
            )
            
            metrics_data['words_per_medical_term'] = metrics_data.apply(
                lambda row: row['word_count'] / row['medical_term_count'] if pd.notna(row['medical_term_count']) and pd.notna(row['word_count']) and row['medical_term_count'] > 0 else np.nan,
                axis=1
            )
            
            # Add group and task efficiency metrics
            group_task_metrics = metrics_data.groupby(['group', 'task_id']).agg({
                'prompt_count': 'mean',
                'medical_term_count': 'mean',
                'word_count': 'mean',
                'medical_term_ratio': 'mean',
                'words_per_medical_term': 'mean',
                'user_id': 'nunique'
            }).reset_index()
            
            group_task_metrics = group_task_metrics.rename(columns={'user_id': 'user_count'})
            
            # Save to CSV
            output_path = os.path.join(self.export_dir, 'prompt_efficiency_metrics.csv')
            metrics_data.to_csv(output_path, index=False, sep=';')
            
            group_output_path = os.path.join(self.export_dir, 'group_task_metrics.csv')
            group_task_metrics.to_csv(group_output_path, index=False, sep=';')
            
            logger.info(f"Exported prompt efficiency metrics: {output_path}")
            logger.info(f"Exported group task metrics: {group_output_path}")
            
            return output_path
        except Exception as e:
            logger.error(f"Error exporting prompt efficiency metrics: {str(e)}")
            return None
    
    def export_highlight_analysis(self):
        """Export analysis dataset for highlighted terms"""
        try:
            # Get unified prompts data which contains highlight information
            unified_path = os.path.join(self.data_dir, 'unified_prompts.csv')
            if not os.path.exists(unified_path):
                logger.warning("Missing unified_prompts.csv for highlight analysis")
                return None
            
            # Load data
            unified_df = pd.read_csv(unified_path, sep=';')
            
            # Filter to get rows with highlight information
            highlight_data = unified_df[unified_df['highlighted_terms'].notna()].copy()
            
            if highlight_data.empty:
                logger.warning("No highlight data found for analysis")
                return None
            
            # Calculate highlight metrics
            highlight_data['terms_count'] = highlight_data['highlighted_terms'].apply(
                lambda x: len(str(x).split(',')) if pd.notna(x) and x != '' else 0
            )
            
            # Extract most common highlighted terms
            all_terms = []
            for terms in highlight_data['highlighted_terms']:
                if pd.notna(terms) and terms != '':
                    all_terms.extend(terms.split(','))
            
            term_counts = pd.Series(all_terms).value_counts().reset_index()
            term_counts.columns = ['term', 'count']
            
            # Group highlights by user and task
            user_highlight_summary = highlight_data.groupby(['user_id', 'task_id', 'group']).agg({
                'terms_count': ['mean', 'max', 'min', 'count'],
                'medical_term_count': ['mean', 'max']
            }).reset_index()
            
            # Flatten multi-level columns
            user_highlight_summary.columns = [
                f"{col[0]}_{col[1]}" if col[1] != '' else col[0] 
                for col in user_highlight_summary.columns
            ]
            
            # Save to CSV
            output_path = os.path.join(self.export_dir, 'highlight_analysis.csv')
            highlight_data.to_csv(output_path, index=False, sep=';')
            
            terms_path = os.path.join(self.export_dir, 'highlight_terms.csv')
            term_counts.to_csv(terms_path, index=False, sep=';')
            
            summary_path = os.path.join(self.export_dir, 'highlight_summary.csv')
            user_highlight_summary.to_csv(summary_path, index=False, sep=';')
            
            logger.info(f"Exported highlight analysis: {output_path}")
            logger.info(f"Exported highlight terms: {terms_path}")
            logger.info(f"Exported highlight summary: {summary_path}")
            
            return output_path
        except Exception as e:
            logger.error(f"Error exporting highlight analysis: {str(e)}")
            return None
    
    def export_combined_data(self):
        """Export a single combined dataset with all information for quick analysis"""
        try:
            # First ensure all standardized datasets exist
            self.export_standardized_prompt_data()
            self.export_standardized_survey_data()
            self.export_task_performance()
            
            # Load standardized datasets
            prompt_path = os.path.join(self.export_dir, 'prompt_data_standardized.csv')
            survey_path = os.path.join(self.export_dir, 'survey_data_standardized.csv')
            task_perf_path = os.path.join(self.export_dir, 'task_performance.csv')
            
            prompt_data = pd.read_csv(prompt_path, sep=';')
            survey_data = pd.read_csv(survey_path, sep=';')
            
            # Try to load task performance data if it exists
            try:
                task_performance = pd.read_csv(task_perf_path, sep=';')
            except:
                # If not available, use survey data
                task_performance = survey_data
            
            # Get user data
            users_path = os.path.join(self.data_dir, 'users.csv')
            if os.path.exists(users_path):
                users = pd.read_csv(users_path, sep=';')
            else:
                # Create minimal user data from other sources
                users = pd.DataFrame({'user_id': survey_data['user_id'].unique()})
            
            # Create combined dataset for analysis
            
            # 1. Get prompt-level data from standardized prompt data
            prompt_level = prompt_data[prompt_data['action_type'] == 'PROMPT_METRICS'].copy()
            
            # 2. Merge with task performance data
            combined_data = pd.merge(
                prompt_level,
                task_performance,
                on=['user_id', 'task_id'],
                how='outer',
                suffixes=('_prompt', '_task')
            )
            
            # 3. Add user information
            combined_data = pd.merge(
                combined_data,
                users,
                on='user_id',
                how='left',
                suffixes=('', '_user')
            )
            
            # Save combined dataset
            output_path = os.path.join(self.export_dir, 'combined_analysis_data.csv')
            combined_data.to_csv(output_path, index=False, sep=';')
            logger.info(f"Exported combined analysis data: {output_path}")
            
            return output_path
        except Exception as e:
            logger.error(f"Error exporting combined data: {str(e)}")
            return None

if __name__ == "__main__":
    # If run as a script, export all data
    exporter = DataExporter()
    exporter.export_all_data()
    print(f"Data exported to {exporter.export_dir}")
