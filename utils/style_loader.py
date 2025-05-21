import streamlit as st
import os

def load_styles():
    """Load shared CSS styles"""
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'styles', 'main.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
