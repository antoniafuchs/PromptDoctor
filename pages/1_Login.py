import streamlit as st
import uuid
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import glob
import json
from tracking.logging import log_chat_interaction
from utils.model_config import ModelConfig

def get_local_ollama_models():
    """Get list of locally available Ollama models"""
    models_path = os.path.expanduser("~/.ollama/models/manifests/registry.ollama.ai/library/")
    if not os.path.exists(models_path):
        return []
    
    model_entries = glob.glob(os.path.join(models_path, "*"))
    models = []
    
    for entry in model_entries:
        model_name = os.path.basename(entry)
        
        # Check if it's a directory
        if os.path.isdir(entry):
            # Try to find a manifest.json inside the directory
            manifest_path = os.path.join(entry, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                        display_name = f"{model_name} ({manifest.get('version', 'unknown')})"
                except:
                    display_name = f"{model_name} (custom)"
            else:
                display_name = f"{model_name} (custom)"
                
        # If it's a file
        else:
            try:
                with open(entry, 'r') as f:
                    manifest = json.load(f)
                    display_name = f"{model_name} ({manifest.get('version', 'unknown')})"
            except:
                display_name = model_name
        
        models.append({
            "name": model_name,
            "display_name": display_name,
            "path": entry
        })
    
    return models

def show_login_page():
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
        
    st.set_page_config(page_title="PromptDoctor - Login", page_icon="🔑")
    st.header("Login")
    st.markdown("### Welcome to PromptDoctor")
    st.markdown("Please login and select your preferred model")

    # Model type selection
    model_type = st.selectbox(
        "Select Model Type",
        ["Ollama", "GPT", "HuggingFace"],
        key="model_selection"
    )

    # Get available models for selected type
    if model_type == "Ollama":
        local_models = get_local_ollama_models()
        if local_models:
            available_models = ModelConfig.merge_with_local_models(local_models)
        else:
            available_models = ModelConfig.DEFAULT_CONFIGS.get(model_type, [])
    else:
        available_models = ModelConfig.DEFAULT_CONFIGS.get(model_type, [])

    model_options = {m["display_name"]: m["name"] for m in available_models}

    if not model_options:
        st.warning("No models found. For Ollama, please ensure models are installed in ~/.ollama/models/")
        model_options = {"No models available": "none"}

    selected_model_display = st.selectbox(
        f"Select {model_type} Model",
        options=list(model_options.keys()),
        key="specific_model_selection"
    )

    selected_model = model_options[selected_model_display]

    if st.button("Login"):
        st.session_state.user_id = str(uuid.uuid4())
        st.session_state.selected_model_type = model_type
        st.session_state.selected_model_name = selected_model
        st.session_state.current_page = "login_survey"
        
        # Log login event
        log_chat_interaction(
            st.session_state.user_id,
            "LOGIN",
            model_type=f"{model_type}/{selected_model_display}"
        )
        
        st.switch_page("pages/2_Survey.py")

show_login_page()
