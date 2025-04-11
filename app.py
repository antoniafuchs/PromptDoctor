import streamlit as st
import requests
import json
import uuid
import datetime
from tracking.timer import Timer
from tracking.logging import (
    log_model_output,
    log_user_interaction,
    log_task_duration,
    log_chat_interaction
)

st.title("PromptDoctor")

# Initialize session state variables
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "selected_model_type" not in st.session_state:
    st.session_state.selected_model_type = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "interaction_timer" not in st.session_state:
    st.session_state.interaction_timer = Timer()
if "model_timer" not in st.session_state:
    st.session_state.model_timer = Timer()
if "iteration_count" not in st.session_state:
    st.session_state.iteration_count = 0

# Add JavaScript to detect input field focus
st.markdown("""
    <script>
        // Start timer when input field is focused
        const inputField = document.querySelector('.stTextInput input');
        if (inputField) {
            inputField.addEventListener('focus', function() {
                window.parent.postMessage({type: 'startInputTimer'}, '*');
            });
        }
    </script>
    """, unsafe_allow_html=True)

# Handle custom events from JavaScript
if st.session_state.get('input_focused'):
    st.session_state.interaction_timer.start()

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

    # System prompt
    system_prompt = "You are PromptDoctor, an AI-powered medical assistant designed to help healthcare professionals analyze clinical notes and provide medically relevant insights based on extracted information. Be concise, clear, and informative."

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle new user input
    if prompt := st.chat_input("How can I help?"):
        # Stop interaction timer and get typing duration
        typing_duration = st.session_state.interaction_timer.stop()
        
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


        # Handle different model types
        with st.chat_message("assistant"):
            with st.spinner("Generating response..."):
                if st.session_state.selected_model_type == "Ollama":
                    # Start model timer
                    st.session_state.model_timer.start()
                    
                    payload = {
                        "model": "llama3-med42-8b",
                        "messages": [
                            {"role": "system", "content": system_prompt}
                        ] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                    }
                    try:
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
                        st.markdown(final_response.strip())
                    except Exception as e:
                        st.markdown(f"Error: {e}")
                        final_response = str(e)

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
                    st.markdown("GPT integration not implemented yet")
                    final_response = "GPT integration not implemented yet"
                    duration = st.session_state.timer.stop()
                    log_chat_interaction(
                        st.session_state.user_id,
                        "CHAT",
                        user_prompt=prompt,
                        model_output=final_response,
                        model_type=st.session_state.selected_model_type,
                        duration=duration
                    )

                else:  # HuggingFace
                    st.markdown("HuggingFace integration not implemented yet")
                    final_response = "HuggingFace integration not implemented yet"
                    duration = st.session_state.timer.stop()
                    log_chat_interaction(
                        st.session_state.user_id,
                        "CHAT",
                        user_prompt=prompt,
                        model_output=final_response,
                        model_type=st.session_state.selected_model_type,
                        duration=duration
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

        # Stop timer and log duration
        duration = st.session_state.timer.stop()
        log_task_duration(
            prompt,
            duration,
            st.session_state.user_id
        )

        # Log interaction summary
        with open("user_logs.txt", "a") as f:
            f.write(f"{datetime.datetime.now()},{st.session_state.user_id},INTERACTION,{st.session_state.selected_model_type},iteration_{st.session_state.iteration_count},{duration:.2f}s\n")
