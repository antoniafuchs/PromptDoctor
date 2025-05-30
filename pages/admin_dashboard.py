"""
Admin Dashboard - Hidden monitoring page for study owners

This page is intentionally named without a number prefix to hide it from the sidebar.
It can be accessed directly via URL: http://localhost:8501/admin_dashboard
"""
import streamlit as st
import sys
import os
import pandas as pd
import json
import datetime
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Any
import traceback
import time

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import project modules
from utils.data_storage import DataStorage
from tracking.logging import check_storage_status

# Password for admin access - you can change this to something more secure
ADMIN_PASSWORD = "PromptDoctorAdmin"

# Set page config
st.set_page_config(
    page_title="PromptDoctor Admin",
    page_icon="🔒",
    layout="wide"
)

# Custom CSS to hide the page from sidebar and for admin styling
st.markdown("""
<style>
    /* Hide this page from sidebar navigation */
    [data-testid="stSidebarNavItems"] a:has(div:contains("admin_dashboard")) {
        display: none;
    }
    
    /* Admin dashboard styling */
    .admin-header {
        background-color: #1E3A8A;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    
    .metric-card {
        background-color: white;
        border-radius: 5px;
        padding: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        text-align: center;
    }
    
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        color: #1E3A8A;
    }
    
    .metric-label {
        font-size: 14px;
        color: #6B7280;
    }
    
    /* Table styling */
    .dataframe {
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

def authenticate():
    """Handle admin authentication"""
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
        st.session_state.login_attempts = 0
    
    if not st.session_state.admin_authenticated:
        st.markdown("""
        <div class="admin-header">
            <h1>PromptDoctor Admin Dashboard</h1>
            <p>This page is restricted to study administrators only.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Password form
        with st.form("admin_login"):
            password = st.text_input("Enter admin password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if password == ADMIN_PASSWORD:
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    st.error(f"Invalid password. Attempt {st.session_state.login_attempts} of 3")
                    
                    if st.session_state.login_attempts >= 3:
                        st.error("Too many failed attempts. Please try again later.")
                        time.sleep(3)  # Delay to discourage brute force attempts
                        st.session_state.login_attempts = 0
        
        st.markdown("Need access? Contact the study administrator.")
        return False
    return True

def load_data():
    """Load and cache study data from CSV files"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    
    # Return object to store all data
    data = {
        "data_dir": data_dir,
        "users": None,
        "tasks": None,
        "interactions": None,
        "surveys": None,
        "feedback": None,
        "logins": None,
        "last_updated": datetime.datetime.now()
    }
    
    # Load all CSV files if they exist
    files_to_load = {
        "users": "users.csv",
        "tasks": "tasks.csv",
        "interactions": "interactions.csv",
        "surveys": "surveys.csv",
        "feedback": "feedback.csv",
        "logins": "logins.csv"
    }
    
    for key, filename in files_to_load.items():
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath, sep=';')
                # Convert timestamps to datetime
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                data[key] = df
            except Exception as e:
                st.warning(f"Error loading {filename}: {str(e)}")
    
    return data

def render_dashboard(data):
    """Render the main admin dashboard"""
    st.markdown("""
    <div class="admin-header">
        <h1>PromptDoctor Admin Dashboard</h1>
        <p>Real-time monitoring of study progress and data collection</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Add refresh button at the top
    col_refresh, col_last_updated = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    with col_last_updated:
        st.markdown(f"Last updated: {data['last_updated'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Overview", "Users", "Tasks", "Prompts", "Feedback", "Data Explorer"
    ])
    
    # Overview Tab
    with tab1:
        render_overview_tab(data)
    
    # Users Tab
    with tab2:
        render_users_tab(data)
    
    # Tasks Tab
    with tab3:
        render_tasks_tab(data)
    
    # Prompts Tab
    with tab4:
        render_prompts_tab(data)
    
    # Feedback Tab
    with tab5:
        render_feedback_tab(data)
    
    # Data Explorer Tab
    with tab6:
        render_data_explorer_tab(data)

def render_overview_tab(data):
    """Render overview dashboard with key metrics"""
    st.header("Study Overview")
    
    # Calculate key metrics
    total_users = len(data["users"]) if data["users"] is not None else 0
    
    # Check if tasks data exists and has the required columns
    completed_tasks = 0
    if data["tasks"] is not None:
        if "completion_status" in data["tasks"].columns:
            completed_tasks = len(data["tasks"][data["tasks"]["completion_status"] == "completed"])
        elif "status" in data["tasks"].columns:
            # Try alternative column name
            completed_tasks = len(data["tasks"][data["tasks"]["status"] == "completed"])
        else:
            st.warning("⚠️ Tasks data doesn't have completion status information")
    
    total_interactions = len(data["interactions"]) if data["interactions"] is not None else 0
    total_surveys = len(data["surveys"]) if data["surveys"] is not None else 0
    
    # Active users in last 24 hours
    active_users_24h = 0
    if data["logins"] is not None:
        now = pd.Timestamp.now()
        active_users_24h = data["logins"][data["logins"]["timestamp"] > (now - pd.Timedelta(hours=24))]["user_id"].nunique()
    
    # Create metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">{}</div>
            <div class="metric-label">Total Users</div>
        </div>
        """.format(total_users), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">{}</div>
            <div class="metric-label">Active Users (24h)</div>
        </div>
        """.format(active_users_24h), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">{}</div>
            <div class="metric-label">Completed Tasks</div>
        </div>
        """.format(completed_tasks), unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">{}</div>
            <div class="metric-label">Interactions</div>
        </div>
        """.format(total_interactions), unsafe_allow_html=True)
    
    with col5:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">{}</div>
            <div class="metric-label">Survey Responses</div>
        </div>
        """.format(total_surveys), unsafe_allow_html=True)
    
    # Group distribution
    st.subheader("User Distribution by Group")
    if data["users"] is not None and "group" in data["users"].columns:
        col1, col2 = st.columns([2, 3])
        
        with col1:
            group_counts = data["users"].groupby("group").size().reset_index()
            group_counts.columns = ["Group", "Count"]
            st.dataframe(group_counts, use_container_width=True)
        
        with col2:
            # Create a bar chart
            fig, ax = plt.subplots(figsize=(8, 4))
            bars = ax.bar(group_counts["Group"], group_counts["Count"])
            
            # Add data labels on top of bars
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom')
            
            ax.set_title("Users by Group")
            ax.set_ylabel("Number of Users")
            st.pyplot(fig)
    else:
        st.info("No group data available")
    
    # Task completion over time
    st.subheader("Task Completion Over Time")
    if data["tasks"] is not None and "timestamp" in data["tasks"].columns:
        # Convert to datetime if not already
        data["tasks"]["timestamp"] = pd.to_datetime(data["tasks"]["timestamp"], errors="coerce")
        
        # Get completed tasks
        completed_tasks = data["tasks"][data["tasks"]["completion_status"] == "completed"].copy()
        
        if not completed_tasks.empty:
            # Group by date
            completed_tasks["date"] = completed_tasks["timestamp"].dt.date
            daily_completions = completed_tasks.groupby("date").size().reset_index()
            daily_completions.columns = ["Date", "Completions"]
            
            # Plot
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(daily_completions["Date"], daily_completions["Completions"], marker='o')
            ax.set_title("Task Completions by Date")
            ax.set_xlabel("Date")
            ax.set_ylabel("Number of Completions")
            fig.autofmt_xdate()  # Rotate date labels
            st.pyplot(fig)
        else:
            st.info("No completed tasks data available")
    else:
        st.info("No task timestamp data available")
    
    # Recent Activity
    st.subheader("Recent Activity")
    if data["logins"] is not None:
        recent_logins = data["logins"].sort_values("timestamp", ascending=False).head(10)
        recent_logins = recent_logins[["timestamp", "user_id", "group", "model_type", "model_name"]]
        st.dataframe(recent_logins, use_container_width=True)
    else:
        st.info("No recent login data available")

def render_users_tab(data):
    """Render user statistics and details"""
    st.header("User Management & Statistics")
    
    # User Search Box
    user_search = st.text_input("Search users by ID or group:", placeholder="Enter user ID or group name...")
    
    if data["users"] is not None:
        # Create a filtered dataframe based on search
        filtered_users = data["users"]
        if user_search:
            filtered_users = filtered_users[
                filtered_users["user_id"].astype(str).str.contains(user_search, case=False) |
                filtered_users["group"].astype(str).str.contains(user_search, case=False)
            ]
        
        # Display user table
        st.dataframe(filtered_users, use_container_width=True)
        
        # User activity by group
        st.subheader("User Activity by Group")
        if data["logins"] is not None and "group" in data["logins"].columns:
            # Convert timestamp to datetime if needed
            if not pd.api.types.is_datetime64_any_dtype(data["logins"]["timestamp"]):
                data["logins"]["timestamp"] = pd.to_datetime(data["logins"]["timestamp"], errors="coerce")
            
            # Calculate timeframes
            now = pd.Timestamp.now()
            data["logins"]["days_ago"] = (now - data["logins"]["timestamp"]).dt.days
            
            # Group by time windows
            time_windows = {
                "Last 24 hours": data["logins"][data["logins"]["timestamp"] > (now - pd.Timedelta(hours=24))],
                "Last 7 days": data["logins"][data["logins"]["timestamp"] > (now - pd.Timedelta(days=7))],
                "Last 30 days": data["logins"][data["logins"]["timestamp"] > (now - pd.Timedelta(days=30))],
                "All time": data["logins"]
            }
            
            # Create activity table
            activity_data = []
            for window, df in time_windows.items():
                if not df.empty and "group" in df.columns:
                    group_counts = df.groupby("group")["user_id"].nunique().reset_index()
                    group_counts.columns = ["Group", "Active Users"]
                    group_counts["Time Period"] = window
                    activity_data.append(group_counts)
            
            if activity_data:
                activity_df = pd.concat(activity_data)
                activity_pivot = activity_df.pivot(index="Group", columns="Time Period", values="Active Users").fillna(0).astype(int)
                st.dataframe(activity_pivot, use_container_width=True)
        
        # User Demographics (if available)
        if "age" in data["users"].columns or "gender" in data["users"].columns:
            st.subheader("User Demographics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Age distribution
                if "age" in data["users"].columns:
                    # Count users by age group
                    age_data = data["users"]["age"].value_counts().sort_index()
                    if not age_data.empty:
                        fig, ax = plt.subplots()
                        ax.bar(age_data.index.astype(str), age_data.values)
                        ax.set_title("Age Distribution")
                        ax.set_xlabel("Age")
                        ax.set_ylabel("Count")
                        st.pyplot(fig)
            
            with col2:
                # Gender distribution
                if "gender" in data["users"].columns:
                    gender_data = data["users"]["gender"].value_counts()
                    if not gender_data.empty:
                        fig, ax = plt.subplots()
                        ax.pie(gender_data.values, labels=gender_data.index, autopct='%1.1f%%')
                        ax.set_title("Gender Distribution")
                        st.pyplot(fig)
    else:
        st.info("No user data available")

def render_prompts_tab(data):
    """Render prompt analysis and verification"""
    st.header("Prompt Analysis")
    
    # Try to load prompt data from various sources
    prompt_sources = {
        "prompt_metrics.csv": None,
        "prompt_counts.csv": None,
        "prompt_data.csv": None,
        "interactions.csv": None
    }
    
    # Load all available prompt data files
    for filename, _ in prompt_sources.items():
        filepath = os.path.join(data["data_dir"], filename)
        if os.path.exists(filepath):
            try:
                prompt_sources[filename] = pd.read_csv(filepath, sep=';')
                st.success(f"✅ Successfully loaded {filename}")
            except Exception as e:
                st.warning(f"⚠️ Error loading {filename}: {str(e)}")
    
    # Check if we have any data to work with
    if all(source is None for source in prompt_sources.values()):
        st.error("No prompt data sources found. Please check that your data files exist.")
        return
    
    # Start with prompt_metrics.csv which contains the most comprehensive prompt data
    if prompt_sources["prompt_metrics.csv"] is not None:
        prompt_metrics_df = prompt_sources["prompt_metrics.csv"]
        
        st.subheader("Prompt Metrics Overview")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_prompts = len(prompt_metrics_df)
            st.metric("Total Prompt Records", f"{total_prompts:,}")
            
        with col2:
            users_with_prompts = prompt_metrics_df["user_id"].nunique()
            st.metric("Unique Users", f"{users_with_prompts:,}")
            
        with col3:
            tasks_with_prompts = prompt_metrics_df["task_id"].nunique()
            st.metric("Tasks Covered", f"{tasks_with_prompts:,}")
        
        # Show prompt evolution metrics
        st.subheader("Prompt Evolution Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Calculate average Levenshtein distance for prompt evolution
            avg_edit_distance = prompt_metrics_df["levenshtein_distance"].mean()
            
            # Calculate distribution of edit distances
            if len(prompt_metrics_df) > 0:
                unchanged = len(prompt_metrics_df[prompt_metrics_df["levenshtein_distance"] == 0])
                minor_edits = len(prompt_metrics_df[(prompt_metrics_df["levenshtein_distance"] > 0) & 
                                                  (prompt_metrics_df["levenshtein_distance"] < 0.5)])
                major_edits = len(prompt_metrics_df[prompt_metrics_df["levenshtein_distance"] >= 0.5])
                
                edit_stats = pd.DataFrame({
                    "Edit Type": ["Unchanged", "Minor Changes", "Major Changes"],
                    "Count": [unchanged, minor_edits, major_edits],
                    "Percentage": [
                        f"{(unchanged/total_prompts)*100:.1f}%", 
                        f"{(minor_edits/total_prompts)*100:.1f}%", 
                        f"{(major_edits/total_prompts)*100:.1f}%"
                    ]
                })
                
                st.dataframe(edit_stats, use_container_width=True)
            
        with col2:
            # Create histogram of Levenshtein distances
            if len(prompt_metrics_df) > 0:
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.hist(prompt_metrics_df["levenshtein_distance"], bins=20, 
                      color="skyblue", edgecolor="black", alpha=0.7)
                ax.set_title("Distribution of Prompt Evolution (Levenshtein Distance)")
                ax.set_xlabel("Normalized Levenshtein Distance")
                ax.set_ylabel("Frequency")
                ax.axvline(x=avg_edit_distance, color='red', linestyle='--', 
                         label=f'Mean = {avg_edit_distance:.2f}')
                ax.legend()
                st.pyplot(fig)
        
        # Prompt length distribution
        st.subheader("Prompt Length Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Statistics on word count
            word_count_stats = {
                "Average Words": f"{prompt_metrics_df['word_count'].mean():.1f}",
                "Median Words": f"{prompt_metrics_df['word_count'].median():.1f}",
                "Min Words": f"{prompt_metrics_df['word_count'].min()}",
                "Max Words": f"{prompt_metrics_df['word_count'].max()}"
            }
            
            stats_df = pd.DataFrame(list(word_count_stats.items()), 
                                  columns=["Metric", "Value"])
            st.dataframe(stats_df, use_container_width=True)
            
        with col2:
            # Create histogram of word counts
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.hist(prompt_metrics_df["word_count"], bins=20, 
                  color="lightgreen", edgecolor="black", alpha=0.7)
            ax.set_title("Distribution of Prompt Lengths")
            ax.set_xlabel("Word Count")
            ax.set_ylabel("Frequency")
            st.pyplot(fig)
        
        # Prompt text explorer
        st.subheader("Prompt Content Explorer")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # User filter
            user_ids = ["All Users"] + sorted(prompt_metrics_df["user_id"].unique().tolist())
            selected_user = st.selectbox("Filter by User ID", user_ids)
            
        with col2:
            # Task filter
            task_ids = ["All Tasks"] + sorted(prompt_metrics_df["task_id"].unique().tolist())
            selected_task = st.selectbox("Filter by Task ID", task_ids)
            
        with col3:
            # Group filter
            groups = ["All Groups"] + sorted(prompt_metrics_df["group"].unique().tolist())
            selected_group = st.selectbox("Filter by Group", groups)
        
        # Apply filters
        filtered_df = prompt_metrics_df.copy()
        
        if selected_user != "All Users":
            filtered_df = filtered_df[filtered_df["user_id"] == selected_user]
            
        if selected_task != "All Tasks":
            filtered_df = filtered_df[filtered_df["task_id"] == selected_task]
            
        if selected_group != "All Groups":
            filtered_df = filtered_df[filtered_df["group"] == selected_group]
        
        # Search in prompts
        search_term = st.text_input("Search in prompts:", placeholder="Enter keywords to search in prompt text...")
        
        if search_term:
            # Search in both first and last prompt
            first_prompt_match = filtered_df["first_prompt"].astype(str).str.contains(search_term, case=False, na=False)
            last_prompt_match = filtered_df["last_prompt"].astype(str).str.contains(search_term, case=False, na=False)
            filtered_df = filtered_df[first_prompt_match | last_prompt_match]
        
        # Show filtered data
        if not filtered_df.empty:
            st.write(f"Showing {len(filtered_df)} prompt records")
            
            # Select what to display
            display_options = st.multiselect(
                "Select columns to display:",
                options=["user_id", "task_id", "group", "prompt_count", "word_count", 
                        "first_prompt", "last_prompt", "levenshtein_distance", "timestamp"],
                default=["user_id", "task_id", "group", "prompt_count", "word_count"]
            )
            
            if display_options:
                st.dataframe(filtered_df[display_options], use_container_width=True)
            
            # Prompt detail view
            st.subheader("Prompt Evolution Detail")
            
            if len(filtered_df) > 0:
                selected_row_idx = st.selectbox(
                    "Select a prompt record to examine:",
                    range(len(filtered_df)),
                    format_func=lambda x: f"User: {filtered_df.iloc[x]['user_id']} - Task: {filtered_df.iloc[x]['task_id']} - Prompts: {filtered_df.iloc[x]['prompt_count']}"
                )
                
                selected_row = filtered_df.iloc[selected_row_idx]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("First Prompt")
                    # Add a unique key to this text_area
                    st.text_area("", selected_row["first_prompt"], height=200, key=f"first_prompt_{selected_row_idx}")
                    st.info(f"Word count: {len(str(selected_row['first_prompt']).split())}")
                
                with col2:
                    st.subheader("Last Prompt")
                    # Add a unique key to this text_area
                    st.text_area("", selected_row["last_prompt"], height=200, key=f"last_prompt_{selected_row_idx}")
                    st.info(f"Word count: {len(str(selected_row['last_prompt']).split())}")
                
                # Show diff if prompts are different
                if selected_row["first_prompt"] != selected_row["last_prompt"]:
                    st.subheader("Differences")
                    
                    # Calculate a simple diff
                    first_words = str(selected_row["first_prompt"]).split()
                    last_words = str(selected_row["last_prompt"]).split()
                    
                    if len(first_words) > 0 and len(last_words) > 0:
                        try:
                            import difflib
                            diff = difflib.ndiff(first_words, last_words)
                            diff_html = ""
                            
                            for line in diff:
                                if line.startswith('+ '):
                                    diff_html += f'<span style="background-color: #CCFFCC">{line[2:]}</span> '
                                elif line.startswith('- '):
                                    diff_html += f'<span style="background-color: #FFCCCC">{line[2:]}</span> '
                                elif line.startswith('  '):
                                    diff_html += f'{line[2:]} '
                            
                            st.markdown(f'<div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px;">{diff_html}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.warning(f"Could not generate diff: {str(e)}")
                
                # Show metadata
                st.subheader("Prompt Metadata")
                metadata_df = pd.DataFrame({
                    "Metric": ["User ID", "Task ID", "Group", "Prompt Count", "Word Count", 
                              "Levenshtein Distance", "Timestamp"],
                    "Value": [
                        selected_row["user_id"],
                        selected_row["task_id"],
                        selected_row["group"],
                        selected_row["prompt_count"],
                        selected_row["word_count"],
                        f"{selected_row['levenshtein_distance']:.4f}",
                        selected_row["timestamp"]
                    ]
                })
                st.dataframe(metadata_df, use_container_width=True)
        else:
            st.info("No prompt records match your filter criteria.")
    
    # If we don't have prompt_metrics.csv, check prompt_data.csv
    elif prompt_sources["prompt_data.csv"] is not None:
        prompt_data_df = prompt_sources["prompt_data.csv"]
        
        st.subheader("Prompt Data Analysis")
        
        # Filter to rows with prompts
        prompt_data_df = prompt_data_df.dropna(subset=["original_prompt"])
        
        if not prompt_data_df.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_prompts = len(prompt_data_df)
                st.metric("Total Prompt Records", f"{total_prompts:,}")
                
            with col2:
                users_with_prompts = prompt_data_df["user_id"].nunique()
                st.metric("Unique Users", f"{users_with_prompts:,}")
                
            with col3:
                tasks_with_prompts = prompt_data_df["task_id"].nunique()
                st.metric("Tasks Covered", f"{tasks_with_prompts:,}")
            
            # Show the prompt data
            st.subheader("Prompt Records")
            
            # Filter options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # User filter
                user_ids = ["All Users"] + sorted(prompt_data_df["user_id"].unique().tolist())
                selected_user = st.selectbox("Filter by User ID", user_ids)
                
            with col2:
                # Task filter
                task_ids = ["All Tasks"] + sorted(prompt_data_df["task_id"].unique().tolist())
                selected_task = st.selectbox("Filter by Task ID", task_ids)
                
            with col3:
                # Action filter if available
                if "event_type" in prompt_data_df.columns:
                    actions = ["All Actions"] + sorted(prompt_data_df["event_type"].unique().tolist())
                    selected_action = st.selectbox("Filter by Action", actions)
                else:
                    selected_action = "All Actions"
            
            # Apply filters
            filtered_df = prompt_data_df.copy()
            
            if selected_user != "All Users":
                filtered_df = filtered_df[filtered_df["user_id"] == selected_user]
                
            if selected_task != "All Tasks":
                filtered_df = filtered_df[filtered_df["task_id"] == selected_task]
                
            if selected_action != "All Actions" and "event_type" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["event_type"] == selected_action]
            
            # Search in prompts
            search_term = st.text_input("Search in prompt data:", placeholder="Enter keywords to search...")
            
            if search_term:
                # Search across all text columns
                text_columns = ["original_prompt", "modified_prompt", "highlighted_terms", "last_prompt"]
                mask = pd.Series(False, index=filtered_df.index)
                
                for col in text_columns:
                    if col in filtered_df.columns:
                        mask = mask | filtered_df[col].astype(str).str.contains(search_term, case=False, na=False)
                
                filtered_df = filtered_df[mask]
            
            # Show filtered data
            if not filtered_df.empty:
                st.write(f"Showing {len(filtered_df)} prompt records")
                
                # Show the dataframe
                columns_to_show = ["user_id", "task_id", "timestamp"]
                
                # Add the most important prompt columns based on availability
                for col in ["original_prompt", "modified_prompt", "last_prompt", "highlighted_terms", "medical_term_count"]:
                    if col in filtered_df.columns:
                        columns_to_show.append(col)
                
                st.dataframe(filtered_df[columns_to_show], use_container_width=True)
                
                # Prompt detail view
                st.subheader("Prompt Detail")
                
                selected_row_idx = st.selectbox(
                    "Select a prompt to examine:",
                    range(len(filtered_df)),
                    format_func=lambda x: f"User: {filtered_df.iloc[x]['user_id']} - Task: {filtered_df.iloc[x]['task_id']} - {filtered_df.iloc[x]['timestamp']}"
                )
                
                selected_row = filtered_df.iloc[selected_row_idx]
                
                # Show prompt details
                prompt_col_name = None
                for col in ["original_prompt", "last_prompt", "modified_prompt"]:
                    if col in selected_row and pd.notna(selected_row[col]) and selected_row[col]:
                        prompt_col_name = col
                        break
                
                if prompt_col_name:
                    # Add a unique key to this text_area
                    st.text_area("Prompt Content", selected_row[prompt_col_name], height=200, key=f"prompt_detail_{selected_row_idx}")
                    
                    # Show highlighted terms if available
                    if "highlighted_terms" in selected_row and pd.notna(selected_row["highlighted_terms"]) and selected_row["highlighted_terms"]:
                        st.subheader("Highlighted Medical Terms")
                        terms = selected_row["highlighted_terms"].split(",") if isinstance(selected_row["highlighted_terms"], str) else []
                        
                        if terms:
                            st.write(", ".join([f"`{term.strip()}`" for term in terms]))
                            st.info(f"Number of medical terms: {len(terms)}")
                
                # Show metadata
                st.subheader("Metadata")
                metadata_cols = [col for col in selected_row.index if col not in ["original_prompt", "modified_prompt", "last_prompt", "highlighted_terms"]]
                metadata_df = pd.DataFrame({
                    "Metadata": metadata_cols,
                    "Value": [selected_row[col] for col in metadata_cols]
                })
                st.dataframe(metadata_df, use_container_width=True)
            else:
                st.info("No prompt records match your filter criteria.")
    
    # If we have prompt_counts.csv but not the others, use that
    elif prompt_sources["prompt_counts.csv"] is not None:
        prompt_counts_df = prompt_sources["prompt_counts.csv"]
        
        st.subheader("Prompt Counts Analysis")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_users = prompt_counts_df["user_id"].nunique()
            st.metric("Total Users", f"{total_users:,}")
            
        with col2:
            total_tasks = prompt_counts_df["task_id"].nunique()
            st.metric("Total Tasks", f"{total_tasks:,}")
            
        with col3:
            avg_prompts = prompt_counts_df["prompt_count"].mean()
            st.metric("Avg Prompts/Task", f"{avg_prompts:.2f}")
        
        # Group by analysis
        st.subheader("Prompt Counts by Group")
        
        if "group" in prompt_counts_df.columns:
            group_counts = prompt_counts_df.groupby("group")["prompt_count"].agg(["mean", "median", "sum", "count"]).reset_index()
            group_counts.columns = ["Group", "Mean Prompts", "Median Prompts", "Total Prompts", "Number of Tasks"]
            group_counts["Mean Prompts"] = group_counts["Mean Prompts"].round(2)
            group_counts["Median Prompts"] = group_counts["Median Prompts"].round(2)
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.dataframe(group_counts, use_container_width=True)
                
            with col2:
                # Create chart comparing groups
                fig, ax = plt.subplots(figsize=(10, 6))
                bar_width = 0.35
                x = np.arange(len(group_counts))
                
                bars1 = ax.bar(x - bar_width/2, group_counts["Mean Prompts"], bar_width, label="Mean Prompts", color="skyblue")
                bars2 = ax.bar(x + bar_width/2, group_counts["Median Prompts"], bar_width, label="Median Prompts", color="lightgreen")
                
                # Add value labels
                for bar in bars1:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.05, f'{height:.2f}', 
                          ha='center', va='bottom')
                
                for bar in bars2:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.05, f'{height:.2f}', 
                          ha='center', va='bottom')
                
                ax.set_xlabel("Group")
                ax.set_ylabel("Number of Prompts")
                ax.set_title("Prompt Counts by Group")
                ax.set_xticks(x)
                ax.set_xticklabels(group_counts["Group"])
                ax.legend()
                
                st.pyplot(fig)
        
        # Task analysis
        st.subheader("Prompt Counts by Task")
        
        task_counts = prompt_counts_df.groupby("task_id")["prompt_count"].agg(["mean", "median", "sum", "count"]).reset_index()
        task_counts.columns = ["Task ID", "Mean Prompts", "Median Prompts", "Total Prompts", "Number of Users"]
        task_counts["Mean Prompts"] = task_counts["Mean Prompts"].round(2)
        task_counts["Median Prompts"] = task_counts["Median Prompts"].round(2)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.dataframe(task_counts, use_container_width=True)
            
        with col2:
            # Create chart comparing tasks
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(task_counts["Task ID"].astype(str), task_counts["Mean Prompts"], color="lightblue")
            
            # Add value labels
            for i, v in enumerate(task_counts["Mean Prompts"]):
                ax.text(i, v + 0.05, f"{v:.2f}", ha='center')
            
            ax.set_xlabel("Task ID")
            ax.set_ylabel("Average Prompts")
            ax.set_title("Average Prompt Count by Task")
            
            st.pyplot(fig)
        
        # Show the raw data
        st.subheader("Raw Prompt Count Data")
        st.dataframe(prompt_counts_df, use_container_width=True)
    
    # Last resort: Check interactions.csv for any prompt-related data
    elif prompt_sources["interactions.csv"] is not None:
        interactions_df = prompt_sources["interactions.csv"]
        
        st.subheader("Interaction Data Analysis")
        st.info("No dedicated prompt files found. Attempting to extract prompt data from interactions.csv")
        
        # Look for columns that might contain prompts
        prompt_columns = []
        for col in interactions_df.columns:
            if any(keyword in col.lower() for keyword in ["prompt", "message", "text", "input", "query"]):
                prompt_columns.append(col)
        
        if prompt_columns:
            st.success(f"Found potential prompt columns: {', '.join(prompt_columns)}")
            
            # Look for action types that might be related to prompts
            action_types = []
            if "action_type" in interactions_df.columns:
                # Find all action types that might be related to prompts
                for action in interactions_df["action_type"].unique():
                    if action and any(keyword in str(action).lower() for keyword in ["prompt", "message", "query", "chat", "input"]):
                        action_types.append(action)
            
            if action_types:
                st.success(f"Found potential prompt-related actions: {', '.join(action_types)}")
                
                # Filter to prompt-related actions
                prompt_df = interactions_df[interactions_df["action_type"].isin(action_types)]
                
                if not prompt_df.empty:
                    # Display summary
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        total_prompts = len(prompt_df)
                        st.metric("Total Interactions", f"{total_prompts:,}")
                        
                    with col2:
                        users_with_prompts = prompt_df["user_id"].nunique()
                        st.metric("Unique Users", f"{users_with_prompts:,}")
                        
                    with col3:
                        if "task_id" in prompt_df.columns:
                            tasks_with_prompts = prompt_df["task_id"].nunique()
                            st.metric("Tasks Covered", f"{tasks_with_prompts:,}")
                    
                    # Sample the data
                    st.subheader("Sample Interaction Data")
                    
                    # Choose columns to display
                    display_cols = ["user_id", "action_type", "timestamp"]
                    display_cols.extend([col for col in prompt_columns if col not in display_cols])
                    
                    if "task_id" in prompt_df.columns:
                        display_cols.insert(1, "task_id")
                    
                    sample_df = prompt_df[display_cols].head(10)
                    st.dataframe(sample_df, use_container_width=True)
                    
                    # Allow searching the data
                    st.subheader("Search Interaction Data")
                    
                    search_term = st.text_input("Search in interactions:", placeholder="Enter keywords to search...")
                    
                    if search_term:
                        # Search across all string columns
                        mask = pd.Series(False, index=prompt_df.index)
                        
                        for col in prompt_df.columns:
                            if prompt_df[col].dtype == 'object':  # String columns
                                mask = mask | prompt_df[col].astype(str).str.contains(search_term, case=False, na=False)
                        
                        search_results = prompt_df[mask]
                        
                        if not search_results.empty:
                            st.write(f"Found {len(search_results)} matching interactions")
                            st.dataframe(search_results[display_cols], use_container_width=True)
                        else:
                            st.info("No matching interactions found.")
                else:
                    st.warning("No prompt-related interactions found in the data.")
            else:
                st.warning("No prompt-related action types found in the interactions data.")
        else:
            st.warning("No prompt-related columns found in the interactions data.")
    else:
        st.error("No prompt data sources available.")
    

def render_tasks_tab(data):
    """Render task completion statistics"""
    st.header("Task Statistics")
    
    if data["tasks"] is not None:
        # Determine which column to use for task completion status
        completion_col = None
        if "completion_status" in data["tasks"].columns:
            completion_col = "completion_status"
        elif "status" in data["tasks"].columns:
            completion_col = "status"
        
        if completion_col:
            # Task completion counts
            completed_tasks = data["tasks"][data["tasks"][completion_col] == "completed"]
            
            st.subheader("Task Completion Rates")
            if not completed_tasks.empty and "task_id" in completed_tasks.columns:
                # Create task completion counts
                task_counts = completed_tasks["task_id"].value_counts().sort_index().reset_index()
                task_counts.columns = ["Task ID", "Completions"]
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.dataframe(task_counts, use_container_width=True)
                
                with col2:
                    # Create chart
                    fig, ax = plt.subplots(figsize=(8, 4))
                    bars = ax.bar(task_counts["Task ID"].astype(str), task_counts["Completions"])
                    
                    # Add labels
                    for bar in bars:
                        height = bar.get_height()
                        ax.annotate(f'{height}',
                                    xy=(bar.get_x() + bar.get_width() / 2, height),
                                    xytext=(0, 3),
                                    textcoords="offset points",
                                    ha='center', va='bottom')
                    
                    ax.set_title("Task Completions")
                    ax.set_xlabel("Task ID")
                    ax.set_ylabel("Number of Completions")
                    st.pyplot(fig)
        else:
            st.warning("⚠️ Task completion status column not found in tasks data")
            # Still show the task data without completion filtering
            st.subheader("All Tasks")
            st.dataframe(data["tasks"], use_container_width=True)
        
        # Task duration statistics
        st.subheader("Task Duration Statistics")
        if "task_duration" in data["tasks"].columns:
            # Convert to numeric if needed
            data["tasks"]["task_duration"] = pd.to_numeric(data["tasks"]["task_duration"], errors="coerce")
            
            # Group by task_id
            duration_stats = data["tasks"].groupby("task_id")["task_duration"].agg(
                ["count", "mean", "median", "min", "max"]
            ).reset_index()
            
            # Convert seconds to minutes for better readability
            duration_stats["mean"] = duration_stats["mean"] / 60
            duration_stats["median"] = duration_stats["median"] / 60
            duration_stats["min"] = duration_stats["min"] / 60
            duration_stats["max"] = duration_stats["max"] / 60
            
            # Rename columns
            duration_stats.columns = ["Task ID", "Count", "Mean (min)", "Median (min)", "Min (min)", "Max (min)"]
            
            # Round values
            for col in ["Mean (min)", "Median (min)", "Min (min)", "Max (min)"]:
                duration_stats[col] = duration_stats[col].round(2)
                
            st.dataframe(duration_stats, use_container_width=True)
            
            # Box plot of task durations
            fig, ax = plt.subplots(figsize=(10, 6))
            # Convert to minutes for the plot
            completed_tasks["duration_minutes"] = completed_tasks["task_duration"] / 60
            
            # Create boxplot
            boxplot = ax.boxplot(
                [group["duration_minutes"] for _, group in completed_tasks.groupby("task_id")],
                labels=sorted(completed_tasks["task_id"].unique()),
                patch_artist=True
            )
            
            # Customize boxplot colors
            colors = ['lightblue', 'lightgreen', 'lightpink']
            for patch, color in zip(boxplot['boxes'], colors * 10):  # Repeat colors if needed
                patch.set_facecolor(color)
            
            ax.set_title("Task Duration Distribution (minutes)")
            ax.set_xlabel("Task ID")
            ax.set_ylabel("Duration (minutes)")
            ax.grid(True, linestyle='--', alpha=0.7)
            st.pyplot(fig)
        
        # Individual task data
        st.subheader("Individual Task Data")
        
        # Task selection
        task_ids = sorted(data["tasks"]["task_id"].unique())
        selected_task = st.selectbox("Select Task ID", task_ids)
        
        # Filter for selected task
        task_data = data["tasks"][data["tasks"]["task_id"] == selected_task]
        
        if not task_data.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total = len(task_data)
                
                # Display completion rate if we have completion status
                if completion_col:
                    completed = len(task_data[task_data[completion_col] == "completed"])
                    completion_rate = (completed / total) * 100 if total > 0 else 0
                    st.metric("Completion Rate", f"{completion_rate:.1f}%", f"{completed}/{total}")
                else:
                    st.metric("Total Entries", f"{total}")
            
            with col2:
                if "task_duration" in task_data.columns:
                    task_data["task_duration"] = pd.to_numeric(task_data["task_duration"], errors="coerce")
                    avg_duration = task_data["task_duration"].mean() / 60  # Convert to minutes
                    st.metric("Avg Duration", f"{avg_duration:.2f} min")
            
            with col3:
                if "prompt_count" in task_data.columns:
                    task_data["prompt_count"] = pd.to_numeric(task_data["prompt_count"], errors="coerce")
                    avg_prompts = task_data["prompt_count"].mean()
                    st.metric("Avg Prompts", f"{avg_prompts:.1f}")
            
            # Show actual task data
            st.dataframe(task_data, use_container_width=True)
        else:
            st.info("No data available for the selected task")
    else:
        st.info("No task data available")

def render_feedback_tab(data):
    """Render feedback statistics"""
    st.header("Feedback Analysis")
    
    # Check if feedback data exists in different places
    feedback_df = None
    source = None
    
    if data["feedback"] is not None and len(data["feedback"]) > 0:
        feedback_df = data["feedback"]
        feedback_column = "feedback_value" if "feedback_value" in feedback_df.columns else "feedback"
        source = "feedback.csv"
    elif data["interactions"] is not None:
        # Filter for feedback interactions
        feedback_interactions = data["interactions"][data["interactions"]["action_type"] == "FEEDBACK"]
        if len(feedback_interactions) > 0:
            feedback_df = feedback_interactions
            feedback_column = "feedback"
            source = "interactions.csv (FEEDBACK actions)"
    
    if feedback_df is not None and len(feedback_df) > 0:
        st.info(f"Showing feedback data from {source}")
        
        # Ensure feedback is numeric
        if feedback_column in feedback_df.columns:
            feedback_df[feedback_column] = pd.to_numeric(feedback_df[feedback_column], errors="coerce")
            
            # Overall feedback statistics
            st.subheader("Overall Feedback")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Calculate counts and percentages
                total_feedback = len(feedback_df)
                positive = len(feedback_df[feedback_df[feedback_column] > 0])
                negative = len(feedback_df[feedback_df[feedback_column] < 0])
                neutral = len(feedback_df[feedback_df[feedback_column] == 0])
                
                positive_pct = (positive / total_feedback) * 100 if total_feedback > 0 else 0
                negative_pct = (negative / total_feedback) * 100 if total_feedback > 0 else 0
                neutral_pct = (neutral / total_feedback) * 100 if total_feedback > 0 else 0
                
                feedback_summary = pd.DataFrame({
                    "Rating": ["Positive", "Neutral", "Negative"],
                    "Count": [positive, neutral, negative],
                    "Percentage": [f"{positive_pct:.1f}%", f"{neutral_pct:.1f}%", f"{negative_pct:.1f}%"]
                })
                
                st.dataframe(feedback_summary, use_container_width=True)
            
            with col2:
                # Create pie chart
                fig, ax = plt.subplots(figsize=(8, 5))
                colors = ['#4CAF50', '#FFC107', '#F44336']  # Green, Yellow, Red
                ax.pie(
                    [positive, neutral, negative],
                    labels=["Positive", "Neutral", "Negative"],
                    autopct='%1.1f%%',
                    colors=colors,
                    startangle=90
                )
                ax.set_title("Feedback Distribution")
                st.pyplot(fig)
            
            # Feedback by task if task_id is available
            if "task_id" in feedback_df.columns:
                st.subheader("Feedback by Task")
                
                # Group by task_id and calculate stats
                task_feedback = feedback_df.groupby("task_id").agg({
                    feedback_column: ["count", "mean"]
                }).reset_index()
                
                task_feedback.columns = ["Task ID", "Count", "Average Rating"]
                task_feedback["Average Rating"] = task_feedback["Average Rating"].round(2)
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.dataframe(task_feedback, use_container_width=True)
                
                with col2:
                    # Create bar chart
                    fig, ax = plt.subplots(figsize=(8, 4))
                    bars = ax.bar(task_feedback["Task ID"].astype(str), task_feedback["Average Rating"])
                    
                    # Color bars based on value
                    for i, bar in enumerate(bars):
                        value = task_feedback["Average Rating"].iloc[i]
                        if value > 0:
                            bar.set_color('#4CAF50')  # Green for positive
                        elif value < 0:
                            bar.set_color('#F44336')  # Red for negative
                        else:
                            bar.set_color('#FFC107')  # Yellow for neutral
                    
                    ax.set_title("Average Feedback by Task")
                    ax.set_xlabel("Task ID")
                    ax.set_ylabel("Average Rating (-1 to 1)")
                    ax.axhline(y=0, color='black', linestyle='-', alpha=0.2)
                    
                    # Add value labels on top of bars
                    for bar in bars:
                        height = bar.get_height()
                        ax.annotate(f'{height:.2f}',
                                    xy=(bar.get_x() + bar.get_width() / 2, height),
                                    xytext=(0, 3 if height >= 0 else -10),
                                    textcoords="offset points",
                                    ha='center', va='bottom' if height >= 0 else 'top')
                    
                    st.pyplot(fig)
            
            # Raw feedback data with improved display of prompts and responses
            st.subheader("Feedback Details")
            
            # Check if we have prompt/response excerpts
            has_prompt_excerpt = "prompt_excerpt" in feedback_df.columns
            has_response_excerpt = "response_excerpt" in feedback_df.columns
            has_model_response = "model_response" in feedback_df.columns
            has_original_prompt = "original_prompt" in feedback_df.columns
            
            # Create a display dataframe with relevant columns
            display_columns = ["user_id", "task_id", feedback_column, "timestamp"]
            
            # Add prompt and response columns if available
            if has_prompt_excerpt:
                display_columns.append("prompt_excerpt")
            elif has_original_prompt:
                display_columns.append("original_prompt")
                
            if has_response_excerpt:
                display_columns.append("response_excerpt") 
            elif has_model_response:
                display_columns.append("model_response")
            
            # Create a more user-friendly display dataframe
            if has_prompt_excerpt or has_response_excerpt or has_original_prompt or has_model_response:
                display_df = feedback_df[display_columns].copy()
                
                # Truncate long text fields for better display
                for col in ["original_prompt", "model_response"]:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].astype(str).apply(lambda x: x[:100] + "..." if len(x) > 100 else x)
                
                st.dataframe(display_df, use_container_width=True)
                
                # Add details expander for viewing full content
                with st.expander("View Full Feedback Details"):
                    selected_index = st.selectbox(
                        "Select feedback item to view details:", 
                        range(len(feedback_df)),
                        format_func=lambda i: f"User: {feedback_df.iloc[i]['user_id']} - Task: {feedback_df.iloc[i]['task_id']} - Rating: {feedback_df.iloc[i][feedback_column]}"
                    )
                    
                    selected_item = feedback_df.iloc[selected_index]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Prompt")
                        prompt_content = ""
                        if has_original_prompt:
                            prompt_content = selected_item.get("original_prompt", "")
                        elif has_prompt_excerpt:
                            prompt_content = selected_item.get("prompt_excerpt", "")
                            
                        # Add a unique key to this text_area
                        st.text_area("", prompt_content, height=200, key=f"feedback_prompt_{selected_index}")
                        
                    with col2:
                        st.subheader("Response")
                        response_content = ""
                        if has_model_response:
                            response_content = selected_item.get("model_response", "")
                        elif has_response_excerpt:
                            response_content = selected_item.get("response_excerpt", "")
                            
                        # Add a unique key to this text_area
                        st.text_area("", response_content, height=200, key=f"feedback_response_{selected_index}")
                    
                    # Display feedback value with appropriate styling
                    feedback_val = selected_item[feedback_column]
                    feedback_text = "Positive" if feedback_val > 0 else ("Negative" if feedback_val < 0 else "Neutral")
                    feedback_color = "#4CAF50" if feedback_val > 0 else ("#F44336" if feedback_val < 0 else "#FFC107")
                    
                    st.markdown(f"""
                    <div style="padding: 10px; background-color: {feedback_color}; color: white; border-radius: 5px; text-align: center; margin: 10px 0;">
                        <h3 style="margin: 0;">Feedback: {feedback_text} ({feedback_val})</h3>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # If we don't have prompt/response data, just show the basic feedback info
                st.dataframe(feedback_df, use_container_width=True)
    else:
        st.info("No feedback data available")

def render_data_explorer_tab(data):
    """Render data exploration interface"""
    st.header("Data Explorer")
    
    # File selector
    data_files = {
        "Users": "users",
        "Tasks": "tasks",
        "Interactions": "interactions",
        "Surveys": "surveys",
        "Feedback": "feedback",
        "Logins": "logins"
    }
    
    available_files = [name for name, key in data_files.items() if data[key] is not None]
    
    if available_files:
        selected_file = st.selectbox("Select data file to explore:", available_files)
        
        # Get the corresponding dataframe
        selected_df = data[data_files[selected_file]]
        
        if not selected_df.empty:
            # Data summary
            st.subheader(f"{selected_file} Data Summary")
            
            # Show file size and row count
            file_path = os.path.join(data["data_dir"], f"{data_files[selected_file]}.csv")
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024) if os.path.exists(file_path) else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Row Count", f"{len(selected_df):,}")
            col2.metric("Column Count", f"{len(selected_df.columns):,}")
            col3.metric("File Size", f"{file_size_mb:.2f} MB")
            
            # Column filter
            if len(selected_df.columns) > 5:
                default_columns = list(selected_df.columns[:5])
                selected_columns = st.multiselect(
                    "Select columns to display:", 
                    options=list(selected_df.columns),
                    default=default_columns
                )
                
                if selected_columns:
                    filtered_df = selected_df[selected_columns]
                else:
                    filtered_df = selected_df
            else:
                filtered_df = selected_df
            
            # Search filter
            search_term = st.text_input("Search in data:", placeholder="Enter search term...")
            if search_term:
                # Apply search across all columns
                mask = pd.Series(False, index=filtered_df.index)
                for col in filtered_df.columns:
                    mask = mask | filtered_df[col].astype(str).str.contains(search_term, case=False, na=False)
                filtered_df = filtered_df[mask]
            
            # Show dataframe
            st.dataframe(filtered_df, use_container_width=True)
            
            # Export options
            st.download_button(
                label="Download Filtered Data as CSV",
                data=filtered_df.to_csv(index=False).encode('utf-8'),
                file_name=f"{data_files[selected_file]}_filtered.csv",
                mime="text/csv"
            )
        else:
            st.info(f"The {selected_file} file is empty")
    else:
        st.warning("No data files available to explore")

def main():
    """Main function to run the admin dashboard"""
    if authenticate():
        # Load data only after authentication
        with st.spinner("Loading study data..."):
            data = load_data()
        
        # Render dashboard
        render_dashboard(data)

if __name__ == "__main__":
    main()
