"""
Study Owner Dashboard - Command Line Version

This script provides a simple command-line view of current study statistics
without needing to launch the full Streamlit dashboard.
"""
import os
import sys
import pandas as pd
import argparse
from datetime import datetime, timedelta
import textwrap

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f" {text} ".center(60, "="))
    print("=" * 60)

def print_subheader(text):
    """Print a formatted subheader"""
    print("\n" + "-" * 60)
    print(f" {text} ")
    print("-" * 60)

def check_data_directory():
    """Check if data directory exists and return path"""
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(data_dir):
        print(f"ERROR: Data directory not found at {data_dir}")
        sys.exit(1)
    return data_dir

def print_user_stats(data_dir):
    """Print user statistics"""
    print_header("USER STATISTICS")
    
    users_file = os.path.join(data_dir, 'users.csv')
    if not os.path.exists(users_file):
        print("No user data found.")
        return
    
    users_df = pd.read_csv(users_file, sep=';')
    
    # Count total users
    total_users = len(users_df)
    print(f"Total registered users: {total_users}")
    
    # Count by group
    if 'group' in users_df.columns:
        print("\nUsers by group:")
        group_counts = users_df['group'].value_counts()
        for group, count in group_counts.items():
            print(f"  Group {group}: {count} users ({count/total_users*100:.1f}%)")
    
    # Count by demographics if available
    if 'gender' in users_df.columns:
        print("\nDemographics:")
        gender_counts = users_df['gender'].value_counts()
        for gender, count in gender_counts.items():
            print(f"  {gender}: {count} users ({count/total_users*100:.1f}%)")
    
    # Experience level
    if 'training_level' in users_df.columns:
        print("\nMedical experience level:")
        training_counts = users_df['training_level'].value_counts()
        for level, count in training_counts.items():
            print(f"  {level}: {count} users ({count/total_users*100:.1f}%)")
    
    # AI familiarity
    if 'gen_ai_familiarity' in users_df.columns:
        try:
            users_df['gen_ai_familiarity'] = pd.to_numeric(users_df['gen_ai_familiarity'], errors='coerce')
            avg_familiarity = users_df['gen_ai_familiarity'].mean()
            print(f"\nAverage AI familiarity (1-5 scale): {avg_familiarity:.2f}")
        except:
            pass
        
    # Prompt engineering familiarity
    if 'prompt_eng_familiarity' in users_df.columns:
        try:
            users_df['prompt_eng_familiarity'] = pd.to_numeric(users_df['prompt_eng_familiarity'], errors='coerce')
            avg_familiarity = users_df['prompt_eng_familiarity'].mean()
            print(f"Average prompt engineering familiarity (1-5 scale): {avg_familiarity:.2f}")
        except:
            pass

def print_task_stats(data_dir):
    """Print task completion statistics"""
    print_header("TASK STATISTICS")
    
    tasks_file = os.path.join(data_dir, 'tasks.csv')
    if not os.path.exists(tasks_file):
        print("No task data found.")
        return
    
    tasks_df = pd.read_csv(tasks_file, sep=';')
    
    # Filter to completed tasks
    completed_tasks = tasks_df[tasks_df['completion_status'] == 'completed']
    
    print(f"Total tasks completed: {len(completed_tasks)}")
    
    # Tasks by ID
    if 'task_id' in completed_tasks.columns:
        print("\nCompletions by task:")
        task_counts = completed_tasks['task_id'].value_counts().sort_index()
        for task_id, count in task_counts.items():
            print(f"  Task {task_id}: {count} completions")
    
    # Tasks by group
    if 'task_id' in completed_tasks.columns and 'group' in completed_tasks.columns:
        print("\nCompletions by task and group:")
        group_task_counts = completed_tasks.groupby(['group', 'task_id']).size().unstack(fill_value=0)
        print(group_task_counts)
    
    # Task duration statistics
    if 'task_duration' in completed_tasks.columns:
        try:
            completed_tasks['task_duration'] = pd.to_numeric(completed_tasks['task_duration'], errors='coerce')
            
            print("\nAverage task duration (minutes):")
            task_duration = completed_tasks.groupby('task_id')['task_duration'].mean() / 60
            for task_id, duration in task_duration.items():
                print(f"  Task {task_id}: {duration:.2f} minutes")
                
            # Duration by group if available
            if 'group' in completed_tasks.columns:
                print("\nAverage task duration by group (minutes):")
                group_duration = completed_tasks.groupby(['group', 'task_id'])['task_duration'].mean() / 60
                print(group_duration.unstack())
        except Exception as e:
            print(f"Error analyzing task duration: {str(e)}")

def print_feedback_stats(data_dir):
    """Print feedback statistics"""
    print_header("FEEDBACK STATISTICS")
    
    feedback_file = os.path.join(data_dir, 'feedback.csv')
    interactions_file = os.path.join(data_dir, 'interactions.csv')
    
    # Try feedback file first
    if os.path.exists(feedback_file):
        try:
            feedback_df = pd.read_csv(feedback_file, sep=';')
            print(f"Total feedback records: {len(feedback_df)}")
            
            if 'feedback_value' in feedback_df.columns:
                feedback_df['feedback_value'] = pd.to_numeric(feedback_df['feedback_value'], errors='coerce')
                
                positive = len(feedback_df[feedback_df['feedback_value'] > 0])
                negative = len(feedback_df[feedback_df['feedback_value'] < 0])
                neutral = len(feedback_df[feedback_df['feedback_value'] == 0])
                
                print("\nFeedback distribution:")
                print(f"  Positive: {positive} ({positive/len(feedback_df)*100:.1f}%)")
                print(f"  Neutral: {neutral} ({neutral/len(feedback_df)*100:.1f}%)")
                print(f"  Negative: {negative} ({negative/len(feedback_df)*100:.1f}%)")
            
            return
        except Exception as e:
            print(f"Error reading feedback file: {str(e)}")
    
    # Fall back to interactions file
    if os.path.exists(interactions_file):
        try:
            interactions_df = pd.read_csv(interactions_file, sep=';')
            feedback_df = interactions_df[interactions_df['action_type'] == 'FEEDBACK']
            
            if len(feedback_df) == 0:
                print("No feedback data found.")
                return
            
            print(f"Total feedback records (from interactions): {len(feedback_df)}")
            
            if 'feedback' in feedback_df.columns:
                feedback_df['feedback'] = pd.to_numeric(feedback_df['feedback'], errors='coerce')
                
                positive = len(feedback_df[feedback_df['feedback'] > 0])
                negative = len(feedback_df[feedback_df['feedback'] < 0])
                neutral = len(feedback_df[feedback_df['feedback'] == 0])
                
                print("\nFeedback distribution:")
                print(f"  Positive: {positive} ({positive/len(feedback_df)*100:.1f}%)")
                print(f"  Neutral: {neutral} ({neutral/len(feedback_df)*100:.1f}%)")
                print(f"  Negative: {negative} ({negative/len(feedback_df)*100:.1f}%)")
            
            # Feedback by task
            if 'task_id' in feedback_df.columns and 'feedback' in feedback_df.columns:
                print("\nFeedback by task:")
                task_feedback = feedback_df.groupby('task_id')['feedback'].agg(['mean', 'count'])
                for task_id, row in task_feedback.iterrows():
                    print(f"  Task {task_id}: {row['count']} feedback records, avg rating: {row['mean']:.2f}")
            
        except Exception as e:
            print(f"Error analyzing feedback data: {str(e)}")
    else:
        print("No feedback data found.")

def print_survey_stats(data_dir):
    """Print survey statistics"""
    print_header("SURVEY STATISTICS")
    
    surveys_file = os.path.join(data_dir, 'surveys.csv')
    if not os.path.exists(surveys_file):
        print("No survey data found.")
        return
    
    try:
        surveys_df = pd.read_csv(surveys_file, sep=';')
        print(f"Total survey responses: {len(surveys_df)}")
        
        # Survey responses by group
        if 'group' in surveys_df.columns:
            print("\nResponses by group:")
            group_counts = surveys_df['group'].value_counts()
            for group, count in group_counts.items():
                print(f"  Group {group}: {count} responses")
        
        # Calculate averages for Likert scale questions
        likert_columns = [
            'US_ease', 'US_clarity', 'US_reuse',
            'TR_model_trust', 'TR_understanding', 'TR_current_trust', 'TR_explanations'
        ]
        
        print("\nAverage ratings (scale 1-5):")
        for col in likert_columns:
            if col in surveys_df.columns:
                try:
                    surveys_df[col] = pd.to_numeric(surveys_df[col], errors='coerce')
                    avg = surveys_df[col].mean()
                    print(f"  {col}: {avg:.2f}")
                except:
                    pass
        
        # Group B specific metrics
        if 'EX_helpful' in surveys_df.columns:
            group_b_df = surveys_df[surveys_df['group'] == 'B']
            if not group_b_df.empty:
                print("\nGroup B specific metrics (scale 1-5):")
                
                explainability_columns = [
                    'EX_helpful', 'EX_refinement', 'EX_understanding', 
                    'EX_edit_helpful', 'EX_terms_useful'
                ]
                
                for col in explainability_columns:
                    if col in group_b_df.columns:
                        try:
                            group_b_df[col] = pd.to_numeric(group_b_df[col], errors='coerce')
                            avg = group_b_df[col].mean()
                            print(f"  {col}: {avg:.2f}")
                        except:
                            pass
    except Exception as e:
        print(f"Error analyzing survey data: {str(e)}")

def print_prompt_analysis(data_dir):
    """Print prompt analysis statistics"""
    print_header("PROMPT ANALYSIS")
    
    # Check for prompt metrics file
    prompt_metrics_file = os.path.join(data_dir, 'prompt_metrics.csv')
    unified_prompts_file = os.path.join(data_dir, 'unified_prompts.csv')
    prompt_data_file = os.path.join(data_dir, 'prompt_data.csv')
    
    # First try unified_prompts which should have the most comprehensive data
    if os.path.exists(unified_prompts_file):
        try:
            prompts_df = pd.read_csv(unified_prompts_file, sep=';')
            print(f"Total prompts tracked: {len(prompts_df)}")
            
            # Calculate average prompt count per task
            if 'prompt_count' in prompts_df.columns and 'task_id' in prompts_df.columns:
                prompts_df['prompt_count'] = pd.to_numeric(prompts_df['prompt_count'], errors='coerce')
                avg_prompts = prompts_df.groupby('task_id')['prompt_count'].mean()
                
                print("\nAverage prompts per task:")
                for task_id, avg in avg_prompts.items():
                    print(f"  Task {task_id}: {avg:.2f} prompts")
            
            # Calculate edit distances by task and group
            if 'edit_distance' in prompts_df.columns and 'task_id' in prompts_df.columns and 'group' in prompts_df.columns:
                prompts_df['edit_distance'] = pd.to_numeric(prompts_df['edit_distance'], errors='coerce')
                
                print("\nAverage edit distances by task and group:")
                for task_id, task_group in prompts_df.groupby('task_id'):
                    for group, group_data in task_group.groupby('group'):
                        avg_distance = group_data['edit_distance'].mean()
                        print(f"  Task {task_id}, Group {group}: {avg_distance:.4f}")
            
            # Medical terms analysis
            if 'medical_term_count' in prompts_df.columns and 'highlighted_terms' in prompts_df.columns:
                prompts_df['medical_term_count'] = pd.to_numeric(prompts_df['medical_term_count'], errors='coerce')
                
                print("\nMedical term usage:")
                avg_terms = prompts_df.groupby('task_id')['medical_term_count'].mean()
                for task_id, avg in avg_terms.items():
                    print(f"  Task {task_id}: {avg:.2f} medical terms per prompt")
                
                # Get most common highlighted terms
                if 'highlighted_terms' in prompts_df.columns:
                    all_terms = []
                    
                    # Collect all terms from highlighted_terms column
                    for terms in prompts_df['highlighted_terms'].dropna():
                        if isinstance(terms, str) and terms:
                            term_list = terms.split(',')
                            all_terms.extend(term_list)
                    
                    # Count term frequencies
                    term_counts = {}
                    for term in all_terms:
                        term = term.strip()
                        if term:
                            term_counts[term] = term_counts.get(term, 0) + 1
                    
                    # Sort by frequency and display top 10
                    sorted_terms = sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                    
                    if sorted_terms:
                        print("\nTop 10 highlighted medical terms:")
                        for term, count in sorted_terms:
                            print(f"  {term}: {count}")
            
            # Sample prompts
            print("\nSample recent prompts:")
            if 'timestamp' in prompts_df.columns:
                prompts_df['timestamp'] = pd.to_datetime(prompts_df['timestamp'], errors='coerce')
                recent_prompts = prompts_df.sort_values('timestamp', ascending=False).head(5)
                
                for i, (_, row) in enumerate(recent_prompts.iterrows()):
                    task_id = row.get('task_id', 'unknown')
                    user_id = row.get('user_id', 'unknown')
                    timestamp = row.get('timestamp', 'unknown')
                    last_prompt = row.get('last_prompt', '')
                    if isinstance(last_prompt, str) and last_prompt:
                        # Truncate and format the prompt
                        prompt_preview = textwrap.shorten(last_prompt, width=70, placeholder="...")
                        print(f"\n  Sample {i+1} - User {user_id}, Task {task_id}, {timestamp}")
                        print(f"  {prompt_preview}")
            
            return
        except Exception as e:
            print(f"Error reading unified prompts data: {str(e)}")
    
    # Fall back to prompt_metrics.csv
    if os.path.exists(prompt_metrics_file):
        try:
            metrics_df = pd.read_csv(prompt_metrics_file, sep=';')
            print(f"Total prompt metrics records: {len(metrics_df)}")
            
            # Calculate average prompt count per task
            if 'prompt_count' in metrics_df.columns and 'task_id' in metrics_df.columns:
                metrics_df['prompt_count'] = pd.to_numeric(metrics_df['prompt_count'], errors='coerce')
                avg_prompts = metrics_df.groupby('task_id')['prompt_count'].mean()
                
                print("\nAverage prompts per task:")
                for task_id, avg in avg_prompts.items():
                    print(f"  Task {task_id}: {avg:.2f} prompts")
            
            # Calculate edit distances by task and group
            if 'levenshtein_distance' in metrics_df.columns and 'task_id' in metrics_df.columns and 'group' in metrics_df.columns:
                metrics_df['levenshtein_distance'] = pd.to_numeric(metrics_df['levenshtein_distance'], errors='coerce')
                
                print("\nAverage edit distances by task and group:")
                for task_id, task_group in metrics_df.groupby('task_id'):
                    for group, group_data in task_group.groupby('group'):
                        avg_distance = group_data['levenshtein_distance'].mean()
                        print(f"  Task {task_id}, Group {group}: {avg_distance:.4f}")
            
            # Sample prompts
            print("\nSample recent prompts:")
            if 'timestamp' in metrics_df.columns and 'last_prompt' in metrics_df.columns:
                metrics_df['timestamp'] = pd.to_datetime(metrics_df['timestamp'], errors='coerce')
                recent_metrics = metrics_df.sort_values('timestamp', ascending=False).head(5)
                
                for i, (_, row) in enumerate(recent_metrics.iterrows()):
                    task_id = row.get('task_id', 'unknown')
                    user_id = row.get('user_id', 'unknown')
                    timestamp = row.get('timestamp', 'unknown')
                    last_prompt = row.get('last_prompt', '')
                    if isinstance(last_prompt, str) and last_prompt:
                        # Truncate and format the prompt
                        prompt_preview = textwrap.shorten(last_prompt, width=70, placeholder="...")
                        print(f"\n  Sample {i+1} - User {user_id}, Task {task_id}, {timestamp}")
                        print(f"  {prompt_preview}")
            
            return
        except Exception as e:
            print(f"Error reading prompt metrics data: {str(e)}")
    
    # Last resort - use prompt_data
    if os.path.exists(prompt_data_file):
        try:
            data_df = pd.read_csv(prompt_data_file)
            print(f"Total prompt data records: {len(data_df)}")
            
            # Count records by action type
            if 'action_type' in data_df.columns:
                action_counts = data_df['action_type'].value_counts()
                
                print("\nAction type distribution:")
                for action, count in action_counts.items():
                    print(f"  {action}: {count}")
            
            # Sample prompts
            print("\nSample recent prompts:")
            if 'timestamp' in data_df.columns and 'original_prompt' in data_df.columns:
                data_df['timestamp'] = pd.to_datetime(data_df['timestamp'], errors='coerce')
                recent_data = data_df.sort_values('timestamp', ascending=False).head(5)
                
                for i, (_, row) in enumerate(recent_data.iterrows()):
                    task_id = row.get('task_id', 'unknown')
                    user_id = row.get('user_id', 'unknown')
                    timestamp = row.get('timestamp', 'unknown')
                    prompt = row.get('original_prompt', '')
                    if isinstance(prompt, str) and prompt:
                        # Truncate and format the prompt
                        prompt_preview = textwrap.shorten(prompt, width=70, placeholder="...")
                        print(f"\n  Sample {i+1} - User {user_id}, Task {task_id}, {timestamp}")
                        print(f"  {prompt_preview}")
            
        except Exception as e:
            print(f"Error reading prompt data: {str(e)}")
    
    else:
        print("No prompt analysis data found")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="PromptDoctor Study Dashboard")
    parser.add_argument('--users', action='store_true', help='Show only user statistics')
    parser.add_argument('--tasks', action='store_true', help='Show only task statistics')
    parser.add_argument('--feedback', action='store_true', help='Show only feedback statistics')
    parser.add_argument('--surveys', action='store_true', help='Show only survey statistics')
    parser.add_argument('--prompts', action='store_true', help='Show only prompt analysis')
    args = parser.parse_args()
    
    # Check for data directory
    data_dir = check_data_directory()
    
    print_header("PROMPTDOCTOR STUDY DASHBOARD")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # If no specific reports requested, show all
    show_all = not (args.users or args.tasks or args.feedback or args.surveys or args.prompts)
    
    if show_all or args.users:
        print_user_stats(data_dir)
    
    if show_all or args.tasks:
        print_task_stats(data_dir)
    
    if show_all or args.feedback:
        print_feedback_stats(data_dir)
    
    if show_all or args.surveys:
        print_survey_stats(data_dir)
    
    if show_all or args.prompts:
        print_prompt_analysis(data_dir)
    
    print("\n" + "=" * 60)
    print(" Dashboard Complete ".center(60, "="))
    print("=" * 60)

if __name__ == "__main__":
    main()
