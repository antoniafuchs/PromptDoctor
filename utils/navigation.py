import streamlit as st

def nav_to(page_name: str):
    """Navigate to another page programmatically"""
    from streamlit.runtime.scriptrunner import RerunData, RerunException
    from streamlit.source_util import get_pages
    
    def standardize_name(name: str) -> str:
        return name.lower().replace(" ", "_")
    
    # Get all pages
    current_pages = get_pages("")
    
    # Find matching page
    for page_hash, config in current_pages.items():
        if standardize_name(config["page_name"]) == standardize_name(page_name):
            raise RerunException(
                RerunData(
                    page_script_hash=page_hash,
                    page_name=page_name,
                )
            )
    
    # If page not found
    raise ValueError(f"Could not find page {page_name}")
