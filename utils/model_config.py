import os
from pathlib import Path
from typing import Dict, List
import json
from transformers import AutoModelForCausalLM, AutoModelForSeq2SeqLM, BertLMHeadModel, AutoTokenizer, PreTrainedModel, GenerationConfig
import re
import torch

class ModelConfig:
    DEFAULT_CONFIGS = {
        "GPT": [
            {"name": "gpt-4", "display_name": "GPT-4"},
            {"name": "gpt-3.5-turbo", "display_name": "GPT-3.5 Turbo"}
        ],
        "HuggingFace": [
            {"name": "m42-health/Llama3-Med42-8B", "display_name": "Med42 8B"},
            {"name": "starmpcc/Asclepius-7B", "display_name": "starmpcc/Asclepius-7B"},
            {"name": "tiiuae/falcon-rw-1b", "display_name": "tiiuae/falcon-rw-1b"},
            {"name": "microsoft/BiomedNLP-BioGPT-Large", "display_name": "BioGPT Large"},
            {"name": "facebook/opt-350m", "display_name": "OPT 350M (Faster)"}
        ],
        "Ollama": [
            {"name": "llama3-med42-8b", "display_name": "Med42 8B"},
            {"name": "llama2-medical", "display_name": "Llama 2 Medical"}
        ],
        "HuggingFaceEndpoint": [
            {
                "name": "openai-community/gpt2",
                "display_name": "GPT-2",
                "endpoint_url": "https://nxy944uw5xyackw4.eu-west-1.aws.endpoints.huggingface.cloud"
            }
        ],
        "Together": [
            {"name": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", "display_name": "Llama 3.3 70B Instruct (Free)"},
            {"name": "meta-llama/Llama-3.1-8B-Instruct", "display_name": "Llama 3.1 8B Instruct"},
            {"name": "mistralai/Mixtral-8x7B-Instruct-v0.1", "display_name": "Mixtral 8x7B Instruct"}
        ]
    }

    @staticmethod
    def get_models_for_type(model_type: str) -> List[Dict]:
        """Get available models for given type"""
        return ModelConfig.DEFAULT_CONFIGS.get(model_type, [])

    @staticmethod
    def merge_with_local_models(local_models: List[Dict]) -> List[Dict]:
        """Merge local models with default models"""
        default_names = {m["name"] for m in ModelConfig.DEFAULT_CONFIGS["Ollama"]}
        merged = ModelConfig.DEFAULT_CONFIGS["Ollama"].copy()
        
        for model in local_models:
            if model["name"] not in default_names:
                merged.append(model)
        
        return merged

    @staticmethod
    def initialize_hf_model(model_name: str):
        """Initialize HuggingFace model with proper configuration"""
        try:
            # Initialize tokenizer first
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Set up basic generation config
            gen_config = GenerationConfig(
                max_new_tokens=512,
                do_sample=True,
                temperature=0.7,
                top_k=50,
                top_p=0.9,
                num_return_sequences=1,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
            
            # Set up tokenizer padding
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
                print(f"[MODEL] Using eos_token as pad_token: {tokenizer.pad_token}")
            
            # Initialize model with basic config
            model = (BertLMHeadModel if "bert" in model_name.lower() else AutoModelForCausalLM).from_pretrained(
                model_name,
                torch_dtype=torch.float32
            )
            
            # Set generation config and ensure padding is properly set
            model.generation_config = gen_config
            model.config.pad_token_id = tokenizer.pad_token_id
            model.config.eos_token_id = tokenizer.eos_token_id
            
            model.eval()
            
            print(f"[MODEL] Initialized {model_name}")
            print(f"[MODEL] Padding token: {tokenizer.pad_token} (id: {tokenizer.pad_token_id})")
            
            return model, tokenizer
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize model: {str(e)}")
            raise
