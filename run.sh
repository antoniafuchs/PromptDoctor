#!/bin/bash

# Set environment variables for Streamlit
export STREAMLIT_WATCHER_IGNORE_MODULES=torch

# Run the app
streamlit run app.py
