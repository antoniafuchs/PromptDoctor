import numpy as np
from lime.lime_text import LimeTextExplainer
from typing import List, Tuple, Set
import requests
import json

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
        predictions = []
        print(f"[LIME] Processing {len(texts)} samples...")
        
        for text in texts:
            try:
                # Get model response for text
                response = self._get_model_response(text)
                
                # Convert text and response to word sets
                text_words = set(text.lower().split())
                resp_words = set(response.lower().split())
                
                # Calculate medical term overlap
                medical_overlap = len((text_words | resp_words) & medical_terms)
                
                # Calculate relevance probability
                if medical_overlap > 0:
                    relevance = min(0.5 + (medical_overlap * 0.1), 0.9)
                else:
                    relevance = 0.1
                    
                predictions.append([1 - relevance, relevance])
                
            except Exception as e:
                print(f"[LIME] Prediction error: {e}")
                predictions.append([0.5, 0.5])  # Default to uncertain prediction
                
        return np.array(predictions)

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
