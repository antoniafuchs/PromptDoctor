import streamlit as st

def get_or_create_unique_id():
    """Get existing or create new user ID"""
    if 'unique_user_id' not in st.session_state:
        st.session_state.unique_user_id = None
    return st.session_state.unique_user_id
