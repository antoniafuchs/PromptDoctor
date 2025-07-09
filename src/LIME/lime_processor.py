import numpy as np
from lime.lime_text import LimeTextExplainer
from typing import List, Callable, Dict, Any
import streamlit as st
import html
import os

class LIMEProcessor:
    def __init__(self):
        """Initialize LIME processor with aligned tokenization"""
        self.explainer = LimeTextExplainer(
            class_names=["Low Impact", "High Impact"],
            split_expression=lambda x: x.split(),  # Match simple word splitting
            bow=False  # Keep position-aware tokenization
        )
        
        # Load medical terms from dataset for better relevance assessment
        try:
            from datasets import load_dataset
            terms = load_dataset("gamino/wiki_medical_terms", split="train")["term"]
            self.med_terms = set(t.lower() for t in terms)
            print(f"[LIME] Loaded {len(self.med_terms)} medical terms from dataset")
        except Exception as e:
            print(f"[LIME] Could not load medical terms dataset: {e}")
            # Fallback to a minimal set of common medical terms
            self.med_terms = set([
                "diagnosis", "treatment", "symptoms", "disease", "patient", 
                "condition", "medication", "medical", "clinical", "health"
            ])
            print(f"[LIME] Using fallback medical terms: {len(self.med_terms)} terms")
        
        print("[LIME] Processor initialized")

    def create_predictor(self, model_type: str) -> Callable:
        """Create model-specific prediction function"""
        if model_type == "Ollama":
            return self._ollama_predictor
        elif model_type == "HuggingFace":
            return self._huggingface_predictor
        elif model_type == "Together":
            return self._together_predictor
        else:
            return self._default_predictor
    
    def _ollama_predictor(self, texts: List[str]) -> np.ndarray:
        """Improved Ollama prediction function with medical term relevance"""
        import requests
        probs = []
        
        for text in texts:
            try:
                response = requests.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": st.session_state.selected_model_name,
                        "messages": [{"role": "user", "content": text}],
                        "stream": False
                    }
                ).json()
                
                response_text = response.get("message", {}).get("content", "")
                
                # Better relevance calculation using medical terms
                input_words = set(text.lower().split())
                response_words = set(response_text.lower().split())
                
                # Calculate medical term relevance
                prompt_med_terms = set(w for w in input_words if w in self.med_terms)
                if not prompt_med_terms:
                    # Fallback to general word overlap if no medical terms found
                    word_overlap = len(input_words.intersection(response_words))
                    confidence = min((word_overlap / len(input_words) if input_words else 0.5) + 0.2, 1.0)
                else:
                    # Calculate how many prompt medical terms are covered in response
                    response_coverage = sum(1 for w in response_words if w in prompt_med_terms)
                    confidence = min((response_coverage / (len(prompt_med_terms) + 1e-5)) + 0.2, 1.0)
                
                probs.append([1 - confidence, confidence])
                
            except Exception as e:
                print(f"[LIME] Prediction error: {str(e)}")
                probs.append([0.5, 0.5])
                
        return np.array(probs)
    
    def _huggingface_predictor(self, texts: List[str]) -> np.ndarray:
        """Prediction function for HuggingFace models with improved medical term relevance"""
        predictions = []
        
        for text in texts:
            try:
                # Get model response using HF model
                response = st.session_state.model_handler.hf_handler.generate_response(text)
                
                # Calculate relevance based on medical terms
                input_words = set(text.lower().split())
                response_words = set(response.lower().split())
                
                # Calculate medical term relevance
                prompt_med_terms = set(w for w in input_words if w in self.med_terms)
                if not prompt_med_terms:
                    # Fallback to general word overlap if no medical terms found
                    word_overlap = len(input_words.intersection(response_words))
                    confidence = min((word_overlap / len(input_words) if input_words else 0.5) + 0.2, 1.0)
                else:
                    # Calculate how many prompt medical terms are covered in response
                    response_coverage = sum(1 for w in response_words if w in prompt_med_terms)
                    confidence = min((response_coverage / (len(prompt_med_terms) + 1e-5)) + 0.2, 1.0)
                
                predictions.append([1 - confidence, confidence])
                
            except Exception as e:
                print(f"[LIME] HF Prediction error: {e}")
                predictions.append([0.5, 0.5])
        
        return np.array(predictions)
    
    def _together_predictor(self, texts: List[str]) -> np.ndarray:
        """Prediction function for Together API models with improved error handling and medical term relevance"""
        try:
            from together import Together
        except ImportError:
            print("[LIME] Together API not available. Install with: pip install together")
            return np.array([[0.5, 0.5] for _ in texts])
            
        predictions = []
        
        # Get API key from session state or environment
        api_key = st.session_state.get("together_api_key")
        if api_key:
            client = Together(api_key=api_key)
        else:
            # Try to use environment variable
            if "TOGETHER_API_KEY" not in os.environ:
                print("[LIME] Together API key not found.")
                return np.array([[0.5, 0.5] for _ in texts])
            client = Together()
        
        for text in texts:
            try:
                # Get model response using Together API
                response = client.chat.completions.create(
                    model=st.session_state.selected_model_name,
                    messages=[{"role": "user", "content": text}],
                    max_tokens=256,
                    temperature=0.7,
                    stream=False
                )
                
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    response_text = response.choices[0].message.content
                else:
                    response_text = ""
                
                # Calculate relevance based on medical terms
                input_words = set(text.lower().split())
                response_words = set(response_text.lower().split())
                
                # Calculate medical term relevance
                prompt_med_terms = set(w for w in input_words if w in self.med_terms)
                if not prompt_med_terms:
                    # Fallback to general word overlap if no medical terms found
                    word_overlap = len(input_words.intersection(response_words))
                    confidence = min((word_overlap / len(input_words) if input_words else 0.5) + 0.2, 1.0)
                else:
                    # Calculate how many prompt medical terms are covered in response
                    response_coverage = sum(1 for w in response_words if w in prompt_med_terms)
                    confidence = min((response_coverage / (len(prompt_med_terms) + 1e-5)) + 0.2, 1.0)
                
                predictions.append([1 - confidence, confidence])
                
            except Exception as e:
                print(f"[LIME] Together API prediction error: {e}")
                predictions.append([0.5, 0.5])
        
        return np.array(predictions)
    
    def _default_predictor(self, texts: List[str]) -> np.ndarray:
        """Default prediction function - fallback in case model type is unsupported"""
        print("[LIME] Using default predictor as fallback - results may be less accurate")
        return np.array([[0.5, 0.5] for _ in texts])

    def _create_visualization_html(self, explanation, text) -> str:
        """Create HTML visualization of LIME explanation"""
        # Single HTML template with embedded CSS
        html_content = """
        <div style="
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            font-family: -apple-system, system-ui, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        ">
            <div style="
                font-weight: bold;
                margin-bottom: 10px;
                color: #333;
                font-size: 14px;
            ">Prompt Impact Analysis</div>
            
            <!-- Highlighted text section -->
            <div style="
                line-height: 1.6;
                font-size: 14px;
                margin-bottom: 15px;
                padding: 10px;
                background-color: white;
                border-radius: 4px;
            ">{}</div>
            
            <!-- Stats section -->
            <div style="
                display: flex;
                justify-content: space-between;
                margin: 15px 0;
                gap: 10px;
            ">
                {}
            </div>
            
            <!-- Table section -->
            <div style="
                margin-top: 15px;
                background-color: white;
                border-radius: 4px;
                overflow: hidden;
            ">
                {}
            </div>
        </div>
        """
        
        return html_content.format(
            self._format_words_html(explanation, text),
            self._format_figures_html(explanation),
            self._format_table_html(explanation)
        )

    def _format_figures_html(self, explanation) -> str:
        """Format impact figures"""
        scores = [score for _, score in explanation.as_list()]
        if not scores:
            return ""
            
        avg_impact = sum(abs(s) for s in scores) / len(scores)
        pos_impact = sum(1 for s in scores if s > 0) / len(scores) * 100
        max_impact = max(abs(s) for s in scores)
        
        stat_style = """
            flex: 1;
            text-align: center;
            padding: 8px;
            background-color: white;
            border-radius: 4px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        """
        
        return f"""
            <div style="{stat_style}">
                <div style="font-size: 10px; color: #666;">Average Impact</div>
                <div style="font-size: 14px; font-weight: 500;">{avg_impact:.3f}</div>
            </div>
            <div style="{stat_style}">
                <div style="font-size: 10px; color: #666;">Positive Impact %</div>
                <div style="font-size: 14px; font-weight: 500;">{pos_impact:.1f}%</div>
            </div>
            <div style="{stat_style}">
                <div style="font-size: 10px; color: #666;">Max Impact</div>
                <div style="font-size: 14px; font-weight: 500;">{max_impact:.3f}</div>
            </div>
        """

    def _format_table_html(self, explanation) -> str:
        """Format impact table with proper word display"""
        items = [(word, score) for word, score in explanation.as_list() if abs(score) > 0.01]
        items.sort(key=lambda x: abs(x[1]), reverse=True)
        
        if not items:
            return "<p>No significant word impacts found.</p>"
        
        table_rows = []
        for word, score in items:
            color = "#dc3545" if score > 0 else "#0d6efd"
            # Use word directly without escaping
            table_rows.append(f"""
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; text-align: left;">{word}</td>
                    <td style="padding: 8px; text-align: right; color: {color}; font-weight: 500;">
                        {score:+.3f}
                    </td>
                </tr>
            """)
            
        return f"""
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="background-color: #f8f9fa;">
                        <th style="padding: 8px; text-align: left;">Word</th>
                        <th style="padding: 8px; text-align: right;">Impact</th>
                    </tr>
                </thead>
                <tbody>{"".join(table_rows)}</tbody>
            </table>
        """

    def _format_words_html(self, explanation, text) -> str:
        """Format words with correct tokenization matching"""
        # Create case-insensitive word score mapping
        word_scores = {word.lower(): score for word, score in explanation.as_list()}
        words = text.split()
        highlighted_words = []
        
        for word in words:
            score = word_scores.get(word.lower(), 0)
            if abs(score) > 0.01:  # Only highlight significant impacts
                opacity = min(abs(score) * 3, 0.9)  # Better opacity scaling
                bg_color = f"rgba(220, 53, 69, {opacity})" if score > 0 else f"rgba(0, 123, 255, {opacity})"
                
                highlighted_words.append(
                    f'<span style="'
                    f'display: inline-block;'
                    f'padding: 2px 4px;'
                    f'margin: 0 2px;'
                    f'border-radius: 3px;'
                    f'background-color: {bg_color};'
                    f'color: black;'
                    f'font-weight: 500;'
                    f'" title="Impact: {score:+.3f}">'
                    f'{word}</span>'  # Use original case
                )
            else:
                highlighted_words.append(word)  # Keep original without escaping
        
        return " ".join(highlighted_words)

    def explain_text(self, text: str, model_type: str) -> Dict[str, Any]:
        """Generate LIME explanation with improved error handling"""
        if len(text.split()) < 2:
            return self._empty_explanation("Text too short for analysis")
            
        try:
            predictor = self.create_predictor(model_type)
            explanation = self.explainer.explain_instance(
                text,
                predictor,
                num_features=min(10, len(text.split())),
                num_samples=10
            )
            
            print("[LIME] Debug info:")
            print(f"Original text words: {text.split()}")
            print(f"LIME features: {explanation.as_list()}")
            
            return {
                "words": [word for word, _ in explanation.as_list()],
                "scores": [score for _, score in explanation.as_list()],
                "html": self._create_visualization_html(explanation, text),
                "raw_explanation": explanation
            }
            
        except Exception as e:
            print(f"[LIME] Explanation error: {str(e)}")
            return self._empty_explanation(str(e))
    
    def _empty_explanation(self, error_msg: str) -> Dict[str, Any]:
        """Create empty explanation result with error message"""
        return {
            "words": [],
            "scores": [],
            "html": f"<p>Error: {error_msg}</p>",
            "error": error_msg
        }
