"""
Run this script to directly access the diagnostics page without going through the main app.
This is useful for administrators who need to check system status quickly.
"""
import os
import sys
import subprocess
import webbrowser
import time
import argparse
import pandas as pd
from datetime import datetime

def count_active_users():
    """Count how many users are currently active based on recent logins"""
    try:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        logins_file = os.path.join(data_dir, 'logins.csv')
        
        if not os.path.exists(logins_file):
            return "No login data found"
            
        # Load logins data
        logins_df = pd.read_csv(logins_file, sep=';')
        
        # Convert timestamps to datetime
        logins_df['timestamp'] = pd.to_datetime(logins_df['timestamp'])
        
        # Filter for recent logins (last 24 hours)
        now = pd.Timestamp.now()
        recent_logins = logins_df[logins_df['timestamp'] > (now - pd.Timedelta(hours=24))]
        
        # Count unique users
        active_users = recent_logins['user_id'].nunique()
        
        return f"Active users in last 24 hours: {active_users}"
    except Exception as e:
        return f"Error counting active users: {str(e)}"

def print_quick_stats():
    """Print quick stats about the study data"""
    try:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        
        print("\nQuick Study Statistics:")
        print("======================")
        
        # Files to check
        files = {
            'users.csv': 'Total users registered',
            'tasks.csv': 'Tasks completed', 
            'interactions.csv': 'Chat interactions',
            'feedback.csv': 'Feedback submissions',
            'surveys.csv': 'Survey responses'
        }
        
        for filename, description in files.items():
            filepath = os.path.join(data_dir, filename)
            if os.path.exists(filepath):
                try:
                    df = pd.read_csv(filepath, sep=';')
                    if 'user_id' in df.columns:
                        count = df['user_id'].nunique()
                        total = len(df)
                        print(f"{description}: {count} users, {total} entries")
                    else:
                        print(f"{description}: {len(df)} entries")
                except Exception as e:
                    print(f"{description}: Error reading file - {str(e)}")
            else:
                print(f"{description}: File not found")
                
        # Show active users
        print(f"\n{count_active_users()}")
        
    except Exception as e:
        print(f"Error generating statistics: {str(e)}")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="PromptDoctor Diagnostics Launcher")
    parser.add_argument('--stats', action='store_true', help='Display quick statistics without launching UI')
    parser.add_argument('--port', type=int, default=8501, help='Port to run Streamlit on (default: 8501)')
    args = parser.parse_args()
    
    # If only stats requested, show them and exit
    if args.stats:
        print_quick_stats()
        return
    
    print("PromptDoctor Diagnostics Launcher")
    print("=================================")
    
    # Path to the diagnostics page
    diag_path = os.path.join(os.path.dirname(__file__), "pages", "99_Diagnostics.py")
    
    if not os.path.exists(diag_path):
        print(f"ERROR: Diagnostics page not found at {diag_path}")
        return
        
    print(f"Found diagnostics page at {diag_path}")
    print("Launching diagnostics directly...")
    
    try:
        # Show quick stats before launching
        print_quick_stats()
        
        # Run streamlit with the diagnostics page on specified port
        subprocess.Popen([
            sys.executable, 
            "-m", "streamlit", 
            "run", 
            diag_path, 
            "--server.port", str(args.port),
            "--server.headless", "true",
            "--server.fileWatcherType", "none"  # Disable file watcher for faster startup
        ])
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Open browser
        webbrowser.open(f"http://localhost:{args.port}")
        
        print(f"Diagnostics page should be opening in your browser at http://localhost:{args.port}")
        print("Use password: PromptDoctorAdmin")
        
    except Exception as e:
        print(f"Error launching diagnostics: {str(e)}")
        
    print("\nReminder: Use password 'PromptDoctorAdmin' to access diagnostics")
    print("Press Ctrl+C to quit the server when finished")

if __name__ == "__main__":
    main()
