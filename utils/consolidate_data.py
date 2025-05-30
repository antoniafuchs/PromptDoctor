import os
import sys
import pandas as pd
from utils.data_storage import DataStorage

def main():
    """Consolidate various data files into a comprehensive dataset"""
    # Initialize data storage
    storage = DataStorage()
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_path, 'data')
    
    # Create a DataMerger instance for consolidated outputs
    from utils.data_merger import DataMerger
    merger = DataMerger()
    merger.base_path = base_path
    
    # First, consolidate prompt data into a standardized format
    unified_file = os.path.join(data_dir, "prompt_data.csv")
    
    # Check if data needs consolidation
    if os.path.exists(unified_file):
        print(f"Consolidated prompt data file already exists: {unified_file}")
        
        # Print summary of unified data
        df = pd.read_csv(unified_file, sep=';')
        print(f"\nContains {len(df)} prompt entries")
        print(f"Users: {df['user_id'].nunique()}")
        print(f"Tasks: {df['task_id'].nunique() if 'task_id' in df.columns else 'N/A'}")
        
        # Calculate prompt counts by user and task
        if 'prompt_count' in df.columns:
            user_counts = df.groupby('user_id')['prompt_count'].max().reset_index()
            print("\nPrompt counts by user:")
            print(user_counts)
            
            task_counts = df.groupby('task_id')['prompt_count'].mean().reset_index()
            print("\nAverage prompt counts by task:")
            print(task_counts)
    else:
        # Load and consolidate different data sources
        data_files = {
            'prompt_metrics': os.path.join(data_dir, "prompt_metrics.csv"),
            'unified_prompts': os.path.join(data_dir, "unified_prompts.csv"),
            'validation': os.path.join(data_dir, "validation.csv"),
            'interactions': os.path.join(data_dir, "interactions.csv")
        }
        
        # Initialize a list to store all dataframes
        dfs = []
        
        # Load each source file
        for source_name, file_path in data_files.items():
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path, sep=';')
                    df['data_source'] = source_name
                    dfs.append(df)
                    print(f"Loaded {len(df)} records from {source_name}")
                except Exception as e:
                    print(f"Error loading {source_name}: {str(e)}")
        
        # If no data found, inform user
        if not dfs:
            print("No data files found to consolidate")
            return
        
        # Define standardized column schema
        standard_columns = [
            'user_id', 'task_id', 'group', 'timestamp', 'event_type', 'action_type',
            'original_prompt', 'modified_prompt', 'highlighted_terms',
            'medical_term_count', 'prompt_count', 'message_id', 'model_type',
            'model_name', 'edit_distance', 'diff_type', 'data_source'
        ]
        
        # Create a comprehensive dataset with standardized columns
        all_columns = set()
        for df in dfs:
            all_columns.update(df.columns)
        
        # Initialize standardized dataframe
        standardized_df = pd.DataFrame(columns=standard_columns)
        
        # Standardize each dataframe before concatenation
        for df in dfs:
            # Map existing columns to standard columns where needed
            column_mapping = {
                'action': 'action_type',
                'first_prompt': 'original_prompt',
                'last_prompt': 'modified_prompt',
                'levenshtein_distance': 'edit_distance'
            }
            
            # Apply column mapping
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns and new_col not in df.columns:
                    df[new_col] = df[old_col]
            
            # Ensure all standard columns exist
            for col in standard_columns:
                if col not in df.columns:
                    df[col] = pd.NA
            
            # Select only standard columns
            standardized_df = pd.concat([
                standardized_df, 
                df[df.columns.intersection(standard_columns)]
            ])
        
        # Save the standardized dataset
        standardized_df.to_csv(unified_file, index=False, sep=';')
        print(f"Created standardized prompt data file: {unified_file}")
        
        # Print summary
        print(f"\nConsolidated {len(standardized_df)} prompt entries")
        print(f"Users: {standardized_df['user_id'].nunique()}")
        print(f"Tasks: {standardized_df['task_id'].nunique() if 'task_id' in standardized_df.columns else 'N/A'}")
    
    # Now create analysis-ready export datasets
    print("\nGenerating analysis-ready datasets...")
    merger.export_analysis_dataset()
    
    # Fix surveys.csv if it exists but has delimiter issues
    surveys_file = os.path.join(data_dir, "surveys.csv")
    if os.path.exists(surveys_file):
        try:
            # Try to read with semicolon delimiter
            surveys_df = pd.read_csv(surveys_file, sep=';')
            print(f"Surveys file looks good with {len(surveys_df)} records")
        except:
            try:
                # Try with comma delimiter
                surveys_df = pd.read_csv(surveys_file, sep=',')
                # If successful, convert to semicolon delimiter
                surveys_df.to_csv(surveys_file, index=False, sep=';')
                print(f"Fixed surveys.csv delimiter (converted from comma to semicolon)")
            except Exception as e:
                print(f"Error fixing surveys.csv: {str(e)}")
    
    # Generate a final consolidated study dataset that can be used for analysis
    try:
        final_dataset = merger.merge_all_data()
        if final_dataset is not None:
            print(f"\nGenerated final consolidated dataset with {len(final_dataset)} records")
            print(f"Contains data for {final_dataset['user_id'].nunique()} users")
            print(f"Tasks: {final_dataset['task_id'].nunique() if 'task_id' in final_dataset.columns else 'N/A'}")
    except Exception as e:
        print(f"Error generating final dataset: {str(e)}")

if __name__ == "__main__":
    main()
