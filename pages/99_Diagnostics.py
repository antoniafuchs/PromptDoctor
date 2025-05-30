import streamlit as st
import sys
import os
import pandas as pd
import json
import datetime
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Any

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now import our modules
from utils.diagnostics import run_storage_diagnostics
from utils.data_storage import DataStorage
from tracking.logging import check_storage_status, enhanced_logger

def main():
    st.set_page_config(
        page_title="PromptDoctor Diagnostics",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("PromptDoctor Diagnostics")
    
    if "auth_check" not in st.session_state:
        st.session_state.auth_check = False
        st.session_state.auth_attempts = 0
    
    # Simple authentication 
    if not st.session_state.auth_check:
        st.warning("⚠️ This page is for study administrators only.")
        password = st.text_input("Enter admin password", type="password")
        
        if st.button("Login"):
            # Replace with your preferred password or authentication method
            if password == "PromptDoctorAdmin":
                st.session_state.auth_check = True
                st.rerun()
            else:
                st.session_state.auth_attempts += 1
                st.error(f"Invalid password. Attempt {st.session_state.auth_attempts} of 3")
                
                if st.session_state.auth_attempts >= 3:
                    st.error("Too many attempts. Please try again later.")
                    st.stop()
        
        st.stop()
    
    # Tabs for different diagnostic views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Dashboard", "System Status", "Data Files", "Logs", "Utilities"])
    
    with tab1:
        st.header("Study Dashboard")
        
        # Add refresh button
        if st.button("Refresh Dashboard", key="refresh_dashboard"):
            st.rerun()
            
        # Show current active users
        st.subheader("Active Users")
        
        # Get data directory
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        logins_file = os.path.join(data_dir, 'logins.csv')
        
        if os.path.exists(logins_file):
            try:
                logins_df = pd.read_csv(logins_file, sep=';')
                
                # Convert timestamps to datetime
                logins_df['timestamp'] = pd.to_datetime(logins_df['timestamp'])
                
                # Filter for recent logins
                now = pd.Timestamp.now()
                last_24h = logins_df[logins_df['timestamp'] > (now - pd.Timedelta(hours=24))]
                last_hour = logins_df[logins_df['timestamp'] > (now - pd.Timedelta(hours=1))]
                
                # Count unique users
                active_users_24h = last_24h['user_id'].nunique() if 'user_id' in last_24h.columns else 0
                active_users_1h = last_hour['user_id'].nunique() if 'user_id' in last_hour.columns else 0
                
                # Display metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_users = logins_df['user_id'].nunique() if 'user_id' in logins_df.columns else 0
                    st.metric("Total Users", total_users)
                    
                with col2:
                    st.metric("Active in Last 24 Hours", active_users_24h)
                    
                with col3:
                    st.metric("Active in Last Hour", active_users_1h)
                
                # Show user distribution by group
                if 'group' in logins_df.columns:
                    st.subheader("User Distribution by Group")
                    group_counts = logins_df.groupby('group')['user_id'].nunique().reset_index()
                    group_counts.columns = ['Group', 'Count']
                    
                    # Plot as bar chart
                    fig, ax = plt.subplots(figsize=(8, 4))
                    ax.bar(group_counts['Group'], group_counts['Count'])
                    ax.set_ylabel('Number of Users')
                    ax.set_title('Users by Group')
                    st.pyplot(fig)
                    
                    # Also show as table
                    st.dataframe(group_counts)
                
            except Exception as e:
                st.error(f"Error analyzing login data: {str(e)}")
        else:
            st.warning("No login data found")
        
        # Task Completion Stats
        st.subheader("Task Completion")
        
        tasks_file = os.path.join(data_dir, 'tasks.csv')
        if os.path.exists(tasks_file):
            try:
                tasks_df = pd.read_csv(tasks_file, sep=';')
                
                if 'task_id' in tasks_df.columns and 'completion_status' in tasks_df.columns:
                    # Count completed tasks
                    completed_tasks = tasks_df[tasks_df['completion_status'] == 'completed']
                    task_counts = completed_tasks.groupby('task_id').size().reset_index()
                    task_counts.columns = ['Task ID', 'Completions']
                    
                    # Plot as bar chart
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.bar(task_counts['Task ID'], task_counts['Completions'])
                    ax.set_xlabel('Task ID')
                    ax.set_ylabel('Number of Completions')
                    ax.set_title('Task Completions')
                    st.pyplot(fig)
                    
                    # Show average completion time
                    if 'task_duration' in tasks_df.columns:
                        tasks_df['task_duration'] = pd.to_numeric(tasks_df['task_duration'], errors='coerce')
                        avg_durations = tasks_df.groupby('task_id')['task_duration'].mean().reset_index()
                        avg_durations.columns = ['Task ID', 'Avg Duration (sec)']
                        avg_durations['Avg Duration (min)'] = avg_durations['Avg Duration (sec)'] / 60
                        
                        st.subheader("Average Task Duration")
                        st.dataframe(avg_durations)
                
            except Exception as e:
                st.error(f"Error analyzing task data: {str(e)}")
        else:
            st.warning("No task data found")
            
        # User Progress
        st.subheader("User Progress")
        
        users_file = os.path.join(data_dir, 'users.csv')
        if os.path.exists(users_file) and os.path.exists(tasks_file):
            try:
                users_df = pd.read_csv(users_file, sep=';')
                tasks_df = pd.read_csv(tasks_file, sep=';')
                
                # Count tasks completed per user
                if 'user_id' in tasks_df.columns and 'completion_status' in tasks_df.columns:
                    user_progress = tasks_df[tasks_df['completion_status'] == 'completed'].groupby('user_id').size().reset_index()
                    user_progress.columns = ['user_id', 'tasks_completed']
                    
                    # Create histogram of completion counts
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.hist(user_progress['tasks_completed'], bins=range(1, 6), alpha=0.7, align='left')
                    ax.set_xticks(range(0, 5))
                    ax.set_xlabel('Tasks Completed')
                    ax.set_ylabel('Number of Users')
                    ax.set_title('User Progress Distribution')
                    st.pyplot(fig)
                    
                    # Show completion percentages
                    total_users = users_df['user_id'].nunique() if 'user_id' in users_df.columns else len(users_df)
                    
                    completion_stats = []
                    for i in range(1, 4):  # Assuming 3 tasks
                        users_completed = len(user_progress[user_progress['tasks_completed'] >= i])
                        pct_completed = (users_completed / total_users) * 100 if total_users > 0 else 0
                        completion_stats.append({
                            'Milestone': f"Completed Task {i}+",
                            'Users': users_completed,
                            'Percentage': f"{pct_completed:.1f}%"
                        })
                    
                    st.dataframe(pd.DataFrame(completion_stats))
                    
            except Exception as e:
                st.error(f"Error analyzing user progress: {str(e)}")
        else:
            st.warning("User or task data files not found")
            
        # Feedback Analysis
        st.subheader("Feedback Analysis")
        
        interactions_file = os.path.join(data_dir, 'interactions.csv')
        if os.path.exists(interactions_file):
            try:
                # Load interactions with feedback
                interactions_df = pd.read_csv(interactions_file, sep=';')
                feedback_df = interactions_df[interactions_df['action_type'] == 'FEEDBACK']
                
                if not feedback_df.empty and 'feedback' in feedback_df.columns:
                    # Convert feedback to numeric
                    feedback_df['feedback'] = pd.to_numeric(feedback_df['feedback'], errors='coerce')
                    
                    # Calculate feedback stats
                    total_feedback = len(feedback_df)
                    positive_feedback = len(feedback_df[feedback_df['feedback'] > 0])
                    negative_feedback = len(feedback_df[feedback_df['feedback'] < 0])
                    neutral_feedback = len(feedback_df[feedback_df['feedback'] == 0])
                    
                    # Display metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Feedback", total_feedback)
                    
                    with col2:
                        positive_pct = (positive_feedback / total_feedback) * 100 if total_feedback > 0 else 0
                        st.metric("Positive Feedback", f"{positive_feedback} ({positive_pct:.1f}%)")
                    
                    with col3:
                        negative_pct = (negative_feedback / total_feedback) * 100 if total_feedback > 0 else 0
                        st.metric("Negative Feedback", f"{negative_feedback} ({negative_pct:.1f}%)")
                    
                    with col4:
                        neutral_pct = (neutral_feedback / total_feedback) * 100 if total_feedback > 0 else 0
                        st.metric("Neutral Feedback", f"{neutral_feedback} ({neutral_pct:.1f}%)")
                    
                    # Feedback by task
                    if 'task_id' in feedback_df.columns:
                        task_feedback = feedback_df.groupby('task_id')['feedback'].agg(['mean', 'count']).reset_index()
                        task_feedback.columns = ['Task ID', 'Average Rating', 'Count']
                        
                        # Plot as bar chart
                        fig, ax = plt.subplots(figsize=(10, 5))
                        bars = ax.bar(task_feedback['Task ID'], task_feedback['Average Rating'])
                        
                        # Color bars based on value
                        for i, bar in enumerate(bars):
                            if task_feedback['Average Rating'].iloc[i] > 0:
                                bar.set_color('green')
                            elif task_feedback['Average Rating'].iloc[i] < 0:
                                bar.set_color('red')
                            else:
                                bar.set_color('gray')
                        
                        ax.set_xlabel('Task ID')
                        ax.set_ylabel('Average Feedback (-1 to 1)')
                        ax.set_title('Average Feedback by Task')
                        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
                        st.pyplot(fig)
                        
                        # Show as table
                        st.dataframe(task_feedback)
            
            except Exception as e:
                st.error(f"Error analyzing feedback data: {str(e)}")
        else:
            st.warning("No interaction data found")

    with tab2:
        st.header("System Status")
        
        if st.button("Run System Diagnostics", key="run_system_diag"):
            with st.spinner("Running diagnostics..."):
                storage_status = check_storage_status()
                
                # Display basic info
                st.subheader("Storage Status")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Log Directory", 
                             "Accessible" if storage_status.get("log_dir_exists") else "Not Found",
                             "Writable" if storage_status.get("log_dir_writable") else "Not Writable")
                    
                with col2:
                    st.metric("Data Directory", 
                             "Accessible" if storage_status.get("data_dir_exists") else "Not Found",
                             "Writable" if storage_status.get("data_dir_writable") else "Not Writable")
                
                # Check key files
                st.subheader("Critical Files")
                file_results = storage_status.get("files_check", {})
                
                for filename, file_info in file_results.items():
                    exists = file_info.get("exists", False)
                    size = file_info.get("size", 0)
                    writable = file_info.get("writable", False)
                    
                    status = "✅" if exists and writable else "❌"
                    st.write(f"{status} **{filename}**: {size} bytes, {'Writable' if writable else 'Not Writable'}")
                
                # Raw JSON
                with st.expander("Raw Diagnostics Data"):
                    st.json(storage_status)

    with tab3:
        st.header("Data Files Overview")
        
        if st.button("Scan Data Files"):
            with st.spinner("Scanning data files..."):
                data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
                
                if os.path.exists(data_dir):
                    files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
                    
                    if not files:
                        st.warning("No CSV files found in data directory")
                    else:
                        st.write(f"Found {len(files)} CSV files in data directory")
                        
                        file_data = []
                        for filename in files:
                            filepath = os.path.join(data_dir, filename)
                            try:
                                file_stats = os.stat(filepath)
                                mtime = datetime.datetime.fromtimestamp(file_stats.st_mtime)
                                
                                # Try to count rows
                                try:
                                    df = pd.read_csv(filepath, sep=';')
                                    row_count = len(df)
                                except:
                                    row_count = "Error"
                                
                                file_data.append({
                                    "Filename": filename,
                                    "Size (KB)": round(file_stats.st_size / 1024, 2),
                                    "Last Modified": mtime.strftime("%Y-%m-%d %H:%M:%S"),
                                    "Row Count": row_count
                                })
                            except Exception as e:
                                file_data.append({
                                    "Filename": filename,
                                    "Size (KB)": "Error",
                                    "Last Modified": "Error",
                                    "Row Count": f"Error: {str(e)}"
                                })
                        
                        # Display as dataframe
                        st.dataframe(pd.DataFrame(file_data))
                        
                        # Sample data viewer
                        st.subheader("View Sample Data")
                        selected_file = st.selectbox("Select file to view", files)
                        
                        if selected_file:
                            try:
                                df = pd.read_csv(os.path.join(data_dir, selected_file), sep=';')
                                row_count = len(df)
                                
                                st.write(f"Showing up to 10 rows from {row_count} total rows")
                                st.dataframe(df.tail(10))
                            except Exception as e:
                                st.error(f"Error reading file: {str(e)}")
                else:
                    st.error(f"Data directory not found: {data_dir}")

    with tab4:
        st.header("Diagnostic Utilities")
        
        st.subheader("Run Full Diagnostics")
        if st.button("Generate Full Diagnostic Report"):
            with st.spinner("Running comprehensive diagnostics..."):
                results = run_storage_diagnostics()
                
                # Save diagnostics to file
                try:
                    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
                    os.makedirs(log_dir, exist_ok=True)
                    
                    diagnostic_file = os.path.join(log_dir, f"diagnostics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                    with open(diagnostic_file, 'w') as f:
                        json.dump(results, f, indent=2)
                    
                    st.success(f"Full diagnostic report saved to {diagnostic_file}")
                except Exception as e:
                    st.error(f"Failed to save diagnostic report: {str(e)}")
                
                # Display summary
                st.json(results)
        
        st.subheader("Test Database Write")
        if st.button("Test Write Operation"):
            try:
                storage = DataStorage()
                test_data = {
                    "user_id": "test_user",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "test_field": "This is a test entry",
                    "source": "diagnostics_page"
                }
                
                # Test writing to interactions
                storage.log_interaction({
                    "user_id": "test_user",
                    "task_id": 0,
                    "action_type": "TEST_WRITE",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "original_prompt": "This is a test prompt",
                    "model_response": "This is a test response",
                    "message_id": f"test_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                })
                
                st.success("Test write completed successfully!")
            except Exception as e:
                st.error(f"Test write failed: {str(e)}")

# Add a check to make sure the page is correctly accessed
if __name__ == "__main__":
    print("Starting diagnostics page...")
    try:
        main()
    except Exception as e:
        st.error(f"Error running diagnostics: {str(e)}")
        st.code(traceback.format_exc())
def render_feedback_analysis_tab():
    """Render a dedicated feedback analysis tab in the diagnostics page"""
    st.header("Feedback Analysis")
    
    # Import the feedback collector
    try:
        from utils.feedback_collector import FeedbackCollector
        collector = FeedbackCollector()
    except ImportError:
        st.error("FeedbackCollector module not found. Please create it first.")
        return
    
    # Get feedback summary
    summary = collector.generate_feedback_summary()
    
    if "error" in summary:
        st.error(f"Error loading feedback data: {summary['error']}")
        return
    
    # Display overall metrics
    st.subheader("Overall Feedback Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Entries", summary["total_entries"])
    
    with col2:
        positive_text = f"{summary['positive_feedback']} ({summary['positive_percentage']}%)"
        st.metric("Positive Feedback", positive_text)
    
    with col3:
        negative_text = f"{summary['negative_feedback']} ({summary['negative_percentage']}%)"
        st.metric("Negative Feedback", negative_text)
    
    with col4:
        neutral_text = f"{summary['neutral_feedback']} ({summary['neutral_percentage']}%)"
        st.metric("Neutral Feedback", neutral_text)
    
    # Display feedback by task
    if "feedback_by_task" in summary and summary["feedback_by_task"]:
        st.subheader("Feedback by Task")
        
        # Convert to DataFrame for better display
        task_data = []
        for task_id, stats in summary["feedback_by_task"].items():
            task_data.append({
                "Task": task_id,
                "Count": stats["count"],
                "Average Rating": stats["average_rating"]
            })
        
        task_df = pd.DataFrame(task_data)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.dataframe(task_df, use_container_width=True)
        
        with col2:
            if len(task_data) > 0:
                # Create bar chart
                fig, ax = plt.subplots(figsize=(10, 6))
                bars = ax.bar(task_df["Task"].astype(str), task_df["Average Rating"])
                
                # Color bars based on values
                for i, bar in enumerate(bars):
                    value = task_df["Average Rating"].iloc[i]
                    if value > 0:
                        bar.set_color('green')
                    elif value < 0:
                        bar.set_color('red')
                    else:
                        bar.set_color('gray')
                
                ax.set_xlabel('Task')
                ax.set_ylabel('Average Rating')
                ax.set_title('Average Feedback by Task')
                
                # Add value labels
                for bar in bars:
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height,
                        f'{height:.2f}',
                        ha='center',
                        va='bottom'
                    )
                
                st.pyplot(fig)
    
    # Option to export feedback data
    st.subheader("Export Feedback Data")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        export_format = st.selectbox(
            "Export Format",
            options=["CSV", "JSON", "Excel"],
            index=0
        )
    
    with col2:
        if st.button("Export Feedback Data", type="primary"):
            export_path = collector.export_feedback_report(format=export_format.lower())
            if export_path:
                st.success(f"Feedback data exported to: {export_path}")
                
                # If the file is small enough, offer download
                if os.path.getsize(export_path) < 200 * 1024 * 1024:  # 200MB limit
                    with open(export_path, "rb") as file:
                        file_data = file.read()
                    
                    st.download_button(
                        label="Download File",
                        data=file_data,
                        file_name=os.path.basename(export_path),
                        mime="application/octet-stream"
                    )
            else:
                st.error("Failed to export feedback data.")
    
    # Raw feedback data
    st.subheader("Raw Feedback Data")
    
    # Get all feedback data
    feedback_df = collector.collect_all_feedback()
    
    if not feedback_df.empty:
        # Determine which column contains feedback values
        feedback_col = None
        for col in ['feedback_value', 'feedback']:
            if col in feedback_df.columns:
                feedback_col = col
                break
        
        # Show the raw data
        st.dataframe(feedback_df, use_container_width=True)
        
        # Interactive analysis tools
        st.subheader("Analysis Tools")
        
        # Filter by task_id if available
        if 'task_id' in feedback_df.columns:
            task_ids = ['All'] + sorted(feedback_df['task_id'].unique().tolist())
            selected_task = st.selectbox("Filter by Task ID", options=task_ids)
            
            if selected_task != 'All':
                feedback_df = feedback_df[feedback_df['task_id'] == selected_task]
        
        # Show stats for filtered data
        if feedback_col and not feedback_df.empty:
            try:
                feedback_df[feedback_col] = pd.to_numeric(feedback_df[feedback_col], errors='coerce')
                
                st.write("#### Feedback Distribution")
                
                # Calculate feedback distribution
                positive = len(feedback_df[feedback_df[feedback_col] > 0])
                negative = len(feedback_df[feedback_df[feedback_col] < 0])
                neutral = len(feedback_df[feedback_df[feedback_col] == 0])
                
                # Create a pie chart
                fig, ax = plt.subplots()
                sizes = [positive, neutral, negative]
                labels = ['Positive', 'Neutral', 'Negative']
                colors = ['green', 'gray', 'red']
                
                ax.pie(
                    sizes, 
                    labels=labels, 
                    colors=colors,
                    autopct='%1.1f%%',
                    startangle=90
                )
                ax.axis('equal')
                
                st.pyplot(fig)
            except Exception as e:
                st.error(f"Error analyzing feedback data: {str(e)}")
    else:
        st.info("No feedback data available.")

# Add this to the main function where tabs are defined
# tabs = st.tabs(["System Status", "User Progress", "Task Metrics", "Feedback Analysis"])
# tab1, tab2, tab3, tab4 = tabs
# with tab4:
#     render_feedback_analysis_tab()
