import numpy as np
from lime.lime_text import LimeTextExplainer

class LIMEMedicalExplainer:
    def __init__(self):
        print("[LIME] Initializing explainer...")
        self.explainer = LimeTextExplainer(
            class_names=['negative', 'positive'],  # Using binary classification
            split_expression='\s+'  # Split on whitespace
        )
        
    def explain_prediction(self, model_output: str, original_text: str, num_features=10):
        """Explain a model's prediction using LIME"""
        print(f"[LIME] Processing text: {original_text[:100]}...")
        
        try:
            # Define predictor that returns probability distributions
            def predictor(texts):
                print(f"[LIME] Analyzing {len(texts)} samples...")
                predictions = []
                for text in texts:
                    # Create probability distribution [negative, positive]
                    # Using simple word overlap as similarity
                    text_words = set(text.lower().split())
                    orig_words = set(original_text.lower().split())
                    similarity = len(text_words.intersection(orig_words)) / max(len(orig_words), 1)
                    predictions.append([1 - similarity, similarity])  # [neg_prob, pos_prob]
                return np.array(predictions)
            
            print("[LIME] Generating explanation...")
            exp = self.explainer.explain_instance(
                original_text, 
                predictor,
                num_features=min(num_features, 20),  # Limit max features
                num_samples=500,  # Increase samples
                top_labels=1  # Only explain top class
            )
            
            # Get explanation for positive class (index 1)
            print("[LIME] Processing explanation...")
            exp_list = exp.as_list(label=1)  # Get positive class explanations
            
            # Format explanation with weights
            explanation = []
            for word, weight in exp_list:
                if abs(weight) < 0.01:  # Filter out very small weights
                    continue
                color = "red" if weight > 0 else "blue"
                explanation.append(f":{color}[{word}] ({weight:.3f})")
            
            formatted = " ".join(explanation) if explanation else "No significant features found"
            print("[LIME] Explanation generated successfully")
            print(f"[LIME] Found {len(explanation)} significant features")
            return formatted
            
        except Exception as e:
            import traceback
            error_msg = f"LIME Error: {str(e)}\n{traceback.format_exc()}"
            print(f"[LIME] {error_msg}")
            return error_msg
