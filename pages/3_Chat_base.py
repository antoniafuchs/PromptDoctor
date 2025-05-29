from multiprocessing.connection import Client
import streamlit as st
import asyncio
import os
import glob
import json
import uuid
import datetime
import pyperclip
import requests
import pandas as pd
from typing import List

# Set event loop policy for thread safety
try:
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except AttributeError:
    # Not on Windows, use default policy
    pass

# Initialize event loop
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Try to import ollama
try:
    from langchain.llms import Ollama
    OLLAMA_CLIENT_AVAILABLE = True
except ImportError:
    print("[WARNING] Ollama client package not installed. Falling back to direct API calls.")
    OLLAMA_CLIENT_AVAILABLE = False

# Page config must be first Streamlit command
st.set_page_config(
    page_title="PromptDoctor",
    layout="wide"
)


# Import remaining modules
from utils.style_loader import load_styles
import requests
import json
import uuid
import datetime
import pyperclip
from typing import List
from tracking.timer import Timer
from tracking.logging import (
    log_chat_interaction,
    log_validation_action,
    log_task_completion,
    log_feedback,
    log_task_duration,
    log_lime_explanation,
    log_model_output
)
from tracking.task_manager import TaskManager 
from utils.pdf_handler import displayPDF, displayPDFpage, handle_pdf_upload
from utils.medical_processor import MedicalTermProcessor
from utils.model_config import ModelConfig
from utils.xai import LIMEMedicalExplainer
from utils.xai.processing import XAIProcessor
import os
import glob
from threading import Thread
import pandas as pd
from utils.ml_utils import init_torch, get_device
from utils.model_handler import ModelHandler
from streamlit_extras.switch_page_button import switch_page
import streamlit_survey as ss 

# Initialize PyTorch with basic settings - safer initialization
try:
    from utils.ml_utils import init_torch, get_device
    # Initialize PyTorch in a way that avoids event loop errors
    init_torch()
except ImportError as e:
    print(f"[WARNING] Error importing PyTorch utilities: {str(e)}")
    # Create fallback functions if import fails
    def init_torch():
        return "PyTorch initialization skipped"
    def get_device():
        return "cpu"
    init_torch()
except Exception as e:
    print(f"[WARNING] Error during PyTorch initialization: {str(e)}")

# Load shared styles
load_styles()

# Add custom CSS for sidebar width detection and font sizes
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
    
    /* Ensure clinical notes and survey questions have 18px font size */
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stRadio"] label,
    div[data-testid="stRadio"] div,
    div[data-testid="stTextArea"] label,
    div[data-testid="stTextArea"] textarea,
    .clinical-note, .clinical-note div, .clinical-note span, .clinical-note p {
        font-size: 18px !important;
    }
    
    /* Fix highlighted terms font size */
    span[style*="display: inline-block"], 
    span[class*="highlight"] {
        font-size: 18px !important;
    }
    
    /* Task description styling */
    div[style*="background-color: rgb(231, 245, 255)"] p,
    div[style*="background-color: rgb(231, 245, 255)"] {
        font-size: 18px !important;
    }
    
    /* Clinical note bold text */
    .clinical-note strong, strong {
        font-size: 18px !important;
    }
    
    /* Chat message styling */
    div[data-testid="stChatMessage"] p {
        font-size: 18px !important;
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
system_prompt = """You are PromptDoctor, a specialized AI assistant for clinical and medical use.
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
    # Check if feedback already exists for this message
    if (index in st.session_state.message_feedback or 
        st.session_state.get(f"feedback_{index}_submitted", False)):
        return
        
    feedback_value = st.session_state[f"feedback_{index}"]
    message = st.session_state.messages[index]
    message_id = f"msg_{index}"
    
    # Map thumbs to feedback values (1 for thumbs up, -1 for thumbs down)
    feedback_text = {
        1: "positive",
        -1: "negative",
        0: "neutral"
    }.get(feedback_value, "neutral")
    
    st.session_state.message_feedback[index] = feedback_value
    st.session_state[f"feedback_{index}_submitted"] = True
    
    # Find the associated prompt and response
    # We need to find the user message that preceded this assistant message
    prompt = ""
    if index > 0 and message["role"] == "assistant":
        # Find the most recent user message
        for i in range(index-1, -1, -1):
            if st.session_state.messages[i]["role"] == "user":
                prompt = st.session_state.messages[i].get("raw_content", st.session_state.messages[i].get("content", ""))
                break
    else:
        # If this is not an assistant message, use the current message content as prompt
        prompt = message.get("raw_content", message.get("content", ""))
    
    # Get the response if this is an assistant message
    response = message.get("content", "") if message["role"] == "assistant" else ""
    
    # Log the feedback with both prompt and response for better context
    log_feedback(
        user_id=st.session_state.user_id,
        task_id=st.session_state.current_task,
        message_id=message_id,
        feedback_value=feedback_value,
        prompt=prompt,
        response=response
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
        log_chat_interaction(
            user_id=st.session_state.user_id,
            action_type="MODEL_OUTPUT",
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

        # Remove obsolete logging to user_logs.txt
        
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
        
        if st.session_state.selected_model_type == "HuggingFaceEndpoint":
            try:
                headers = {
                    "Authorization": f"Bearer {st.session_state.hf_api_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                
                # Create conversation context
                conversation = f"{system_prompt}\n\n"
                for msg in st.session_state.messages[-5:]:
                    content = msg.get("raw_content", msg.get("content", ""))
                    conversation += f"{msg['role']}: {content}\n"
                conversation += f"user: {prompt}\nassistant:"
                
                payload = {
                    "inputs": conversation,
                    "parameters": {
                        "max_new_tokens": 25,
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "do_sample": True,
                        "return_full_text": False
                    }
                }
                
                # Use session with longer timeout
                session = requests.Session()
                retry_count = 0
                max_retries = 3
                
                while retry_count < max_retries:
                    try:
                        response = session.post(
                            st.session_state.endpoint_url,
                            headers=headers,
                            json=payload,
                            timeout=90
                        )
                        response.raise_for_status()
                        final_response = response.json()[0]["generated_text"]
                        break
                    except requests.Timeout:
                        retry_count += 1
                        if retry_count == max_retries:
                            final_response = "Error: Request timed out after multiple retries"
                        continue
                    except Exception as e:
                        final_response = f"Error with HuggingFace endpoint: {str(e)}"
                        break
                
            except Exception as e:
                final_response = f"Error with HuggingFace endpoint: {str(e)}"
                
        elif st.session_state.selected_model_type == "Ollama":
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
        elif st.session_state.selected_model_type == "Together":
            try:
                # Import together API
                try:
                    from together import Together
                    together_available = True
                except ImportError:
                    together_available = False
                    final_response = "Error: Together package not installed. Install with 'pip install together'"
                    return highlighted_prompt, final_response, typing_duration, generation_duration
                
                if together_available:
                    # Initialize client if needed
                    api_key = st.session_state.get("together_api_key")
                    
                    if api_key:
                        client = Together(api_key=api_key)
                        # Also set environment variable as backup
                        os.environ["TOGETHER_API_KEY"] = api_key
                    else:
                        # Try to use environment variable
                        if "TOGETHER_API_KEY" not in os.environ:
                            final_response = "Error: Together API key not found. Please set the TOGETHER_API_KEY environment variable or provide it via the UI."
                            return highlighted_prompt, final_response, typing_duration, generation_duration
                        client = Together()
                    
                    # Prepare messages
                    formatted_messages = [
                        {"role": "system", "content": system_prompt}
                    ]
                    
                    # Add conversation history (last few messages)
                    for m in st.session_state.messages[-5:]:
                        formatted_messages.append({
                            "role": m["role"],
                            "content": m.get("raw_content", m.get("content"))
                        })
                    
                    # Add current prompt
                    formatted_messages.append({"role": "user", "content": prompt})
                    
                    # Get response
                    try:
                        response = client.chat.completions.create(
                            model=st.session_state.selected_model_name,
                            messages=formatted_messages,
                            max_tokens=1024,
                            temperature=0.7,
                            stream=False
                        )
                        
                        if hasattr(response, 'choices') and len(response.choices) > 0:
                            final_response = response.choices[0].message.content
                        else:
                            final_response = "No response generated"
                    except Exception as e:
                        final_response = f"Error calling Together API: {str(e)}"
            except Exception as e:
                final_response = f"Error with Together API: {str(e)}"
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
        st.switch_page("Home.py")
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
        
    # Show task controls in main UI
    st.session_state.task_manager.render_task_controls()
    
    # Show survey if needed
    current_task = st.session_state.current_task
    survey_data = st.session_state.task_manager.show_task_survey(current_task)
    if survey_data:
        # Calculate task duration from start time
        task = st.session_state.task_states[current_task - 1]
        if task.started_at:
            duration = (datetime.datetime.now() - task.started_at).total_seconds()
        else:
            duration = 0.0
            
        # Add duration to survey data
        survey_data['task_duration'] = duration
        survey_data['start_time'] = task.started_at.isoformat() if task.started_at else None
        survey_data['end_time'] = datetime.datetime.now().isoformat()
            
        # Log completion with duration
        log_task_completion(
            st.session_state.user_id, 
            current_task, 
            survey_data,
            duration
        )
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
                    # Only disable if feedback already given for this specific message
                    disabled=feedback is not None,
                    on_change=save_feedback,
                    args=[i],
                )

    # Direct chat input handling without validation
    if prompt := st.chat_input("How can I help?", key="main_chat_input"):
        # Hide task intro
        st.session_state.show_task_intro = False
        
        # Track the prompt submission for the current task
        st.session_state.task_manager.track_prompt_submission(
            st.session_state.current_task, 
            prompt
        )
        
        # Immediately show user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response
        highlighted_prompt, final_response, typing_duration, generation_duration = process_prompt_and_get_response(prompt)
        
        # Add messages to history (user message was already displayed)
        user_message = {
            "role": "user",
            "content": prompt,
            "raw_content": prompt,
            "timestamp": datetime.datetime.now().isoformat(),
            "iteration": st.session_state.iteration_count
        }
        st.session_state.messages.append(user_message)
        
        # Show assistant message with streaming effect
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            for i in range(len(final_response)):
                message_placeholder.markdown(final_response[:i+1])
        
        # Add assistant message to history
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
            user_prompt=prompt,
            model_output=final_response,
            model_type=st.session_state.selected_model_type,
            duration={
                "typing": typing_duration,
                "generation": generation_duration
            }
        )
        st.rerun()

show_chatbot()