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
