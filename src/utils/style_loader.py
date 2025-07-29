"""
style_loader.py

This file provides utilities for loading and applying styles in PromptDoctor, supporting UI customization and theming.
"""

import streamlit as st
import os

def load_styles():
    """Load shared styles for consistent display across pages"""
    
    st.markdown("""
    <style>
        /* Base styling */
        body {
            color: #303030;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 16px;
        }
                
        p {
            font-size: 16px;
        }
        
        /* Clinical note styling */
        .clinical-note {
            line-height: 1.8;
            font-size: 16px;
            margin: 15px 0;
            padding: 15px;
            background-color: white;
            border-radius: 8px;
            border: 1px solid #eee;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        /* Highlight styling */
        .highlight-red {
            display: inline-block;
            padding: 2px 4px;
            margin: 0 2px;
            border-radius: 3px;
            background-color: rgba(220, 53, 69, 0.37);
            color: black;
            font-weight: 500;
        }
        .highlight-blue {
            display: inline-block;
            padding: 2px 4px;
            margin: 0 2px;
            border-radius: 3px;
            background-color: rgba(0, 123, 255, 0.22);
            color: black;
            font-weight: 500;
        }
        .highlight-legend-red {
            color: rgb(220, 53, 69);
            font-weight: 600;
        }
        .highlight-legend-blue {
            color: rgb(0, 123, 255);
            font-weight: 600;
        }
        .highlight-explanation {
            margin-top: 15px;
            line-height: 1.6;
            font-size: 16px;
        }
        
        /* Form controls */
        button {
            border-radius: 4px;
        }
        
        
    </style>
    """, unsafe_allow_html=True)
