import streamlit as st

# Page config must be first Streamlit command
st.set_page_config(
    page_title="PromptDoctor - Chat",
    layout="wide"
)

import requests
import json
import uuid
import datetime
import pyperclip
from typing import List
from tracking.timer import Timer
from tracking.logging import (
    log_model_output,
    log_user_interaction,
    log_task_duration,
    log_chat_interaction,
    log_validation_action,
    log_lime_explanation
)
from tracking.task_manager import TaskManager  # Add this import
from utils.pdf_handler import displayPDF, displayPDFpage, handle_pdf_upload
from utils.medical_processor import MedicalTermProcessor
from utils.prompt_validator import validate_prompt, add_highlights
from utils.model_config import ModelConfig
from utils.xai import LIMEMedicalExplainer
from utils.xai.processing import XAIProcessor
import os
import glob
from threading import Thread
import pandas as pd
from utils.ml_utils import init_torch
from utils.model_handler import ModelHandler
from streamlit_extras.switch_page_button import switch_page

# Initialize PyTorch with basic settings
init_torch()

# Try to import ollama, fallback to requests if not available
try:
    OLLAMA_CLIENT_AVAILABLE = True
except ImportError:
    print("[WARNING] Ollama client package not installed. Falling back to direct API calls.")
    OLLAMA_CLIENT_AVAILABLE = False


# Add custom CSS for sidebar width detection
st.markdown("""
<style>
    [data-testid="stSidebar"] > div:first-child {
        width: var(--sidebar-width, 100%);
    }
    /* Add XAI visualization styling */
    .word-span {
        transition: transform 0.1s ease-in-out;
    }
    .word-span:hover {
        transform: scale(1.05);
    }
    iframe.xai-frame {
        border: none;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "selected_model_type" not in st.session_state:
    st.session_state.selected_model_type = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "model_timer" not in st.session_state:
    st.session_state.model_timer = Timer()
if "iteration_count" not in st.session_state:
    st.session_state.iteration_count = 0
if "last_input_time" not in st.session_state:
    st.session_state.last_input_time = datetime.datetime.now()
if "pdf_file" not in st.session_state:
    st.session_state.pdf_file = None
if "pdf_upload_time" not in st.session_state:
    st.session_state.pdf_upload_time = None
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = None
if "medical_processor" not in st.session_state:
    st.session_state.medical_processor = MedicalTermProcessor()
if "message_feedback" not in st.session_state:
    st.session_state.message_feedback = {}
if "stage" not in st.session_state:
    st.session_state.stage = "user"
    st.session_state.pending_prompt = None
    st.session_state.validation = {}
if "model_handler" not in st.session_state:
    st.session_state.model_handler = ModelHandler()
if "available_models" in st.session_state:
    del st.session_state.available_models
if "selected_model_name" not in st.session_state:
    st.session_state.selected_model_name = None
if "hf_model" not in st.session_state:
    st.session_state.hf_model = None
if "hf_tokenizer" not in st.session_state:
    st.session_state.hf_tokenizer = None
if "lime_explainer" not in st.session_state:
    st.session_state.lime_explainer = LIMEMedicalExplainer()
if "xai_queue" not in st.session_state:
    st.session_state.xai_queue = []
if "xai_processing" not in st.session_state:
    st.session_state.xai_processing = False
if "xai_results" not in st.session_state:
    st.session_state.xai_results = {}
if "xai_processor" not in st.session_state:
    st.session_state.xai_processor = XAIProcessor()
if "current_task" not in st.session_state:
    st.session_state.current_task = 1
if "task_completed" not in st.session_state:
    st.session_state.task_completed = []

# Initialize TaskManager in session state
if "task_manager" not in st.session_state:
    st.session_state.task_manager = TaskManager(total_tasks=3)

# Define the system prompt
system_prompt = "You are PromptDoctor, an AI-powered medical assistant designed to help healthcare professionals analyze clinical notes and provide medically relevant insights based on extracted information. Be concise, clear, and informative."

# Remove JavaScript section and replace with input focus handler
def on_input_focus():
    if st.session_state.input_start_time is None:
        st.session_state.input_start_time = datetime.datetime.now()

def save_feedback(index):
    """Save feedback for a specific message"""
    feedback_value = st.session_state[f"feedback_{index}"]
    
    # Map thumbs to feedback values (1 for thumbs up, -1 for thumbs down)
    feedback_text = {
        1: "positive",
        -1: "negative",
        0: "neutral"
    }.get(feedback_value, "neutral")
    
    st.session_state.message_feedback[index] = feedback_value
    
    # Log the feedback
    message = st.session_state.messages[index]
    log_chat_interaction(
        user_id=st.session_state.user_id,
        interaction_type="FEEDBACK",
        model_type=st.session_state.selected_model_type,
        user_prompt=message.get("raw_content", message.get("content")),
        model_output=message.get("content"),
        feedback=feedback_text
    )

def process_prompt(prompt, response_placeholder):
    """Process the accepted prompt and send to model"""
    current_time = datetime.datetime.now()
    typing_duration = (current_time - st.session_state.last_input_time).total_seconds()
    st.session_state.last_input_time = current_time
    st.session_state.iteration_count += 1
    
    # Process prompt for highlighting
    highlighted_prompt = st.session_state.medical_processor.highlight_medical_terms(prompt)
    
    # Add to message history
    message = {
        "role": "user",
        "content": highlighted_prompt,
        "raw_content": prompt,
        "user_id": st.session_state.user_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "iteration": st.session_state.iteration_count
    }
    st.session_state.messages.append(message)
    
    # Handle model response
    final_response = ""
    generation_duration = 0.0

    with st.spinner("Generating response..."):
        if st.session_state.selected_model_type == "Ollama":
            st.session_state.model_timer.start()
            try:
                payload = {
                    "model": "llama3-med42-8b",
                    "messages": [
                        {"role": "system", "content": system_prompt}
                    ] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                }
                response = requests.post("http://localhost:11434/api/chat", json=payload, stream=True)
                final_response = ""
                
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            final_response += content
                            response_placeholder.markdown(final_response)
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                final_response = f"Error: {e}"
                response_placeholder.markdown(final_response)

            generation_duration = st.session_state.model_timer.stop()
            
        elif st.session_state.selected_model_type == "GPT":
            st.session_state.model_timer.start()
            final_response = "GPT integration not implemented yet"
            response_placeholder.markdown(final_response)
            generation_duration = st.session_state.model_timer.stop()
            
        else:  # HuggingFace
            st.session_state.model_timer.start()
            final_response = "HuggingFace integration not implemented yet"
            response_placeholder.markdown(final_response)
            generation_duration = st.session_state.model_timer.stop()

        # Update response placeholder
        response_placeholder.markdown(final_response)

        # Save assistant's reply
        assistant_message = {
            "role": "assistant",
            "content": final_response,
            "user_id": st.session_state.user_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "iteration": st.session_state.iteration_count
        }
        st.session_state.messages.append(assistant_message)
        
        # Log interactions
        log_model_output(prompt, final_response, st.session_state.user_id)
        log_chat_interaction(
            st.session_state.user_id,
            "CHAT",
            user_prompt=prompt,
            model_output=final_response,
            model_type=st.session_state.selected_model_type,
            duration={
                "typing": typing_duration,
                "generation": generation_duration
            }
        )

        # Add feedback for new message
        current_message_index = len(st.session_state.messages) - 1
        st.feedback(
            "thumbs",
            key=f"feedback_{current_message_index}",
            on_change=save_feedback,
            args=[current_message_index],
        )

        # Update the interaction summary logging
        with open("user_logs.txt", "a") as f:
            f.write(f"{datetime.datetime.now()},{st.session_state.user_id},INTERACTION,{st.session_state.selected_model_type},iteration_{st.session_state.iteration_count},{typing_duration:.2f},{generation_duration:.2f}\n")

    return highlighted_prompt, final_response

def process_prompt_and_get_response(prompt):
    """Process prompt and get model response without creating chat messages"""
    current_time = datetime.datetime.now()
    typing_duration = (current_time - st.session_state.last_input_time).total_seconds()
    st.session_state.last_input_time = current_time
    st.session_state.iteration_count += 1
    
    highlighted_prompt = st.session_state.medical_processor.highlight_medical_terms(prompt)
    final_response = ""
    generation_duration = 0.0

    with st.spinner("Generating response..."):
        st.session_state.model_timer.start()
        
        if st.session_state.selected_model_type == "Ollama":
            # Combine all messages including system prompt and new user prompt
            all_messages = [{"role": "system", "content": system_prompt}]
            for m in st.session_state.messages:
                all_messages.append({
                    "role": m["role"],
                    "content": m.get("raw_content", m.get("content"))
                })
            all_messages.append({"role": "user", "content": prompt})
            
            # Verify model exists locally
            local_models = get_local_ollama_models()
            model_names = [m["name"] for m in local_models]
            
            if st.session_state.selected_model_name not in model_names:
                return highlighted_prompt, "Error: Selected model not found locally", 0, 0
            
            try:
                if OLLAMA_CLIENT_AVAILABLE:
                    # Try client first
                    try:
                        client = Client(host='http://localhost:11434')
                        response = client.chat(
                            model=st.session_state.selected_model_name,
                            messages=all_messages
                        )
                        final_response = response['message']['content']
                    except Exception as client_error:
                        print(f"[Ollama] Client error, falling back to API: {str(client_error)}")
                        raise  # Trigger fallback
                else:
                    raise ImportError("Ollama client not available")
                    
            except Exception as e:
                # Fallback to direct API call
                try:
                    payload = {
                        "model": st.session_state.selected_model_name,
                        "messages": all_messages
                    }
                    
                    response = requests.post(
                        "http://localhost:11434/api/chat",
                        json=payload,
                        stream=True,
                        timeout=30
                    )
                    
                    final_response = ""
                    for line in response.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if data.get("error"):
                                raise Exception(data["error"])
                            content = data.get("message", {}).get("content", "")
                            if content:
                                final_response += content
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                            
                except Exception as api_error:
                    final_response = f"Error with Ollama: {str(api_error)}"
        elif st.session_state.selected_model_type == "HuggingFace":
            try:
                if st.session_state.hf_model is None:
                    with st.spinner("Loading HuggingFace model..."):
                        model, tokenizer = ModelConfig.initialize_hf_model(st.session_state.selected_model_name)
                        st.session_state.hf_model = model
                        st.session_state.hf_tokenizer = tokenizer
                
                # Prepare prompt
                prompt_text = f"{system_prompt}\n\n"
                for msg in st.session_state.messages[-5:]:  # Limit context window
                    content = msg.get("raw_content", msg.get("content", ""))
                    prompt_text += f"{msg['role']}: {content}\n"
                prompt_text += f"user: {prompt}\nassistant:"
                
                # Tokenize
                inputs = st.session_state.hf_tokenizer(
                    prompt_text,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=512
                )
                
                # Generate using model's generation config
                outputs = st.session_state.hf_model.generate(
                    **inputs,
                    min_length=10,
                    repetition_penalty=1.2,
                    no_repeat_ngram_size=3,
                    early_stopping=True
                )
                
                final_response = st.session_state.hf_tokenizer.decode(
                    outputs[0], 
                    skip_special_tokens=True
                ).split("assistant:")[-1].strip()
                
            except Exception as e:
                final_response = f"Error with HuggingFace model: {str(e)}"
        else:
            final_response = "Model type not implemented"
        
        generation_duration = st.session_state.model_timer.stop()

    return highlighted_prompt, final_response, typing_duration, generation_duration

def get_medical_terms(text: str, medical_processor) -> List[str]:
    """Extract medical terms from text"""
    words = text.lower().split()
    return [word for word in words if word in medical_processor.medical_terms]

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


def show_chatbot():
    if "user_id" not in st.session_state or st.session_state.user_id is None:
        st.switch_page("pages/1_Login.py")
        return

    # Initialize task intro on first login
    if "first_login" not in st.session_state:
        st.session_state.first_login = True
        st.session_state.show_task_intro = True

    st.header("PromptDoctor")
    
    # Add custom CSS
    st.markdown("""
    <style>
        [data-testid="stSidebar"] > div:first-child {
            width: var(--sidebar-width, 100%);
        }
        .word-span {
            transition: transform 0.1s ease-in-out;
        }
        .word-span:hover {
            transform: scale(1.05);
        }
        iframe.xai-frame {
            border: none;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        # Show progress tracking in sidebar
        st.session_state.task_manager.render_progress_sidebar()
        
        st.divider()
        
        # Show other sidebar content
        st.text(f"User ID: {st.session_state.user_id}")
        st.text(f"Model: {st.session_state.selected_model_type}")
        if st.button("Logout"):
            st.switch_page("pages/4_Logout.py")
            
        # Add PDF upload section
        st.markdown("### Document Upload")
        uploaded_file = st.file_uploader(
            "Upload PDF file",
            type=["pdf"],
            help="Only PDF files are supported"
        )
        
        # Handle initial PDF upload
        if uploaded_file and uploaded_file != st.session_state.pdf_file:
            st.session_state.pdf_file = uploaded_file
            st.session_state.pdf_upload_time = datetime.datetime.now()
            
            # Process and log PDF upload
            pdf_data, extracted_text = handle_pdf_upload(
                uploaded_file,
                st.session_state.user_id,
                log_chat_interaction
            )
            st.session_state.pdf_text = extracted_text
        
        # Always display PDF if one is loaded
        if st.session_state.pdf_file:
            st.markdown("### Document Preview")
            pdf_container = st.container()
            with pdf_container:
                displayPDF(st.session_state.pdf_file, "100%")
            
            st.markdown("### Extracted Text")
            col1, col2 = st.columns([4, 1])
            with col1:
                text_area = st.text_area(
                    "Document Content",
                    value=st.session_state.pdf_text,
                    height=400,
                    disabled=True
                )
            with col2:
                if st.button("Copy", help="Copy text to clipboard"):
                    try:
                        pyperclip.copy(st.session_state.pdf_text)
                        st.success("Text copied")
                    except Exception as e:
                        st.error(f"Failed to copy: {str(e)}")
        
        # Add XAI results section
        st.markdown("### Analysis Queue")
        if st.session_state.xai_processing:
            st.info("🔄 Processing explanation...")
            st.session_state.xai_processor.process_queue()
        
        if st.session_state.xai_results:
            st.markdown("### Latest Analyses")
            for prompt, result in list(st.session_state.xai_results.items())[-3:]:
                with st.expander(f"Analysis for: {prompt[:30]}..."):
                    st.text(f"Timestamp: {result['timestamp']}")
                    st.markdown("#### Word Impact Analysis")
                    # Use iframe to properly render HTML with styles
                    st.components.v1.html(
                        result["html"],
                        height=180,
                        scrolling=True
                    )
                    st.markdown("#### Response")
                    st.write(result["response"])
                    
                    # Add explanation of colors
                    st.markdown("""
                        <small>
                        🔴 Red: Higher positive impact<br>
                        🔵 Blue: Higher negative impact<br>
                        Hover over words to see exact values
                        </small>
                    """, unsafe_allow_html=True)

                    if st.button("Remove", key=f"remove_{prompt[:10]}", type="tertiary"):
                        del st.session_state.xai_results[prompt]
                        st.rerun()

    # Show task controls in main UI
    st.session_state.task_manager.render_task_controls()
    
    # Show survey if needed
    current_task = st.session_state.current_task
    survey_data = st.session_state.task_manager.show_task_survey(current_task)
    if survey_data:
        log_task_completion(st.session_state.user_id, current_task, survey_data)
        st.session_state.task_manager.complete_task(current_task, survey_data)
        st.rerun()

    # Display chat history with proper feedback handling
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                feedback = st.session_state.message_feedback.get(i)
                st.feedback(
                    "thumbs",
                    key=f"feedback_{i}",
                    disabled=feedback is not None,
                    on_change=save_feedback,
                    args=[i],
                )

    # Single chat input handler with validation flow
    if prompt := st.chat_input("How can I help?", key="main_chat_input"):
        if st.session_state.stage == "user":
            # Store prompt and show validation
            st.session_state.pending_prompt = prompt
            st.session_state.stage = "validate"
            st.rerun()
    
    # Handle validation stages
    if st.session_state.stage == "validate":
        # Validate and highlight prompt
        sentences, highlighted, has_terms = validate_prompt(
            st.session_state.pending_prompt,
            st.session_state.medical_processor
        )
        
        # Display validation UI
        st.markdown(" ".join(highlighted))
        st.divider()
        
        # Log validation display
        medical_terms = get_medical_terms(st.session_state.pending_prompt, st.session_state.medical_processor)
        log_validation_action(
            st.session_state.user_id,
            "VALIDATION_VIEW",
            st.session_state.pending_prompt,
            medical_terms,
            medical_term_count=len(medical_terms)
        )
        
        cols = st.columns(4)  # Changed from 3 to 4 columns
        if cols[0].button("Edit", type="primary", key="edit_button"):
            log_validation_action(
                st.session_state.user_id,
                "EDIT_CLICK",
                st.session_state.pending_prompt
            )
            st.session_state.validation = {
                "sentences": sentences,
                "highlighted": highlighted,
                "has_terms": has_terms
            }
            st.session_state.stage = "edit"
            st.rerun()
        
        if cols[1].button("Accept", key="accept_button"):
            log_validation_action(
                st.session_state.user_id,
                "ACCEPT_CLICK",
                st.session_state.pending_prompt
            )
            # Get response first
            highlighted_prompt, final_response, typing_duration, generation_duration = process_prompt_and_get_response(
                st.session_state.pending_prompt
            )
            
            # Add messages to history
            user_message = {
                "role": "user",
                "content": highlighted_prompt,
                "raw_content": st.session_state.pending_prompt,
                "timestamp": datetime.datetime.now().isoformat(),
                "iteration": st.session_state.iteration_count
            }
            st.session_state.messages.append(user_message)
            
            assistant_message = {
                "role": "assistant",
                "content": final_response,
                "timestamp": datetime.datetime.now().isoformat(),
                "iteration": st.session_state.iteration_count
            }
            st.session_state.messages.append(assistant_message)
            
            # Log interactions
            log_chat_interaction(
                st.session_state.user_id,
                "CHAT",
                user_prompt=st.session_state.pending_prompt,
                model_output=final_response,
                model_type=st.session_state.selected_model_type,
                duration={
                    "typing": typing_duration,
                    "generation": generation_duration
                }
            )
            
            # Reset state and rerun
            st.session_state.stage = "user"
            st.session_state.pending_prompt = None
            st.rerun()
        
        if cols[2].button("Accept & Explain", type="secondary", key="explain_button"):
            log_validation_action(
                st.session_state.user_id,
                "EXPLAIN_CLICK",
                st.session_state.pending_prompt
            )
            
            print("\n[APP] Starting explanation process with debug...")
            start_time = datetime.datetime.now()
            
            # Get model response first
            highlighted_prompt, final_response, typing_duration, generation_duration = process_prompt_and_get_response(
                st.session_state.pending_prompt
            )
            
            # Queue XAI processing
            print("[APP] Queueing XAI request...")
            st.session_state.xai_processor.queue_xai_request(
                st.session_state.pending_prompt,
                final_response,
                st.session_state.selected_model_type
            )
            
            # Process queue once
            st.session_state.xai_processor.process_queue()
            
            # Add messages to history immediately
            user_message = {
                "role": "user",
                "content": highlighted_prompt,
                "raw_content": st.session_state.pending_prompt,
                "timestamp": datetime.datetime.now().isoformat(),
                "iteration": st.session_state.iteration_count
            }
            st.session_state.messages.append(user_message)
            
            assistant_message = {
                "role": "assistant",
                "content": final_response,
                "timestamp": datetime.datetime.now().isoformat(),
                "iteration": st.session_state.iteration_count
            }
            st.session_state.messages.append(assistant_message)
            
            # Log interactions
            print("[APP] Logging interaction...")
            log_chat_interaction(
                st.session_state.user_id,
                "CHAT_WITH_EXPLANATION_QUEUED",
                user_prompt=st.session_state.pending_prompt,
                model_output=final_response,
                model_type=st.session_state.selected_model_type,
                duration={
                    "typing": typing_duration,
                    "generation": generation_duration,
                    "queue_time": (datetime.datetime.now() - start_time).total_seconds()
                }
            )
            
            print("[APP] Chat message added, XAI processing queued")
            
            # Reset state and continue
            st.session_state.stage = "user"
            st.session_state.pending_prompt = None
            st.rerun()

        if cols[3].button("Rewrite", type="tertiary", key="rewrite_button"):
            st.session_state.stage = "rewrite"
            st.rerun()

    elif st.session_state.stage == "edit":
        with st.chat_message("user"):
            st.markdown(" ".join(st.session_state.validation["highlighted"]))
            st.divider()
            
            new_prompt = st.text_area(
                "Edit prompt:",
                value=st.session_state.pending_prompt
            )
            
            cols = st.columns(2)
            if cols[0].button("Update", type="primary"):
                log_validation_action(
                    st.session_state.user_id,
                    "EDIT_UPDATE",
                    st.session_state.pending_prompt,
                    modified_prompt=new_prompt,
                    highlighted_terms=get_medical_terms(new_prompt, st.session_state.medical_processor)
                )
                st.session_state.pending_prompt = new_prompt
                st.session_state.stage = "validate"
                st.rerun()
            
            if cols[1].button("Cancel"):
                st.session_state.stage = "validate"
                st.rerun()

    elif st.session_state.stage == "rewrite":
        with st.chat_message("user"):
            new_prompt = st.text_area(
                "Rewrite prompt:",
                value=st.session_state.pending_prompt
            )
            
            if st.button("Update", type="primary"):
                log_validation_action(
                    st.session_state.user_id,
                    "REWRITE_UPDATE",
                    st.session_state.pending_prompt,
                    modified_prompt=new_prompt,
                    highlighted_terms=get_medical_terms(new_prompt, st.session_state.medical_processor)
                )
                st.session_state.pending_prompt = new_prompt
                st.session_state.stage = "validate"
                st.rerun()

    elif st.session_state.stage == "viewing_explanation":
        if st.button("Continue", type="primary"):
            st.session_state.stage = "user"
            st.session_state.pending_prompt = None
            st.rerun()

show_chatbot()