import shap
import numpy as np
from typing import List, Callable, Dict, Any
import streamlit as st
import html
import requests
import datetime
import torch

class SHAPProcessor:
    def __init__(self):
        """Initialize SHAP processor"""
        print("[SHAP] Processor initialized")
        self.explainer = None  # Will be initialized when model is available
        self.model = None
        self.tokenizer = None

    def _setup_model(self):
        """Setup HuggingFace model and tokenizer"""
        if self.model is None:
            self.model = st.session_state.hf_model
            self.tokenizer = st.session_state.hf_tokenizer
            
            # Ensure tokenizer has padding token
            if self.tokenizer.pad_token is None:
                if self.tokenizer.eos_token is not None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                    self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
                else:
                    self.tokenizer.add_special_tokens({'pad_token': '[PAD]'})
                    self.model.resize_token_embeddings(len(self.tokenizer))
                print(f"[SHAP] Set padding token: {self.tokenizer.pad_token}")

    def _model_predict(self, texts: List[str]) -> np.ndarray:
        """Predict function for SHAP using HuggingFace model"""
        self._setup_model()
        predictions = []
        
        try:
            # Handle different model types
            is_bert = "bert" in st.session_state.selected_model_name.lower()
            max_length = 128 if is_bert else 512  # Shorter sequences for BERT
            
            # Tokenize with appropriate settings
            inputs = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=max_length
            )
            
            # Generate outputs based on model type
            with torch.no_grad():
                if is_bert:
                    outputs = self.model(**inputs)
                    logits = outputs.logits
                    # Use sequence probabilities
                    probs = torch.softmax(logits[:, -1], dim=-1)
                    scores = probs.mean(dim=-1)
                else:
                    outputs = self.model.generate(
                        **inputs,
                        max_length=max_length,
                        num_return_sequences=1,
                        pad_token_id=self.tokenizer.pad_token_id,
                        do_sample=False  # Deterministic for SHAP
                    )
                    scores = torch.ones(len(texts))  # Default scores
                
                predictions = scores.numpy()
                
        except Exception as e:
            print(f"[SHAP] Prediction error: {str(e)}")
            predictions = np.array([0.5] * len(texts))
            
        return predictions

    def explain_text(self, text: str) -> Dict[str, Any]:
        """Generate SHAP explanation"""
        try:
            self._setup_model()
            
            # Initialize explainer with current model
            if self.explainer is None:
                self.explainer = shap.Explainer(
                    self._model_predict,
                    masker=shap.maskers.Text(),
                )
            
            # Generate SHAP values
            shap_values = self.explainer([text])
            
            # Extract word importances (use first element as we have single output)
            words = text.split()
            importances = shap_values.values[0]
            
            # Normalize importances for visualization
            max_abs = max(abs(imp) for imp in importances)
            normalized_importances = [imp/max_abs if max_abs > 0 else imp for imp in importances]
            
            # Create word-score pairs
            word_scores = list(zip(words, normalized_importances))
            word_scores.sort(key=lambda x: abs(x[1]), reverse=True)
            
            return {
                "words": [w for w, _ in word_scores],
                "scores": [float(s) for _, s in word_scores],
                "html": self._create_visualization_html(word_scores, text),
                "raw_explanation": shap_values,
                "timestamp": datetime.datetime.now().isoformat(),  # Add timestamp
                "response": "",  # Empty response as it will be filled by XAIProcessor
                "status": "success"  # Add status field
            }
            
        except Exception as e:
            print(f"[SHAP] Explanation error: {str(e)}")
            return self._empty_explanation(str(e))

    def _create_visualization_html(self, word_scores: List[tuple], text: str) -> str:
        """Create HTML visualization matching LIME style"""
        # Use the same HTML template as LIME processor
        html_content = """
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; font-family: system-ui;">
            <div style="font-weight: bold; margin-bottom: 10px; color: #333;">SHAP Impact Analysis</div>
            <div style="line-height: 1.6; font-size: 14px; background: white; padding: 10px; border-radius: 4px;">
                {highlighted_text}
            </div>
            <div style="display: flex; gap: 10px; margin: 15px 0;">
                {stats}
            </div>
            <div style="background: white; border-radius: 4px; overflow: hidden;">
                {table}
            </div>
        </div>
        """
        
        return html_content.format(
            highlighted_text=self._format_highlighted_text(word_scores, text),
            stats=self._format_stats(word_scores),
            table=self._format_table(word_scores)
        )

    def _format_highlighted_text(self, word_scores: List[tuple], text: str) -> str:
        """Format text with highlighted words"""
        words = text.split()
        scores_dict = dict(word_scores)
        
        highlighted_words = []
        for word in words:
            score = scores_dict.get(word, 0)
            if abs(score) > 0.01:
                opacity = min(abs(score) * 3, 0.9)
                color = f"rgba(220, 53, 69, {opacity})" if score > 0 else f"rgba(0, 123, 255, {opacity})"
                highlighted_words.append(
                    f'<span style="padding: 2px 4px; margin: 0 2px; border-radius: 3px; '
                    f'background-color: {color}; color: black; font-weight: 500;" '
                    f'title="Impact: {score:+.3f}">{word}</span>'
                )
            else:
                highlighted_words.append(word)
                
        return " ".join(highlighted_words)

    def _format_stats(self, word_scores: List[tuple]) -> str:
        """Format statistics section"""
        scores = [s for _, s in word_scores]
        avg_impact = np.mean([abs(s) for s in scores]) if scores else 0
        pos_impact = sum(1 for s in scores if s > 0) / len(scores) * 100 if scores else 0
        max_impact = max([abs(s) for s in scores]) if scores else 0
        
        stat_style = (
            "flex: 1; text-align: center; padding: 8px; background: white; "
            "border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1);"
        )
        
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

    def _format_table(self, word_scores: List[tuple]) -> str:
        """Format table section"""
        rows = []
        for word, score in word_scores:
            if abs(score) > 0.01:
                color = "#dc3545" if score > 0 else "#0d6efd"
                rows.append(
                    f'<tr style="border-bottom: 1px solid #dee2e6;">'
                    f'<td style="padding: 8px; text-align: left;">{word}</td>'
                    f'<td style="padding: 8px; text-align: right; color: {color}; '
                    f'font-weight: 500;">{score:+.3f}</td></tr>'
                )
        
        return f"""
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead><tr style="background: #f8f9fa;">
                    <th style="padding: 8px; text-align: left;">Word</th>
                    <th style="padding: 8px; text-align: right;">Impact</th>
                </tr></thead>
                <tbody>{"".join(rows)}</tbody>
            </table>
        """

    def _empty_explanation(self, error_msg: str) -> Dict[str, Any]:
        """Create empty explanation with required fields"""
        return {
            "words": [],
            "scores": [],
            "html": f"<p>Error: {error_msg}</p>",
            "error": error_msg,
            "timestamp": datetime.datetime.now().isoformat(),
            "response": "",
            "status": "error"
        }
