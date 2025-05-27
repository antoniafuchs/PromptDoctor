import sys
import signal
import psutil
import gc
import argparse
from pathlib import Path
import logging
import torch
from lime.lime_text import LimeTextExplainer
import numpy as np
from typing import List, Dict, Any
import json
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer
from contextlib import contextmanager
import traceback

# Configure logging
logger = logging.getLogger(__name__)

def setup_logging(debug: bool, log_file: str = None):
    log_level = logging.DEBUG if debug else logging.INFO
    logging.getLogger().handlers = []
    
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

def log_memory_usage():
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

class TorchMemoryManager:
    def __enter__(self):
        torch.cuda.empty_cache()
        gc.collect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        torch.cuda.empty_cache()
        gc.collect()

def get_unique_filepath(base_path: Path) -> Path:
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

def setup_model(model_name: str):
    try:
        logger.info("=" * 50)
        logger.info("Starting model initialization...")
        logger.info(f"Loading model: {model_name}")
        
        logger.info("Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True,
            use_fast=True
        )
        
        logger.info("Loading model weights...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16,
            device_map="auto"
        ).eval()
        
        logger.info("Model initialization complete!")
        logger.info("=" * 50)
        return model, tokenizer
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise

class LIMEProcessor:
    def __init__(self, model, tokenizer, max_length=512, num_features=10):
        self.model = model
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.num_features = num_features
        self.model.eval()
        self._setup_tokenizer()
        self.explainer = LimeTextExplainer(class_names=['negative', 'positive'])

    def _setup_tokenizer(self):
        if self.tokenizer.pad_token is None:
            if self.tokenizer.eos_token is not None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            else:
                self.tokenizer.add_special_tokens({'pad_token': '[PAD]'})
                self.model.resize_token_embeddings(len(self.tokenizer))

    def predict_proba(self, texts):
        """Prediction function for LIME"""
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            inputs = self.tokenizer(
                texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.max_length
            ).to(self.model.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits[:, -1, :]
                probs = torch.softmax(logits, dim=-1).cpu().numpy()
                # Convert to binary classification for simplicity
                return np.column_stack([1-probs.mean(axis=1), probs.mean(axis=1)])
        except Exception as e:
            logger.error(f"[LIME] Prediction error: {str(e)}")
            return np.zeros((len(texts), 2))

    def explain_text(self, text: str) -> Dict[str, Any]:
        """Generate LIME explanation"""
        try:
            exp = self.explainer.explain_instance(
                text,
                self.predict_proba,
                num_features=self.num_features
            )
            
            # Create visualization
            html_exp = self._create_visualization_html(exp, text)
            
            return {
                "explanation": exp,
                "html": html_exp,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"[LIME] Explanation error: {str(e)}")
            return self._empty_explanation(str(e))

    def _create_visualization_html(self, exp, text: str) -> str:
        """Create HTML visualization using LIME's visualization method"""
        try:
            # Get word weights
            words = text.split()
            exp_list = exp.as_list()
            word_weights = dict(exp_list)
            
            # Create unique div name
            div_name = f"lime_viz_{hash(text) & 0xffffffff}"
            exp_name = f"exp_{div_name}"
            
            # Create JavaScript explanation object
            js_object = {
                "words": words,
                "weights": [word_weights.get(word, 0) for word in words]
            }
            
            html = f"""
            <div id="{div_name}" style="margin: 20px; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <script>
                    var {exp_name} = {json.dumps(js_object)};
                    document.addEventListener('DOMContentLoaded', function() {{
                        visualize_instance_html(
                            {exp_name}.weights,
                            1,
                            "{div_name}",
                            "{exp_name}",
                            true,
                            true
                        );
                    }});
                </script>
                <style>
                    .lime-word {{ padding: 2px 4px; margin: 0 1px; border-radius: 3px; }}
                    .lime-positive {{ background-color: rgba(40, 167, 69, VAR); }}
                    .lime-negative {{ background-color: rgba(220, 53, 69, VAR); }}
                </style>
            </div>
            """
            
            return html
        except Exception as e:
            logger.error(f"[LIME] Visualization error: {str(e)}")
            return f"<p>Error creating visualization: {str(e)}</p>"

    def _empty_explanation(self, error_msg: str) -> Dict[str, Any]:
        return {
            "error": error_msg,
            "html": f"<p>Error: {error_msg}</p>",
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }

def process_prompts(processor: LIMEProcessor, prompts: list, output_dir: str):
    """Process multiple prompts and save visualizations"""
    results = []
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    total_prompts = len(prompts)
    logger.info("=" * 50)
    logger.info(f"Starting analysis of {total_prompts} prompts...")
    
    for idx, prompt in enumerate(prompts, 1):
        try:
            logger.info(f"Processing prompt {idx}/{total_prompts}")
            logger.info(f"Prompt text: {prompt[:100]}...")
            
            logger.debug("Generating LIME explanation...")
            explanation = processor.explain_text(prompt)
            
            if explanation["status"] == "success":
                html_path = output_dir / f"lime_visualization_{idx}.html"
                logger.debug(f"Saving visualization to {html_path}")
                with open(html_path, 'w') as f:
                    f.write(explanation["html"])
                
                results.append({
                    'prompt': prompt,
                    'visualization_path': str(html_path),
                    'success': True
                })
                logger.info(f"✓ Successfully processed prompt {idx}")
            else:
                logger.warning(f"Failed to process prompt {idx}: {explanation.get('error', 'Unknown error')}")
                results.append({
                    'prompt': prompt,
                    'error': explanation.get("error", "Unknown error"),
                    'success': False
                })
                
        except Exception as e:
            logger.error(f"Error processing prompt {idx}: {str(e)}")
            results.append({
                'prompt': prompt,
                'error': str(e),
                'success': False
            })
        
        logger.info("-" * 30)
    
    logger.info("Analysis complete!")
    logger.info(f"Successfully processed: {sum(1 for r in results if r['success'])} / {total_prompts}")
    logger.info("=" * 50)
    return results

def main():
    parser = argparse.ArgumentParser(description="LIME Analysis for Text")
    parser.add_argument("--input", type=str, required=True, 
                      help="Path to text file containing prompts")
    parser.add_argument("--output-dir", type=str, default="lime_outputs",
                      help="Directory to save visualizations")
    parser.add_argument("--model", type=str,
                      default="m42-health/Llama3-Med42-8B",
                      help="Model name/path")
    parser.add_argument("--num-features", type=int, default=10,
                      help="Number of features to explain")
    args = parser.parse_args()

    try:
        logger.info("Starting LIME Analysis...")
        logger.info("=" * 50)
        
        # Load model and prompts
        model, tokenizer = setup_model(args.model)
        processor = LIMEProcessor(model, tokenizer, num_features=args.num_features)
        
        logger.info("Loading prompts from file...")
        with open(args.input, 'r') as f:
            prompts = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(prompts)} prompts")
        
        results = process_prompts(processor, prompts, args.output_dir)
        
        # Save summary
        logger.info("Generating analysis summary...")
        summary_path = Path(args.output_dir) / "analysis_summary.html"
        with open(summary_path, 'w') as f:
            f.write(create_summary_html(results))
        
        logger.info(f"Analysis complete. Results saved in: {args.output_dir}")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
