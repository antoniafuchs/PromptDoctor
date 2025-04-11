import streamlit as st
import requests
import json

st.title("PromptDoctor")

# Initialize model in session state
if "ollama_model" not in st.session_state:
    st.session_state["ollama_model"] = "llama3-med42-8b"

# Initialize the chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Define system prompt
system_prompt = "You are PromptDoctor, an AI-powered medical assistant designed to help healthcare professionals analyze clinical notes and provide medically relevant insights based on extracted information. Be concise, clear, and informative."


# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle new user input
if prompt := st.chat_input("How can I help?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

     # Prepare the payload for Ollama API, including the system prompt
    payload = {
        "model": st.session_state["ollama_model"],
        "messages": [
            {"role": "system", "content": system_prompt}
        ] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    }

    # Send the request to Ollama API
    with st.chat_message("assistant"):
        st.write("Fetching response from Ollama...")

        try:
            response = requests.post("http://localhost:11434/api/chat", json=payload, stream=True)
            final_response = ""

            # Process streaming response and accumulate only final content
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")

                        # Accumulate content until final response is flagged as done
                        final_response += content

                        # Break if done
                        if data.get("done", False):
                            break

                    except json.JSONDecodeError as e:
                        st.write(f"JSON decoding error: {e}")
                        continue

            # Display the final response
            st.markdown(final_response.strip())

        except Exception as e:
            st.markdown(f"Unexpected error: {e}")

    # Save assistant's reply to session
    st.session_state.messages.append({"role": "assistant", "content": final_response})
