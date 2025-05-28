from typing import Dict, List
import requests
import os
import streamlit as st

try:
    from together import Together
    TOGETHER_AVAILABLE = True
except ImportError:
    TOGETHER_AVAILABLE = False
    print("[WARNING] Together API package not installed. Install with 'pip install together'")

from .base import ModelProvider

class TogetherProvider(ModelProvider):
    DEFAULT_MODELS = [
        {"name": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", "display_name": "Llama 3.3 70B Instruct (Free)"},
        {"name": "meta-llama/Llama-3.1-8B-Instruct", "display_name": "Llama 3.1 8B Instruct"},
        {"name": "mistralai/Mixtral-8x7B-Instruct-v0.1", "display_name": "Mixtral 8x7B Instruct"}
    ]
    
    def __init__(self):
        self.client = None
        self.current_model = None
        
    def get_available_models(self) -> List[Dict[str, str]]:
        """Return list of available Together models"""
        return self.DEFAULT_MODELS
        
    def initialize_model(self, model_name: str) -> None:
        """Initialize Together API client and set model"""
        self.current_model = model_name
        if TOGETHER_AVAILABLE:
            self._init_client()
        
    def _init_client(self):
        """Initialize Together client with proper API key handling"""
        try:
            # First check if API key is in session state
            api_key = st.session_state.get("together_api_key")
            
            # If API key is in session state, initialize with it
            if api_key:
                self.client = Together(api_key=api_key)
                print("[Together] Initialized client with API key from session state")
                return
                
            # If not in session state but in environment, initialize without explicit key
            if "TOGETHER_API_KEY" in os.environ:
                self.client = Together()
                print("[Together] Initialized client with API key from environment")
                return
                
            # No API key available
            print("[Together] WARNING: No API key found in session state or environment")
            self.client = None
        except Exception as e:
            print(f"[Together] Error initializing client: {str(e)}")
            self.client = None
        
    def generate_response(self, messages: List[Dict], system_prompt: str) -> str:
        """Generate response using Together API"""
        if not TOGETHER_AVAILABLE:
            return "Error: Together package not installed. Install with 'pip install together'"
            
        if not self.client:
            self._init_client()
            if not self.client:
                return "Error: Failed to initialize Together client. API key may be missing."
            
        if not self.current_model:
            return "Error: No model selected"
            
        try:
            # Format messages for the API
            formatted_messages = []
            
            # Add system message first if provided
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
                
            # Add all other messages
            formatted_messages.extend(messages)
            
            # Generate completion
            response = self.client.chat.completions.create(
                model=self.current_model,
                messages=formatted_messages,
                max_tokens=1024,
                temperature=0.7,
                stream=False
            )
            
            # Extract and return the response text
            if hasattr(response, 'choices') and len(response.choices) > 0:
                return response.choices[0].message.content
            return "No response generated"
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
