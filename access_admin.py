"""
Admin Dashboard Access Script

Run this script to directly access the admin dashboard without going through the main app.
This is useful for quickly checking study progress.

Usage:
    python access_admin.py
"""
import streamlit as st
import webbrowser
import time
import os
import sys
import subprocess

def main():
    print("PromptDoctor Admin Dashboard Launcher")
    print("=====================================")
    
    # Path to the admin dashboard page
    admin_path = os.path.join(os.path.dirname(__file__), "pages", "admin_dashboard.py")
    
    if not os.path.exists(admin_path):
        print(f"ERROR: Admin dashboard page not found at {admin_path}")
        return
        
    print(f"Found admin dashboard at {admin_path}")
    print("Launching admin dashboard directly...")
    
    try:
        # Run streamlit with the admin dashboard page
        process = subprocess.Popen([
            sys.executable, 
            "-m", 
            "streamlit", 
            "run", 
            admin_path,
            "--server.headless", "true",
            "--server.fileWatcherType", "none"  # Disable file watcher for faster startup
        ])
        
        # Wait a moment for server to start
        time.sleep(2)
        
        # Open browser
        webbrowser.open("http://localhost:8501")
        
        print("Admin dashboard should be opening in your browser.")
        print("Use password: PromptDoctorAdmin")
        
        print("\nPress Ctrl+C to stop the server when done.")
        
        # Keep the process running until user interrupts
        process.wait()
        
    except KeyboardInterrupt:
        print("\nShutting down admin dashboard...")
        # Try to gracefully terminate the process
        process.terminate()
        time.sleep(1)
        if process.poll() is None:  # If still running
            process.kill()  # Force kill
    except Exception as e:
        print(f"Error launching admin dashboard: {str(e)}")

if __name__ == "__main__":
    main()
