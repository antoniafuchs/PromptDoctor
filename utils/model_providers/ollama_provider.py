import os
from pathlib import Path
import requests
import json
from .base import ModelProvider

class OllamaProvider(ModelProvider):
    DEFAULT_MODELS = [
        {"name": "llama2-medical", "display_name": "Llama 2 Medical"},
        {"name": "llama3-med42-8b", "display_name": "Med42 8B"}
    ]
    
    def __init__(self):
        self.current_model = None
        self.model_path = os.path.join(str(Path.home()), ".ollama/models")
    
    def get_available_models(self) -> List[Dict[str, str]]:
        try:
            # Check local models directory
            if os.path.exists(self.model_path):
                models = []
                lib_path = os.path.join(self.model_path, "manifests/registry.ollama.ai/library")
                if os.path.exists(lib_path):
                    for model_name in os.listdir(lib_path):
                        if os.path.isfile(os.path.join(lib_path, model_name)):
                            name = model_name.split(':')[0]
                            models.append({
                                "name": name,
                                "display_name": name
                            })
                return models or self.DEFAULT_MODELS
        except Exception:
            pass
        return self.DEFAULT_MODELS

    def initialize_model(self, model_name: str) -> None:
        self.current_model = model_name
        
    def generate_response(self, messages: List[Dict], system_prompt: str) -> str:
        try:
            payload = {
                "model": self.current_model,
                "messages": [{"role": "system", "content": system_prompt}] + messages
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
            
            return final_response
        except:
            return "Error: Could not generate response. Please make sure Ollama is running."
