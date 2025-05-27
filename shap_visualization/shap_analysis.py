import logging
import argparse
import sys
import signal
import psutil
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
import traceback
import torch.nn.functional as F
from contextlib import contextmanager
import time
from threading import Timer
import scipy as sp
import os

# Disable Numba JIT to avoid recursive typing errors
os.environ['NUMBA_DISABLE_JIT'] = '1'

class TimeoutException(Exception):
    pass

@contextmanager
def timeout(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Prediction timed out")
    
    # Set the signal handler and a timeout
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Disable the alarm
        signal.alarm(0)

class ThreadTimeout:
    """Platform-independent timeout handler"""
    def __init__(self, seconds):
        self.seconds = seconds
        self.timer = None
        self.timed_out = False
    
    def timeout_handler(self):
        self.timed_out = True
    
    def __enter__(self):
        self.timer = Timer(self.seconds, self.timeout_handler)
        self.timer.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.timer:
            self.timer.cancel()

def setup_logging(debug: bool, log_file: str = None):
    """Configure logging with both console and file output"""
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Clear any existing handlers
    logging.getLogger().handlers = []
    
    # Create formatters and handlers
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
    
    # Ensure torch operations are logged
    logging.getLogger("torch").setLevel(logging.DEBUG if debug else logging.INFO)

def log_memory_usage():
    """Log current memory usage"""
    process = psutil.Process()
    gpu_memory = []
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            allocated = torch.cuda.memory_allocated(i) / 1024**2
            reserved = torch.cuda.memory_reserved(i) / 1024**2
            gpu_memory.append(f"GPU {i}: {allocated:.1f}MB allocated, {reserved:.1f}MB reserved")
    
    logger.debug(
        "Memory Usage - RAM: %.1fGB, VRAM: %s", 
        process.memory_info().rss / 1024**3,
        ", ".join(gpu_memory)
    )

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

class TeacherForcingWrapper:
    """Wrapper for teacher forcing predictions"""
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        
    def __call__(self, inputs, outputs=None):
        if outputs is None:
            return self.model(**inputs).logits
        
        input_ids = inputs["input_ids"]
        output_ids = self.tokenizer(outputs, return_tensors="pt")["input_ids"].to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids)
            logits = outputs.logits[:, -1, :]  # Get last token logits
            scores = torch.log_softmax(logits, dim=-1)
            token_scores = torch.gather(scores, 1, output_ids[:, 0].unsqueeze(1))
            return token_scores.squeeze(-1)

class SHAPProcessor:
    def __init__(self, model, tokenizer, max_length=512, timeout_seconds=30):
        self.model = model
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.timeout_seconds = timeout_seconds
        self.model.eval()
        self._setup_tokenizer()
        
        # Initialize explainer with partition explainer instead of text masker
        logger.debug("[SHAP] Initializing partition explainer...")
        try:
            self.explainer = shap.explainers.Partition(
                model=self._model_predict_wrapper,
                max_samples=100,  # Reduce samples for better performance
                output_names=['next_token']
            )
            logger.info("[SHAP] Processor and explainer initialized successfully")
        except Exception as e:
            logger.error(f"[SHAP] Failed to initialize explainer: {str(e)}")
            self.explainer = None

    def _setup_tokenizer(self):
        """Setup tokenizer with proper padding token"""
        if self.tokenizer.pad_token is None:
            if self.tokenizer.eos_token is not None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
            else:
                self.tokenizer.add_special_tokens({'pad_token': '[PAD]'})
                self.model.resize_token_embeddings(len(self.tokenizer))
            logger.info(f"[SHAP] Set padding token: {self.tokenizer.pad_token}")

    def _model_predict_wrapper(self, texts: List[str]) -> np.ndarray:
        """Wrapper around model predict to handle text inputs properly"""
        try:
            if isinstance(texts, str):
                texts = [texts]
            elif not isinstance(texts, list):
                texts = list(texts)
            
            # Ensure all inputs are strings
            texts = [str(text) if text is not None else "" for text in texts]
            logger.debug(f"[SHAP] Processing {len(texts)} text inputs")
            
            return self._model_predict(texts)
        except Exception as e:
            logger.error(f"[SHAP] Prediction wrapper error: {str(e)}")
            return np.zeros((len(texts), 1))

    def _model_predict(self, texts: List[str]) -> np.ndarray:
        """Next token prediction function for SHAP"""
        try:
            # Tokenize inputs
            inputs = self.tokenizer(
                texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.max_length
            )
            input_ids = inputs["input_ids"].to(self.model.device)
            attention_mask = inputs["attention_mask"].to(self.model.device)

            # Get next token predictions
            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                next_token_logits = outputs.logits[:, -1, :]
                probs = torch.softmax(next_token_logits, dim=-1).cpu().numpy()
                
                # Return all probabilities instead of just top ones
                return probs

        except Exception as e:
            logger.error(f"[SHAP] Prediction error: {str(e)}")
            return np.zeros((len(texts), self.model.config.vocab_size))

    def explain_text(self, text: str) -> Dict[str, Any]:
        """Generate SHAP explanation using partition explainer"""
        try:
            if not isinstance(text, str):
                text = str(text)
            
            logger.debug(f"[SHAP] Computing SHAP values for text: {text[:50]}...")
            
            # Split text into words for analysis
            words = text.split()
            background = ["" for _ in range(len(words))]  # Empty background dataset
            
            try:
                with timeout(self.timeout_seconds):
                    shap_values = self.explainer([text], background)
            except TimeoutException:
                logger.warning("[SHAP] Explanation timed out, using fallback analysis")
                return self._fallback_explanation(text)
            
            # Extract words and scores
            scores = shap_values.values[0]
            if len(words) != len(scores):
                scores = self._normalize_scores(scores, len(words))
            
            return {
                "words": words,
                "scores": scores.tolist() if isinstance(scores, np.ndarray) else scores,
                "html": self._create_text_plot_html(shap_values[0]),
                "raw_explanation": shap_values,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"[SHAP] Explanation error: {str(e)}\n{traceback.format_exc()}")
            return self._fallback_explanation(text)

    def explain_generation(self, inputs: List[str], outputs: List[str] = None) -> Dict[str, Any]:
        """Explain text generation with SHAP"""
        try:
            # Initialize explainer with text masker
            masker = shap.maskers.Text(
                self.tokenizer,
                mask_token="...",
                collapse_mask_token=True
            )
            
            explainer = shap.Explainer(
                self.teacher_forcing,
                masker,
                output_names=self.tokenizer.convert_ids_to_tokens(
                    self.tokenizer(outputs[0] if outputs else "", return_tensors="pt")["input_ids"][0]
                ) if outputs else None
            )
            
            # Generate SHAP values
            shap_values = explainer(inputs, outputs)
            
            return {
                "shap_values": shap_values,
                "html": self._create_text_plot_html(shap_values),
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"[SHAP] Generation explanation error: {str(e)}")
            return self._empty_explanation(str(e))

    def _fallback_explanation(self, text: str) -> Dict[str, Any]:
        """Simple fallback analysis when SHAP computation fails"""
        try:
            words = text.split()
            # Create simple impact scores based on word positions
            scores = np.zeros(len(words))
            for i, _ in enumerate(words):
                scores[i] = 1.0 - (i / len(words))  # Simple position-based scoring
            
            return {
                "words": words,
                "scores": scores.tolist(),
                "html": self._create_simple_html(words, scores),
                "timestamp": datetime.now().isoformat(),
                "status": "fallback"
            }
        except Exception as e:
            logger.error(f"[SHAP] Fallback explanation failed: {str(e)}")
            return self._empty_explanation(str(e))

    def _create_simple_html(self, words: List[str], scores: np.ndarray) -> str:
        """Create simple HTML visualization for fallback case"""
        try:
            word_score_pairs = list(zip(words, scores))
            return self._create_visualization_html(word_score_pairs, " ".join(words))
        except Exception as e:
            logger.error(f"[SHAP] Simple HTML creation failed: {str(e)}")
            return f"<p>Error creating visualization: {str(e)}</p>"

    def _create_text_plot_html(self, shap_values) -> str:
        """Create HTML visualization using SHAP's text plot"""
        try:
            import matplotlib
            matplotlib.use('Agg')  # Force Agg backend
            import matplotlib.pyplot as plt
            import io
            import base64
            
            # Reset plot state
            plt.clf()
            plt.close('all')
            
            # Configure style
            plt.rcParams.update({
                'figure.figsize': (12, 4),
                'font.size': 10,
                'axes.titlesize': 12,
                'axes.labelsize': 10
            })
            
            fig = plt.figure()
            
            try:
                shap.plots.text(shap_values, show=False)
                plt.title("Token Impact Analysis", pad=20)
                plt.tight_layout()
            except Exception as e:
                logger.error(f"[SHAP] Text plot error: {str(e)}")
                plt.text(0.5, 0.5, f"Error creating SHAP plot: {str(e)}", 
                        ha='center', va='center', wrap=True)
            
            # Save plot
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            # Convert to base64
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            
            # Create HTML with improved styling
            html = f"""
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="font-weight: bold; margin-bottom: 15px; color: #333;">
                    SHAP Token Impact Analysis
                </div>
                <img src="data:image/png;base64,{img_str}" 
                     style="width: 100%; max-width: 1200px; border-radius: 5px;">
                <div style="font-size: 12px; color: #666; margin-top: 10px;">
                    Red: Positive impact | Blue: Negative impact
                </div>
            </div>
            """
            return html
            
        except Exception as e:
            logger.error(f"[SHAP] Plot creation error: {str(e)}")
            return f"<p>Error creating plot: {str(e)}</p>"

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

def get_unique_filepath(base_path: Path) -> Path:
    """Generate a unique filepath by adding a numeric suffix if file exists."""
    if not base_path.exists():
        return base_path
    
    parent = base_path.parent
    stem = base_path.stem
    suffix = base_path.suffix
    counter = 1
    
    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1

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
    
    # Get unique filepath if file exists
    output_path = str(get_unique_filepath(Path(output_path)))
    fig.write_html(output_path)
    logger.info(f"Saved visualization to: {output_path}")
    return fig, output_path

def setup_model(model_name: str):
    """Initialize Med42 model with optimized settings"""
    try:
        logger.info(f"Loading model: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True,
            use_fast=True
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16,
            device_map="auto"
        ).eval()  # Set to eval mode immediately
        
        return model, tokenizer
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise

def process_prompts(processor: SHAPProcessor, prompts: list, output_dir: str, batch_size: int = 5):
    """Process multiple prompts with memory management and detailed visualization"""
    results = []
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure all prompts are strings
    prompts = [str(prompt) if prompt is not None else "" for prompt in prompts]
    
    for i in range(0, len(prompts), batch_size):
        batch = prompts[i:i + batch_size]
        with TorchMemoryManager():
            for j, prompt in enumerate(batch):
                try:
                    idx = i + j
                    logger.info(f"Processing prompt {idx + 1}/{len(prompts)}: {prompt[:100]}...")
                    
                    if not prompt.strip():
                        logger.warning(f"Skipping empty prompt at index {idx}")
                        continue
                    
                    # Get SHAP explanation
                    explanation = processor.explain_text(prompt)
                    
                    # Create more detailed visualization
                    if explanation and 'words' in explanation and 'scores' in explanation:
                        base_html_path = output_dir / f"shap_visualization_{idx}.html"
                        html_path = get_unique_filepath(base_html_path)
                        fig, actual_path = create_word_impact_plot(
                            explanation['words'],
                            explanation['scores'],
                            str(html_path)
                        )
                        
                        # Add additional visualization details
                        with open(actual_path, 'a') as f:
                            f.write(f"""
                            <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa;">
                                <h3>Analysis Details</h3>
                                <p><strong>Input Text:</strong> {html.escape(prompt)}</p>
                                <p><strong>Analysis Time:</strong> {explanation.get('timestamp', 'N/A')}</p>
                                <p><strong>Status:</strong> {explanation.get('status', 'N/A')}</p>
                            </div>
                            """)
                        
                        results.append({
                            'prompt': prompt,
                            'explanation': explanation,
                            'visualization_path': str(html_path),
                            'analysis_success': True
                        })
                    else:
                        logger.error(f"No valid explanation generated for prompt {idx}")
                        results.append({
                            'prompt': prompt,
                            'error': 'No valid explanation generated',
                            'analysis_success': False
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing prompt {idx}: {str(e)}")
                    results.append({
                        'prompt': prompt,
                        'error': str(e),
                        'analysis_success': False
                    })
                
                # Force garbage collection after each prompt
                gc.collect()
                torch.cuda.empty_cache()
    
    # Save detailed results summary with unique filename
    summary_base_path = output_dir / "analysis_summary.html"
    summary_path = get_unique_filepath(summary_base_path)
    with open(summary_path, 'w') as f:
        f.write("""
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .result { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .success { border-left: 5px solid #28a745; }
                .error { border-left: 5px solid #dc3545; }
            </style>
        </head>
        <body>
        <h1>SHAP Analysis Summary</h1>
        """)
        
        for result in results:
            success_class = "success" if result.get('analysis_success', False) else "error"
            f.write(f"""
            <div class="result {success_class}">
                <h3>Prompt Analysis</h3>
                <p><strong>Input:</strong> {html.escape(result['prompt'][:200])}...</p>
                """)
            
            if result.get('analysis_success', False):
                f.write(f"""
                <p><strong>Visualization:</strong> 
                    <a href="{Path(result['visualization_path']).name}">View Analysis</a>
                </p>
                """)
            else:
                f.write(f"""
                <p><strong>Error:</strong> {html.escape(result.get('error', 'Unknown error'))}</p>
                """)
            
            f.write("</div>")
        
        f.write("</body></html>")
    
    # Save text summary with unique filename
    text_summary_base_path = output_dir / "analysis_summary.txt"
    text_summary_path = get_unique_filepath(text_summary_base_path)
    with open(text_summary_path, 'w') as f:
        for result in results:
            f.write(f"Prompt: {result['prompt']}\n")
            f.write(f"Visualization: {result['visualization_path']}\n")
            f.write("-" * 80 + "\n")
    
    logger.info(f"Analysis complete. Results saved in: {output_dir}")
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
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    parser.add_argument("--log-file", type=str, default="shap_analysis.log",
                        help="Log file path")
    args = parser.parse_args()

    # Setup logging first
    setup_logging(args.debug, args.log_file)
    
    # Setup signal handler
    def signal_handler(signum, frame):
        logger.critical("Received interrupt signal. Cleaning up...")
        log_memory_usage()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Load prompts
        with open(args.input, 'r') as f:
            prompts = [line.strip() for line in f if line.strip()]
        
        # Setup model and processor
        model, tokenizer = setup_model(args.model)
        processor = SHAPProcessor(model, tokenizer)
        
        # Process prompts
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
        logger.error(f"Full traceback: {traceback.format_exc()}")
        log_memory_usage()
        sys.exit(1)

if __name__ == "__main__":
    main()
