"""
LIME_Chatbot.py
This file implements the LIME Chatbot for PromptDoctor, providing model interpretability and explanation features via a chatbot interface.
"""

import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import requests
import json
import uuid
import datetime
import pyperclip
from typing import List
from tracking.metrics.timer import Timer
from tracking.logging import (
    log_model_output,
    log_task_duration,
    log_chat_interaction,
    log_validation_action,
    log_lime_explanation
)
from utils.pdf_handler import displayPDF, displayPDFpage, handle_pdf_upload
from medical.medical_processor import MedicalTermProcessor
from medical.prompt_validator import validate_prompt, add_highlights
from models.model_config import ModelConfig
from processing import XAIProcessor
import os
import glob
from threading import Thread
import pandas as pd
from utils.ml_utils import init_torch
from models.model_handler import ModelHandler
from streamlit_extras.switch_page_button import switch_page

# Initialize PyTorch with basic settings
init_torch()

# Try to import ollama, fallback to requests if not available
try:
    OLLAMA_CLIENT_AVAILABLE = True
except ImportError:
    print("[WARNING] Ollama client package not installed. Falling back to direct API calls.")
    OLLAMA_CLIENT_AVAILABLE = False

st.set_page_config(page_title="PromptDoctor", layout="wide")
st.header("PromptDoctor")

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

# NOTE: To use the --lime flag, run:
#   streamlit run src/LIME/LIME_Chatbot.py -- --lime
# Streamlit passes arguments after '--' to your script.

# Parse --lime flag
parser = argparse.ArgumentParser()
parser.add_argument('--lime', action='store_true')
args, _ = parser.parse_known_args()

# If --lime is set, configure study mode (Together API, no login)
if args.lime:
    st.session_state.study_mode = True
    st.session_state.selected_model_type = "Together"
    st.session_state.selected_model_name = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
    st.session_state.together_api_key = "tgp_v1_qMVnwAdRKPrsy0ASdwt2bMowEWAkz6q5X4XmUbGdRr8"
    os.environ["TOGETHER_API_KEY"] = st.session_state.together_api_key
    st.session_state.user_id = "lime_user"
    st.session_state.group = "B"
    # Initialize model handler with Together API configuration
    st.session_state.model_handler = ModelHandler()
    st.session_state.model_handler.initialize_model("Together", st.session_state.selected_model_name)
    # Optionally, set any other defaults needed for study mode

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
if "xai_queue" not in st.session_state:
    st.session_state.xai_queue = []
if "xai_processing" not in st.session_state:
    st.session_state.xai_processing = False
if "xai_results" not in st.session_state:
    st.session_state.xai_results = {}
if "xai_processor" not in st.session_state:
    st.session_state.xai_processor = XAIProcessor()

SYSTEM_PROMPT = """You are PromptDoctor, a specialized AI assistant for clinical and medical use.
Your core function is to assist healthcare professionals, medical students, and clinical researchers by analyzing clinical notes and medical case data, and generating medically accurate, relevant, and concise responses.

Key capabilities:

– Identify and extract key medical information (e.g., symptoms, diagnoses, treatments, lab values) from clinical notes.
– Provide differential diagnoses, treatment recommendations, or summaries based on structured and unstructured input.
– Support medical prompt optimization by highlighting which input elements significantly affect model output.
– Justify answers using medically valid reasoning and highlight any uncertainties or assumptions.

Your Responsibilities & Safety
– Always prioritize clinical safety and evidence-based practices.
– Avoid overconfidence: if information is missing or ambiguous, clearly state limitations or uncertainties.
– Do not fabricate clinical facts or suggest experimental treatments unless explicitly requested and labeled as such.
– Respect data privacy and do not request identifiable patient information.

Your Tone and Style:
– Be concise, clear, and professional.
– Tailor your explanations to the level of medical knowledge (e.g., differentiate between student-level and expert-level users if prompted).
– Use structured formats (e.g., bullet points, labeled sections) when possible to improve readability.
You have been fine-tuned for real-world clinical and educational contexts. Respond only to medically relevant tasks, and escalate or abstain when a question is beyond your scope or safety constraints."""

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
        action_type="FEEDBACK",  # Add the missing required argument
        interaction_type="FEEDBACK",
        model_type=st.session_state.selected_model_type,
        user_prompt=message.get("raw_content", message.get("content")),
        model_output=message.get("content"),
        feedback=feedback_text
    )

def process_prompt(prompt, response_placeholder):
    """Process the accepted prompt and send to model"""
    # Use the global system prompt instead of redefining it
    global SYSTEM_PROMPT
    
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
                        {"role": "system", "content": SYSTEM_PROMPT}
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
            
        elif st.session_state.selected_model_type == "HuggingFace":
            st.session_state.model_timer.start()
            final_response = "HuggingFace integration not implemented yet"
            response_placeholder.markdown(final_response)
            generation_duration = st.session_state.model_timer.stop()
            
        elif st.session_state.selected_model_type == "Together":
            # Use the model handler for Together API
            st.session_state.model_timer.start()
            try:
                model_handler = st.session_state.model_handler
                messages = [{"role": m["role"], "content": m.get("raw_content", m.get("content"))} for m in st.session_state.messages]
                final_response = model_handler.generate_response(
                    messages, SYSTEM_PROMPT
                )
                response_placeholder.markdown(final_response)
            except Exception as e:
                final_response = f"Error: {e}"
                response_placeholder.markdown(final_response)
            generation_duration = st.session_state.model_timer.stop()
        else:
            final_response = "Model type not implemented"
            response_placeholder.markdown(final_response)
            generation_duration = 0.0

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
    # Use the global system prompt instead of redefining it
    global SYSTEM_PROMPT
    
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
            all_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
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
                prompt_text = f"{SYSTEM_PROMPT}\n\n"
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
        elif st.session_state.selected_model_type == "Together":
            try:
                # Ensure model handler is initialized for Together API
                if not st.session_state.model_handler or not hasattr(st.session_state.model_handler, 'current_model') or not st.session_state.model_handler.current_model:
                    st.session_state.model_handler.initialize_model("Together", st.session_state.selected_model_name)
                
                model_handler = st.session_state.model_handler
                messages = [{"role": m["role"], "content": m.get("raw_content", m.get("content"))} for m in st.session_state.messages]
                messages.append({"role": "user", "content": prompt})
                final_response = model_handler.generate_response(
                    messages, SYSTEM_PROMPT
                )
            except Exception as e:
                final_response = f"Error with Together API: {str(e)}"
                st.error(f"Together API error: {str(e)}")
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
    # Only require login if not in lime/study mode
    if not getattr(st.session_state, "study_mode", False):
        if "user_id" not in st.session_state or st.session_state.user_id is None:
            st.warning("You are not logged in. Please go to the Login page.")
            st.stop()
            return


    # Sidebar
    with st.sidebar:
        st.text(f"User ID: {st.session_state.user_id}")
        st.text(f"Model: {st.session_state.selected_model_type}")
        if st.button("Logout"):
            switch_page("Logout Survey")
        
        # Add PDF upload section - Fixed indentation to be outside the if statement
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
            st.info("Processing explanation...")
            st.session_state.xai_processor.process_queue()
        
        if st.session_state.xai_results:
            st.markdown("### Latest Analyses")
            for prompt, result in list(st.session_state.xai_results.items())[-3:]:
                with st.expander(f"Analysis for: {prompt[:30]}..."):
                    #st.text(f"Timestamp: {result['timestamp']}")
                    # Use iframe to properly render HTML with styles
                    st.components.v1.html(
                        result["html"],
                        height=180,
                        scrolling=True
                    )
                    
                    # Add explanation of colors
                    st.markdown("""
                        <div class="highlight-explanation" style="margin-top: 15px; line-height: 1.6; font-size: 12px;">
                            <span class="highlight-legend-red" style="color: rgb(220, 53, 69); font-weight: 600;">Red highlights</span> show the words with the highest impact on the model's answer. They boost its confidence the most.<br>
                            <span class="highlight-legend-blue" style="color: rgb(0, 123, 255); font-weight: 600;">Blue highlights</span> show the words with the lowest impact. They lower its confidence the most.<br>
                        </div>
                    """, unsafe_allow_html=True)

                    if st.button("Remove", key=f"remove_{prompt[:10]}", type="tertiary"):
                        del st.session_state.xai_results[prompt]
                        st.rerun()

    # System prompt
    SYSTEM_PROMPT = "You are PromptDoctor, an AI-powered medical assistant designed to help healthcare professionals analyze clinical notes and provide medically relevant insights based on extracted information. Be concise, clear, and informative."

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
            
            # Process queue immediately and show results
            print("[APP] Processing XAI request...")
            result = st.session_state.xai_processor.process_queue_immediately()
            
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
            
            # Show the explanation immediately
            if result and 'html' in result:
                st.markdown("### Prompt Impact Analysis")
                st.components.v1.html(result['html'], height=350, scrolling=True)
                
                # Display saved HTML file path if available
                if 'html_path' in result and result['html_path']:
                    html_path = result['html_path']
                    st.success(f"Analysis saved to: {os.path.basename(html_path)}")
                
                # Log LIME explanation
                log_lime_explanation(
                    st.session_state.user_id, 
                    st.session_state.current_task if 'current_task' in st.session_state else 0,
                    st.session_state.pending_prompt, 
                    result
                )
            
            print("[APP] Chat message added, XAI processing complete")
            
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

    # Add section in sidebar to show saved HTML files
    with st.sidebar:
        # ...existing code...
        
        # Show HTML results directory
        if "xai_processor" in st.session_state and hasattr(st.session_state.xai_processor, "get_html_results_dir"):
            html_dir = st.session_state.xai_processor.get_html_results_dir()
            if os.path.exists(html_dir):
                st.markdown("### Saved Analyses")
                html_files = [f for f in os.listdir(html_dir) if f.endswith('.html')]
                if html_files:
                    st.text(f"{len(html_files)} saved analyses")
                    if st.button("Open Results Folder"):
                        # Try to open the folder in file explorer
                        try:
                            import subprocess
                            if os.name == 'nt':  # Windows
                                os.startfile(html_dir)
                            elif os.name == 'posix':  # macOS/Linux
                                subprocess.call(['open', html_dir])
                            st.success("Opened results folder")
                        except Exception as e:
                            st.error(f"Couldn't open folder: {e}")
                else:
                    st.text("No saved analyses yet")

show_chatbot()