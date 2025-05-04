import numpy as np
from lime.lime_text import LimeTextExplainer
from typing import List, Tuple, Set
import streamlit as st
import requests
import json
import torch

class LIMEMedicalExplainer:
    def __init__(self):
        print("[LIME] Initializing explainer...")
        self.explainer = LimeTextExplainer(
            class_names=['not_relevant', 'relevant'],
            verbose=True,
            split_expression='\s+'  # Split on whitespace
        )
        
    def _get_model_response(self, text: str, model_name: str = "llama3-med42-8b") -> str:
        """Get response from Ollama model"""
        try:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": text}
                ]
            }
            response = requests.post(
                "http://localhost:11434/api/chat",
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                return response.json()["message"]["content"]
            return ""
        except Exception as e:
            print(f"[LIME] Model error: {e}")
            return ""

    def _predictor_fn(self, texts: List[str], medical_terms: Set[str]) -> np.ndarray:
        """Predict medical relevance for multiple texts"""
        try:
            predictions = []
            for text in texts:
                if st.session_state.model_handler is None:
                    raise ValueError("Model handler not initialized")
                
                if st.session_state.selected_model_type == "HuggingFace":
                    # Use HuggingFace model's confidence scores
                    if not st.session_state.hf_model:
                        raise ValueError("HuggingFace model not initialized")
                        
                    # Tokenize input
                    inputs = st.session_state.hf_tokenizer(
                        text,
                        return_tensors="pt",
                        padding=True,
                        truncation=True,
                        max_length=128
                    )
                    
                    # Get logits from model
                    with torch.no_grad():
                        outputs = st.session_state.hf_model(**inputs)
                        logits = outputs.logits
                        
                        # Calculate confidence score using softmax
                        probs = torch.nn.functional.softmax(logits[:, -1], dim=-1)
                        confidence = float(probs.mean())
                        predictions.append([1 - confidence, confidence])
                else:
                    # Fallback to basic medical term overlap for other models
                    response = st.session_state.model_handler.generate_response(
                        [{"role": "user", "content": text}],
                        system_prompt="You are a medical assistant."
                    )
                    
                    words = set(text.lower().split())
                    resp_words = set(response.lower().split())
                    medical_overlap = len((words | resp_words) & medical_terms)
                    score = min(0.1 + (medical_overlap * 0.2), 0.9)
                    predictions.append([1 - score, score])
                
            return np.array(predictions)
            
        except Exception as e:
            print(f"[LIME] Prediction error: {str(e)}")
            print("[LIME] Debug info:")
            print(f"Original text words: {[word for word in texts[0].split()]}")
            return np.array([[0.5, 0.5] for _ in texts])

    def explain_prediction(
        self, 
        text: str, 
        medical_terms: Set[str],
        num_features: int = 10,
        num_samples: int = 100
    ) -> Tuple[List[Tuple[str, float]], str]:
        """Generate and format LIME explanation"""
        try:
            print("[LIME] Starting explanation generation...")
            
            # Create predictor function with medical terms
            predictor = lambda x: self._predictor_fn(x, medical_terms)
            
            # Generate explanation
            exp = self.explainer.explain_instance(
                text,
                predictor,
                num_features=min(num_features, len(text.split())),
                num_samples=num_samples,
                labels=(1,)  # Only explain 'relevant' class
            )
            
            # Get feature importance list
            feature_importance = exp.as_list(label=1)
            
            # Format explanation for display
            explanation_text = []
            for word, importance in feature_importance:
                color = "red" if importance > 0 else "blue"
                explanation_text.append(f":{color}[{word}] ({importance:.3f})")
            
            print("[LIME] Explanation generated successfully")
            return feature_importance, " ".join(explanation_text)
            
        except Exception as e:
            import traceback
            error_msg = f"[LIME] Error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return [], f"Error generating explanation: {str(e)}"
