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
    
    # Check if unified prompts file already exists
    unified_file = os.path.join(data_dir, "unified_prompts.csv")
    if os.path.exists(unified_file):
        print(f"Unified prompts file already exists: {unified_file}")
        
        # Print summary of unified data
        df = pd.read_csv(unified_file, sep=';')
        print(f"\nContains {len(df)} prompt entries")
        print(f"Users: {df['user_id'].nunique()}")
        print(f"Tasks: {df['task_id'].nunique()}")
        
        # Calculate prompt counts by user and task
        if 'prompt_count' in df.columns:
            user_counts = df.groupby('user_id')['prompt_count'].max().reset_index()
            print("\nPrompt counts by user:")
            print(user_counts)
            
            task_counts = df.groupby('task_id')['prompt_count'].mean().reset_index()
            print("\nAverage prompt counts by task:")
            print(task_counts)
        
        return
    
    # If unified file doesn't exist, consolidate the data
    # Load the different prompt-related files
    prompt_metrics_file = os.path.join(data_dir, "prompt_metrics.csv")
    prompt_counts_file = os.path.join(data_dir, "prompt_counts.csv")
    validation_file = os.path.join(data_dir, "validation.csv")
    prompt_data_file = os.path.join(data_dir, "prompt_data.csv")
    
    dfs = []
    
    # Load each file if it exists
    if os.path.exists(prompt_metrics_file):
        try:
            metrics_df = pd.read_csv(prompt_metrics_file, sep=';')
            metrics_df['data_source'] = 'prompt_metrics'
            dfs.append(metrics_df)
        except Exception as e:
            print(f"Error loading prompt_metrics.csv: {str(e)}")
    
    if os.path.exists(prompt_counts_file):
        try:
            counts_df = pd.read_csv(prompt_counts_file, sep=';')
            counts_df['data_source'] = 'prompt_counts'
            dfs.append(counts_df)
        except Exception as e:
            print(f"Error loading prompt_counts.csv: {str(e)}")
    
    if os.path.exists(validation_file):
        try:
            validation_df = pd.read_csv(validation_file, sep=';')
            validation_df['data_source'] = 'validation'
            dfs.append(validation_df)
        except Exception as e:
            print(f"Error loading validation.csv: {str(e)}")
            
    # Also load prompt_data.csv which may contain additional/consolidated information
    if os.path.exists(prompt_data_file):
        try:
            prompt_data_df = pd.read_csv(prompt_data_file, sep=',')  # Note: this file uses comma separator
            prompt_data_df['data_source'] = 'prompt_data'
            dfs.append(prompt_data_df)
        except Exception as e:
            print(f"Error loading prompt_data.csv: {str(e)}")
    
    # If no data found, inform user
    if not dfs:
        print("No prompt data files found to consolidate")
        return
    
    # Create a comprehensive dataset with all columns
    all_columns = set()
    for df in dfs:
        all_columns.update(df.columns)
    
    # Initialize unified dataframe
    unified_df = pd.DataFrame(columns=list(all_columns))
    
    # Combine all dataframes
    for df in dfs:
        for col in all_columns:
            if col not in df.columns:
                df[col] = pd.NA
        unified_df = pd.concat([unified_df, df])
    
    # Add timestamp check to identify possible timezone issues
    if 'timestamp' in unified_df.columns:
        try:
            unified_df['timestamp_utc'] = pd.to_datetime(unified_df['timestamp'], errors='coerce')
            print("\nTimestamp analysis:")
            print(f"Min timestamp: {unified_df['timestamp_utc'].min()}")
            print(f"Max timestamp: {unified_df['timestamp_utc'].max()}")
            # Check if timestamps appear to be in different timezones
            if not pd.isna(unified_df['timestamp_utc']).all():
                hour_distribution = unified_df['timestamp_utc'].dt.hour.value_counts().sort_index()
                print("\nHour distribution (UTC):")
                print(hour_distribution)
        except Exception as e:
            print(f"Error analyzing timestamps: {str(e)}")
    
    # Save the unified file
    unified_df.to_csv(unified_file, index=False, sep=';')
    print(f"Created unified prompts file: {unified_file}")
    
    # Print summary
    print(f"\nConsolidated {len(unified_df)} prompt entries")
    print(f"Users: {unified_df['user_id'].nunique()}")
    print(f"Tasks: {unified_df['task_id'].nunique() if 'task_id' in unified_df.columns else 'N/A'}")
    
    # Identify and report potential duplicates across sources
    if 'data_source' in unified_df.columns and 'user_id' in unified_df.columns and 'task_id' in unified_df.columns:
        try:
            # Group by user, task and count distinct data sources
            duplicate_check = unified_df.groupby(['user_id', 'task_id'])['data_source'].nunique().reset_index()
            multiple_sources = duplicate_check[duplicate_check['data_source'] > 1]
            
            if len(multiple_sources) > 0:
                print("\nPotential duplicate data detected for these user/task combinations:")
                print(multiple_sources)
                
                # Show a sample of duplicate entries
                print("\nExample of duplicate entries:")
                sample_user = multiple_sources.iloc[0]['user_id']
                sample_task = multiple_sources.iloc[0]['task_id']
                duplicates = unified_df[(unified_df['user_id'] == sample_user) & 
                                       (unified_df['task_id'] == sample_task)]
                print(duplicates[['user_id', 'task_id', 'data_source', 'timestamp']].head())
        except Exception as e:
            print(f"Error checking for duplicates: {str(e)}")

if __name__ == "__main__":
    main()
