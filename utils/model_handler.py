import requests
import json
from .model_config import ModelConfig

class ModelHandler:
    def __init__(self):
        self.model_type = None
        self.current_model = None
        self.hf_handler = None
    
    def initialize_model(self, model_type, model_name=None):
        """Initialize the selected model type and specific model"""
        self.model_type = model_type
        self.current_model = model_name
        
        if model_type == "HuggingFace" and model_name:
            # Lazy import and initialize HuggingFace handler
            from .huggingface_handler import HuggingFaceHandler
            self.hf_handler = HuggingFaceHandler()
            self.hf_handler.initialize_model(model_name)

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
        if not self.hf_handler:
            return "HuggingFace model not initialized"
        
        # Combine messages into a single prompt
        prompt = system_prompt + "\n\n"
        for msg in messages:
            role = msg["role"]
            content = msg.get("raw_content", msg.get("content", ""))
            prompt += f"{role}: {content}\n"
        prompt += "assistant:"
        
        return self.hf_handler.generate_response(prompt)
