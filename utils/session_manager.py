import streamlit as st
from typing import Optional

class SessionManager:
    @staticmethod
    def get_session_id() -> Optional[str]:
        """Get current user session ID"""
        return st.session_state.get('user_id')
    
    @staticmethod
    def set_session_id(user_id: str) -> None:
        """Set user session ID"""
        st.session_state.user_id = user_id
    
    @staticmethod
    def clear_session() -> None:
        """Clear session data"""
        if 'user_id' in st.session_state:
            del st.session_state.user_id

class DataStorage:
    def __init__(self):
        # Initialize db attribute to prevent 'no attribute' error
        self.db = None
    
    def save_highlight_metrics(self, metrics_data):
        if not hasattr(self, 'db') or self.db is None:
            # Initialize db connection or handle the error gracefully
            print("Warning: Database connection not initialized for metrics storage")
            return False
        # ...existing implementation...
