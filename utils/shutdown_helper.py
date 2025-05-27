import os
import sys
import psutil
import platform
from typing import Optional
import streamlit as st

def shutdown_app():
    """Gracefully shutdown the Streamlit app"""
    print("[DEBUG] Initiating app shutdown...")
    
    # Get the current process
    pid = os.getpid()
    try:
        process = psutil.Process(pid)
        
        # Log before terminating
        print(f"[DEBUG] Terminating process {pid}")
        
        # Different handling for different platforms
        current_platform = platform.system().lower()
        
        if current_platform == 'darwin':  # macOS
            os.kill(pid, 9)
        elif current_platform == 'windows':
            process.terminate()
        else:  # Linux and others
            process.kill()
            
    except Exception as e:
        print(f"[DEBUG] Error during shutdown: {str(e)}")
        sys.exit(0)  # Fallback exit
