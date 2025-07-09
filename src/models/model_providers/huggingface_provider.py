from typing import Dict, List
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from .base import ModelProvider

class HuggingFaceProvider(ModelProvider):
    DEFAULT_MODELS = [
        {"name": "microsoft/BioGPT-Large", "display_name": "BioGPT Large"},
        {"name": "starmpcc/Asclepius-7B", "display_name": "Asclepius 7B"}
    ]
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def get_available_models(self) -> List[Dict[str, str]]:
        return self.DEFAULT_MODELS
        
    def initialize_model(self, model_name: str) -> None:
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
    def generate_response(self, messages: List[Dict], system_prompt: str) -> str:
        if not self.model or not self.tokenizer:
            return "Model not initialized"
            
        # Combine messages into prompt
        prompt = f"{system_prompt}\n\n"
        for msg in messages:
            prompt += f"{msg['role']}: {msg['content']}\n"
        prompt += "assistant:"
        
        inputs = self.tokenizer(prompt, return_tensors="pt", padding=True).to(self.device)
        outputs = self.model.generate(
            **inputs,
            max_length=512,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True
        )
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response.split("assistant:")[-1].strip()
