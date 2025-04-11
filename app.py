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

# Remove JavaScript section and replace with input focus handler
def on_input_focus():
    if st.session_state.input_start_time is None:
        st.session_state.input_start_time = datetime.datetime.now()

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

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle chat input
    if prompt := st.chat_input("How can I help?"):
        # Calculate typing duration for this interaction
        current_time = datetime.datetime.now()
        typing_duration = (current_time - st.session_state.last_input_time).total_seconds()
        st.session_state.last_input_time = current_time
        
        st.session_state.iteration_count += 1

        # Log user interaction with typing duration
        log_user_interaction(
            st.session_state.user_id,
            f"Iteration {st.session_state.iteration_count}: {prompt} (typing time: {typing_duration:.2f}s)"
        )
        
        # Display user message and add to history
        with st.chat_message("user"):
            st.markdown(prompt)
        
        message = {
            "role": "user",
            "content": prompt,
            "user_id": st.session_state.user_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "iteration": st.session_state.iteration_count
        }
        st.session_state.messages.append(message)

        # Create single message container for assistant
        with st.spinner("Generating response..."):
            # Show assistant message container
            assistant_container = st.chat_message("assistant")
            response_placeholder = assistant_container.empty()
            
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

                # Stop model timer and get generation duration
                generation_duration = st.session_state.model_timer.stop()

                # Log model output
                log_model_output(
                    prompt,
                    final_response,
                    st.session_state.user_id
                )

                # Log complete interaction with both durations
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

            elif st.session_state.selected_model_type == "GPT":
                # Start model timer
                st.session_state.model_timer.start()
                
                st.markdown("GPT integration not implemented yet")
                final_response = "GPT integration not implemented yet"
                
                # Stop model timer and get generation duration
                generation_duration = st.session_state.model_timer.stop()
                
                # Log complete interaction with both durations
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

            else:  # HuggingFace
                # Start model timer
                st.session_state.model_timer.start()
                
                st.markdown("HuggingFace integration not implemented yet")
                final_response = "HuggingFace integration not implemented yet"
                
                # Stop model timer and get generation duration
                generation_duration = st.session_state.model_timer.stop()
                
                # Log complete interaction with both durations
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

        # Save assistant's reply with iteration info
        assistant_message = {
            "role": "assistant",
            "content": final_response,
            "user_id": st.session_state.user_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "iteration": st.session_state.iteration_count
        }
        st.session_state.messages.append(assistant_message)

        # Update the interaction summary logging with separate durations
        with open("user_logs.txt", "a") as f:
            f.write(f"{datetime.datetime.now()},{st.session_state.user_id},INTERACTION,{st.session_state.selected_model_type},iteration_{st.session_state.iteration_count},{typing_duration:.2f},{generation_duration:.2f}\n")
