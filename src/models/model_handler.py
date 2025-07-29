"""
model_handler.py

This file handles model loading, inference, and management for PromptDoctor, providing an interface to interact with different models.
"""

import requests
import json
from .model_config import ModelConfig
from .huggingface_handler import HuggingFaceHandler
import streamlit as st
import os

class ModelHandler:
    def __init__(self):
        self.model_type = None
        self.current_model = None
        self.hf_handler = None
        self.together_client = None
    
    def initialize_model(self, model_type, model_name=None):
        """Initialize the selected model type and specific model"""
        self.model_type = model_type
        self.current_model = model_name
        
        if model_type == "HuggingFace" and model_name:
            self._initialize_huggingface(model_name)
        elif model_type == "Together" and model_name:
            self._initialize_together(model_name)

    def generate_response(self, messages, system_prompt, stream_handler=None):
        """Generate response based on model type"""
        if self.model_type == "Ollama":
            try:
                payload = {
                    "model": self.current_model or "llama3-med42-8b",
                    "messages": [
                        {"role": "system", "content": system_prompt}
                    ] + messages
                }
                response = requests.post(
                    "http://localhost:11434/api/chat",
                    json=payload,
                    stream=True
                )
                final_response = ""
                
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            final_response += content
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                
                return final_response or "No response generated"
                
            except Exception as e:
                return f"Error: {str(e)}"
        elif self.model_type == "HuggingFace":
            return self._generate_huggingface(messages, system_prompt)
        elif self.model_type == "Together":
            return self._generate_together(messages, system_prompt, stream_handler)
        elif self.model_type == "GPT":
            return "GPT integration not implemented yet"
        return "Unknown model type"

    def _generate_ollama(self, messages, system_prompt, stream_handler=None):
        """Handle Ollama model generation with graceful error handling"""
        try:
            payload = {
                "model": self.current_model or "llama3-med42-8b",
                "messages": [
                    {"role": "system", "content": system_prompt}
                ] + messages
            }
            response = requests.post(
                f"{self.ollama_server_url}/api/chat",
                json=payload,
                stream=True,
                timeout=60
            )

            final_response = ""
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        final_response += content
                        if stream_handler:
                            stream_handler(final_response)
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
            
            return final_response or "No response generated"
            
        except requests.exceptions.ConnectionError:
            return ("Error: Could not connect to Ollama server. Please make sure it's running with 'ollama serve' "
                   "or check your connection.")
        except Exception as e:
            return f"Error: {str(e)}"

    def _generate_huggingface(self, messages, system_prompt):
        """Handle HuggingFace model generation"""
        try:
            if not self.hf_handler:
                self.hf_handler = HuggingFaceHandler()
                if self.current_model:
                    self.hf_handler.initialize_model(self.current_model)
                else:
                    raise ValueError("No HuggingFace model specified")
            
            # Combine messages into a single prompt
            prompt = system_prompt + "\n\n"
            for msg in messages:
                content = msg.get("content", "")
                prompt += f"{content}\n"
                
            return self.hf_handler.generate_response(prompt)
        except Exception as e:
            print(f"[Model] HuggingFace generation error: {str(e)}")
            return f"Error generating response: {str(e)}"

    def _initialize_huggingface(self, model_name: str) -> None:
        """Initialize HuggingFace model with proper settings"""
        if not self.hf_handler:
            from .huggingface_handler import HuggingFaceHandler
            self.hf_handler = HuggingFaceHandler()
        self.hf_handler.initialize_model(model_name)
        print(f"[Model] HuggingFace model {model_name} initialized")

    def _initialize_together(self, model_name: str) -> None:
        """Initialize Together API client"""
        try:
            from together import Together
            
            # Check for API key in session state
            api_key = None
            if hasattr(st, 'session_state') and 'together_api_key' in st.session_state:
                api_key = st.session_state.together_api_key
                
            # Initialize client with API key if available
            if api_key:
                self.together_client = Together(api_key=api_key)
                # Also set environment variable as backup
                os.environ["TOGETHER_API_KEY"] = api_key
            else:
                # Check if environment variable is set
                if "TOGETHER_API_KEY" in os.environ:
                    self.together_client = Together()
                else:
                    print("[WARNING] No Together API key found in session state or environment")
                    return
                    
            self.current_model = model_name
            print(f"[Model] Together API initialized with model {model_name}")
        except ImportError:
            print("[WARNING] Together package not installed. Install with 'pip install together'")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Together API: {str(e)}")

    def _generate_together(self, messages, system_prompt, stream_handler=None):
        """Generate response using Together API"""
        try:
            if not self.together_client:
                # Try to reinitialize with API key
                api_key = None
                if hasattr(st, 'session_state') and 'together_api_key' in st.session_state:
                    api_key = st.session_state.together_api_key
                
                from together import Together
                if api_key:
                    self.together_client = Together(api_key=api_key)
                else:
                    if "TOGETHER_API_KEY" in os.environ:
                        self.together_client = Together()
                    else:
                        return "Error: Together API key not found. Please set the TOGETHER_API_KEY environment variable or provide it via the UI."
            
            # Format messages for the API
            formatted_messages = []
            
            # Add system message first if provided
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
                
            # Add all other messages
            formatted_messages.extend(messages)
            
            # Generate completion
            if stream_handler:
                # Streaming mode
                response = self.together_client.chat.completions.create(
                    model=self.current_model,
                    messages=formatted_messages,
                    max_tokens=1024,
                    temperature=0.7,
                    stream=True
                )
                
                full_response = ""
                for token in response:
                    if hasattr(token, 'choices') and token.choices and hasattr(token.choices[0], 'delta'):
                        chunk = token.choices[0].delta.content or ""
                        full_response += chunk
                        if stream_handler:
                            stream_handler(full_response)
                            
                return full_response
            else:
                # Non-streaming mode
                response = self.together_client.chat.completions.create(
                    model=self.current_model,
                    messages=formatted_messages,
                    max_tokens=1024,
                    temperature=0.7,
                    stream=False
                )
                
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    return response.choices[0].message.content
                return "No response generated"
                
        except ImportError:
            return "Error: Together package not installed. Install with 'pip install together'"
        except Exception as e:
            return f"Error generating response: {str(e)}"
