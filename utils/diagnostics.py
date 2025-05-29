import os
import sys
import json
import pandas as pd
import datetime
import traceback
import streamlit as st
from typing import Dict, List, Any, Optional
from utils.data_storage import DataStorage
from tracking.logging import check_storage_status, enhanced_logger

def run_storage_diagnostics() -> Dict:
    """Run comprehensive diagnostics on the storage system"""
    results = {
        "timestamp": datetime.datetime.now().isoformat(),
        "system_info": {
            "python_version": sys.version,
            "pandas_version": pd.__version__,
            "platform": sys.platform,
            "executable": sys.executable
        },
        "storage_status": None,
        "file_counts": {},
        "sample_data": {}
    }
    
    try:
        # Get storage status
        storage = DataStorage()
        results["storage_status"] = storage.get_storage_status()
        
        # Get logging status
        results["logging_status"] = check_storage_status()
        
        # Count rows in key files
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        key_files = ['users.csv', 'tasks.csv', 'interactions.csv', 'surveys.csv', 'validation.csv']
        
        for filename in key_files:
            filepath = os.path.join(data_dir, filename)
            if os.path.exists(filepath):
                try:
                    df = pd.read_csv(filepath, sep=';')
                    results["file_counts"][filename] = len(df)
                    
                    # Get sample data (last 2 rows)
                    if not df.empty:
                        # Convert to dict for JSON serialization
                        sample = df.tail(2).to_dict(orient='records')
                        # Truncate long text fields
                        for record in sample:
                            for key, value in record.items():
                                if isinstance(value, str) and len(value) > 200:
                                    record[key] = value[:200] + "..."
                        results["sample_data"][filename] = sample
                except Exception as e:
                    results["file_counts"][filename] = f"Error: {str(e)}"
            else:
                results["file_counts"][filename] = "File not found"
                
        # Check for recent log files
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        if os.path.exists(log_dir):
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log') or f.endswith('.txt')]
            results["log_files"] = {}
            
            for log_file in log_files:
                filepath = os.path.join(log_dir, log_file)
                file_stats = os.stat(filepath)
                
                # Get last few lines of each log file
                last_lines = []
                try:
                    with open(filepath, 'r') as f:
                        lines = f.readlines()
                        last_lines = lines[-10:] if len(lines) >= 10 else lines
                except Exception as e:
                    last_lines = [f"Error reading file: {str(e)}"]
                
                results["log_files"][log_file] = {
                    "size_bytes": file_stats.st_size,
                    "modified": datetime.datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    "last_lines": last_lines
                }
    except Exception as e:
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()
    
    return results

def render_diagnostics_page():
    """Render a Streamlit diagnostics page"""
    st.title("PromptDoctor Diagnostics")
    
    st.write("This utility helps diagnose issues with the logging system.")
    
    if st.button("Run Diagnostics"):
        with st.spinner("Running diagnostics..."):
            results = run_storage_diagnostics()
            
            st.write("## System Information")
            st.json(results["system_info"])
            
            st.write("## Storage Status")
            if "storage_status" in results and results["storage_status"]:
                # Show directories status
                st.write("### Directories")
                directories = results["storage_status"]["directories"]
                for dir_name, dir_info in directories.items():
                    status = "✅" if dir_info.get("exists") and dir_info.get("writable") else "❌"
                    st.write(f"{status} **{dir_name}**: {dir_info.get('path')}")
                
                # Show files status
                st.write("### Files")
                files = results["storage_status"]["files"]
                for file_name, file_info in files.items():
                    status = "✅" if file_info.get("exists") else "❌"
                    row_count = file_info.get("row_count", "Unknown")
                    if row_count == -1:
                        row_count = "Error counting rows"
                    st.write(f"{status} **{file_name}**: {row_count} rows, {file_info.get('size_bytes', 0)} bytes")
            else:
                st.error("Failed to get storage status")
            
            st.write("## Data File Counts")
            for filename, count in results.get("file_counts", {}).items():
                st.write(f"**{filename}**: {count}")
            
            st.write("## Sample Data")
            for filename, samples in results.get("sample_data", {}).items():
                if samples:
                    st.write(f"### Recent entries in {filename}")
                    st.json(samples)
            
            st.write("## Log Files")
            for log_name, log_info in results.get("log_files", {}).items():
                with st.expander(f"{log_name} ({log_info.get('modified')})"):
                    st.code("".join(log_info.get("last_lines", [])))
            
            # Full JSON data
            with st.expander("Full Diagnostic Data (JSON)"):
                st.json(results)
            
            # Save diagnostics to file
            try:
                log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
                os.makedirs(log_dir, exist_ok=True)
                
                diagnostic_file = os.path.join(log_dir, f"diagnostics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(diagnostic_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                st.success(f"Diagnostic data saved to {diagnostic_file}")
            except Exception as e:
                st.error(f"Failed to save diagnostic data: {str(e)}")

if __name__ == "__main__":
    render_diagnostics_page()
