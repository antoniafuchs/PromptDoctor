import os
from pathlib import Path
from typing import Dict, List
import json

class ModelConfig:
    DEFAULT_CONFIGS = {
        "GPT": [
            {"name": "gpt-4", "display_name": "GPT-4"},
            {"name": "gpt-3.5-turbo", "display_name": "GPT-3.5 Turbo"}
        ],
        "HuggingFace": [
            {"name": "starmpcc/Asclepius-7B", "display_name": "starmpcc/Asclepius-7B"},
            {"name": "microsoft/BiomedNLP-BioGPT-Large", "display_name": "BioGPT Large"},
            {"name": "facebook/opt-350m", "display_name": "OPT 350M (Faster)"}
        ],
        "Ollama": [
            {"name": "llama3-med42-8b", "display_name": "Med42 8B"},
            {"name": "llama2-medical", "display_name": "Llama 2 Medical"}
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
