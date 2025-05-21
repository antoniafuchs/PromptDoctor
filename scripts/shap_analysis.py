import logging
import argparse
from datetime import datetime
import torch
import gc
from pathlib import Path
import pandas as pd
import plotly.express as px
from transformers import AutoModelForCausalLM, AutoTokenizer
import shap
import numpy as np
from typing import List, Dict, Any
import html
from IPython.display import HTML

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TorchMemoryManager:
    def __enter__(self):
        torch.cuda.empty_cache()
        gc.collect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        torch.cuda.empty_cache()
        gc.collect()

class SHAPProcessor:
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        self.explainer = None
        logger.info("[SHAP] Processor initialized")
        self._setup_tokenizer()

    # ...existing _setup_tokenizer method...

    def _model_predict(self, texts: List[str]) -> np.ndarray:
        # ...existing _model_predict method...

    def explain_text(self, text: str) -> Dict[str, Any]:
        """Generate SHAP explanation"""
        try:
            if self.explainer is None:
                self.explainer = shap.Explainer(
                    self._model_predict,
                    masker=shap.maskers.Text(),
                )
            
            shap_values = self.explainer([text])
            words = text.split()
            importances = shap_values.values[0]
            
            max_abs = max(abs(imp) for imp in importances)
            normalized_importances = [imp/max_abs if max_abs > 0 else imp for imp in importances]
            
            word_scores = list(zip(words, normalized_importances))
            word_scores.sort(key=lambda x: abs(x[1]), reverse=True)
            
            return {
                "words": [w for w, _ in word_scores],
                "scores": [float(s) for _, s in word_scores],
                "html": self._create_visualization_html(word_scores, text),
                "raw_explanation": shap_values,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"[SHAP] Explanation error: {str(e)}")
            return self._empty_explanation(str(e))

    def _create_visualization_html(self, word_scores: List[tuple], text: str) -> str:
        html_content = """
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; font-family: system-ui;">
            <div style="font-weight: bold; margin-bottom: 10px; color: #333;">SHAP Impact Analysis</div>
            <div style="line-height: 1.6; font-size: 14px; background: white; padding: 10px; border-radius: 4px;">
                {highlighted_text}
            </div>
            <div style="margin: 15px 0;">
                {table}
            </div>
        </div>
        """
        
        return html_content.format(
            highlighted_text=self._format_highlighted_text(word_scores, text),
            table=self._format_table(word_scores)
        )

    def _format_highlighted_text(self, word_scores: List[tuple], text: str) -> str:
        words = text.split()
        scores_dict = dict(word_scores)
        highlighted_words = []
        
        for word in words:
            score = scores_dict.get(word, 0)
            if abs(score) > 0.01:
                opacity = min(abs(score) * 3, 0.9)
                color = f"rgba(220, 53, 69, {opacity})" if score > 0 else f"rgba(0, 123, 255, {opacity})"
                highlighted_words.append(
                    f'<span style="background-color: {color};">{word}</span>'
                )
            else:
                highlighted_words.append(word)
        
        return " ".join(highlighted_words)

    def _format_table(self, word_scores: List[tuple]) -> str:
        rows = []
        for word, score in word_scores:
            if abs(score) > 0.01:
                color = "#dc3545" if score > 0 else "#0d6efd"
                rows.append(
                    f'<tr><td>{word}</td><td style="color: {color}">{score:+.3f}</td></tr>'
                )
        
        return f"""
            <table style="width: 100%; border-collapse: collapse;">
                <tr><th>Word</th><th>Impact</th></tr>
                {"".join(rows)}
            </table>
        """

    def _empty_explanation(self, error_msg: str) -> Dict[str, Any]:
        return {
            "words": [],
            "scores": [],
            "html": f"<p>Error: {error_msg}</p>",
            "error": error_msg,
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }

def create_word_impact_plot(words, scores, output_path: str):
    df = pd.DataFrame({'Word': words, 'Impact': scores})
    df = df.sort_values('Impact', ascending=True)
    
    fig = px.bar(df, x='Impact', y='Word', orientation='h',
                 title='Word Impact Analysis',
                 color='Impact',
                 color_continuous_scale='RdBu')
    
    fig.update_layout(
        height=max(400, len(words) * 20),
        xaxis_title='Impact Score',
        yaxis_title='Word'
    )
    
    fig.write_html(output_path)
    logger.info(f"Saved visualization to: {output_path}")
    return fig

def setup_model(model_name: str):
    try:
        logger.info(f"Loading model: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        return model, tokenizer
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise





# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TorchMemoryManager:
    def __enter__(self):
        torch.cuda.empty_cache()
        gc.collect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        torch.cuda.empty_cache()
        gc.collect()

def setup_model(model_name: str):
    """Initialize model and tokenizer with proper error handling"""
    try:
        logger.info(f"Loading model: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        return model, tokenizer
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise

def create_word_impact_plot(words, scores, output_path: str):
    """Create and save word impact visualization"""
    df = pd.DataFrame({'Word': words, 'Impact': scores})
    df = df.sort_values('Impact', ascending=True)
    
    fig = px.bar(df, x='Impact', y='Word', orientation='h',
                 title='Word Impact Analysis',
                 color='Impact',
                 color_continuous_scale='RdBu')
    
    fig.update_layout(
        height=max(400, len(words) * 20),
        xaxis_title='Impact Score',
        yaxis_title='Word'
    )
    
    fig.write_html(output_path)
    logger.info(f"Saved visualization to: {output_path}")

def process_prompts(processor: SHAPProcessor, prompts: list, output_dir: str, batch_size: int = 5):
    """Process multiple prompts with memory management"""
    results = []
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for i in range(0, len(prompts), batch_size):
        batch = prompts[i:i + batch_size]
        with TorchMemoryManager():
            for j, prompt in enumerate(batch):
                try:
                    idx = i + j
                    logger.info(f"Processing prompt {idx + 1}/{len(prompts)}: {prompt[:50]}...")
                    
                    explanation = processor.explain_text(prompt)
                    html_path = output_dir / f"shap_visualization_{idx}.html"
                    create_word_impact_plot(
                        explanation['words'], 
                        explanation['scores'], 
                        str(html_path)
                    )
                    
                    results.append({
                        'prompt': prompt,
                        'explanation': explanation,
                        'visualization_path': str(html_path)
                    })
                except Exception as e:
                    logger.error(f"Error processing prompt {idx}: {str(e)}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="SHAP Analysis for Med42 LLM")
    parser.add_argument("--input", type=str, required=True, 
                        help="Path to text file containing prompts (one per line)")
    parser.add_argument("--output-dir", type=str, default="shap_outputs",
                        help="Directory to save visualizations")
    parser.add_argument("--model", type=str, 
                        default="m42-health/Llama3-Med42-8B",
                        help="Model name/path")
    parser.add_argument("--batch-size", type=int, default=5,
                        help="Batch size for processing")
    args = parser.parse_args()

    try:
        # Load prompts
        with open(args.input, 'r') as f:
            prompts = [line.strip() for line in f if line.strip()]
        
        # Setup
        model, tokenizer = setup_model(args.model)
        
        # Create mock session state for the processor
        class SessionState:
            def __init__(self, model, tokenizer):
                self.hf_model = model
                self.hf_tokenizer = tokenizer
                self.selected_model_name = "Llama3-Med42-8B"
        
        import types
        sys.modules['streamlit'] = types.ModuleType('streamlit')
        sys.modules['streamlit'].session_state = SessionState(model, tokenizer)
        
        # Initialize processor and process prompts
        processor = SHAPProcessor()
        results = process_prompts(
            processor=processor,
            prompts=prompts,
            output_dir=args.output_dir,
            batch_size=args.batch_size
        )
        
        # Save results summary
        summary_path = Path(args.output_dir) / "analysis_summary.txt"
        with open(summary_path, 'w') as f:
            for result in results:
                f.write(f"Prompt: {result['prompt']}\n")
                f.write(f"Visualization: {result['visualization_path']}\n")
                f.write("-" * 80 + "\n")
        
        logger.info(f"Analysis complete. Results saved in: {args.output_dir}")
        
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
