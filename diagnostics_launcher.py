import streamlit as st
import webbrowser
import time
import os
import sys
from pathlib import Path

def main():
    """Launch the diagnostics page directly"""
    print("PromptDoctor Diagnostics Launcher")
    print("=================================")
    
    # Determine the Streamlit server URL
    # Default to localhost:8501 if not specified
    base_url = "http://localhost:8501"
    
    # Build the diagnostics page URL
    diagnostics_url = f"{base_url}/99_Diagnostics"
    
    print(f"Opening diagnostics page at {diagnostics_url}")
    print(f"Password: PromptDoctorAdmin")
    
    # Open the browser to the diagnostics page
    webbrowser.open(diagnostics_url)
    
    print("If the browser doesn't open automatically, please navigate to:")
    print(diagnostics_url)
    print("\nRemember to use the password: PromptDoctorAdmin")

if __name__ == "__main__":
    main()
