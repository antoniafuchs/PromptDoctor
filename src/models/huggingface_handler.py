"""
huggingface_handler.py
This file provides integration with Hugging Face models for PromptDoctor, including loading, inference, and management of Hugging Face models.
"""

import os

class HuggingFaceHandler:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        
    def initialize_model(self, model_name):
        """Lazy load model and tokenizer"""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        except Exception as e:
            print(f"Error loading HuggingFace model: {e}")
            
    def generate_response(self, prompt):
        """Generate response using HuggingFace model"""
        if not self.model or not self.tokenizer:
            return "HuggingFace model not initialized"
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt", padding=True)
            outputs = self.model.generate(
                **inputs,
                max_length=512,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True
            )
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response.split("assistant:")[-1].strip()
        except Exception as e:
            return f"Error generating response: {str(e)}"
