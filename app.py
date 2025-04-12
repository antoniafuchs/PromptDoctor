import streamlit as st
import requests
import json
import uuid
import datetime
import pyperclip
from tracking.timer import Timer
from tracking.logging import (
    log_model_output,
    log_user_interaction,
    log_task_duration,
    log_chat_interaction
)
from utils.pdf_handler import displayPDF, displayPDFpage, handle_pdf_upload
from utils.medical_processor import MedicalTermProcessor
from utils.prompt_validator import validate_prompt, add_highlights

st.set_page_config(page_title="PromptDoctor", layout="wide")
st.header("PromptDoctor")

# Add custom CSS for sidebar width detection
st.markdown("""
<style>
    [data-testid="stSidebar"] > div:first-child {
        width: var(--sidebar-width, 100%);
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
    
    # Process prompt for highlighting
    highlighted_prompt = st.session_state.medical_processor.highlight_medical_terms(prompt)
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
                    ] + [{"role": m["role"], "content": m.get("raw_content", m.get("content"))} for m in st.session_state.messages]
                }
                # Add the current prompt
                payload["messages"].append({"role": "user", "content": prompt})
                
                response = requests.post("http://localhost:11434/api/chat", json=payload, stream=True)
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
                            
            except Exception as e:
                final_response = f"Error: {e}"

            generation_duration = st.session_state.model_timer.stop()
            
        elif st.session_state.selected_model_type == "GPT":
            # ...existing GPT code...
            pass
            
        else:  # HuggingFace
            # ...existing HuggingFace code...
            pass

    return highlighted_prompt, final_response, typing_duration, generation_duration

# Login page
if st.session_state.user_id is None:
    st.markdown("### Welcome to PromptDoctor")
    st.markdown("Please login and select your preferred model")
    
    # Model selection
    model_type = st.selectbox(
        "Select Model Type",
        ["Ollama", "GPT", "HuggingFace"],
        key="model_selection"
    )
    
    if st.button("Login"):
        st.session_state.user_id = str(uuid.uuid4())
        st.session_state.selected_model_type = model_type
        # Log login event
        log_chat_interaction(
            st.session_state.user_id,
            "LOGIN",
            model_type=model_type
        )
        st.rerun()

# Main chat interface
else:
    # Sidebar with user info and model selection
    with st.sidebar:
        st.text(f"User ID: {st.session_state.user_id}")
        st.text(f"Model: {st.session_state.selected_model_type}")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
        
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

    # System prompt
    system_prompt = "You are PromptDoctor, an AI-powered medical assistant designed to help healthcare professionals analyze clinical notes and provide medically relevant insights based on extracted information. Be concise, clear, and informative."

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
        
        cols = st.columns(3)
        if cols[0].button("Edit", type="primary", key="edit_button"):
            st.session_state.validation = {
                "sentences": sentences,
                "highlighted": highlighted,
                "has_terms": has_terms
            }
            st.session_state.stage = "edit"
            st.rerun()
        
        if cols[1].button("Accept", key="accept_button"):
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
        
        if cols[2].button("Rewrite", type="tertiary", key="rewrite_button"):
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
                st.session_state.pending_prompt = new_prompt
                st.session_state.stage = "validate"
                st.rerun()
