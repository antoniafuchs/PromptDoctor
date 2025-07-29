"""
model_registry.py
This file manages the registry of models available in PromptDoctor, including model metadata and access logic.
"""

from typing import Dict, Type
from .model_providers.base import ModelProvider
from .model_providers.ollama_provider import OllamaProvider
from .model_providers.huggingface_provider import HuggingFaceProvider
from .model_providers.together_provider import TogetherProvider
import os

class ModelRegistry:
    _providers: Dict[str, Type[ModelProvider]] = {
        "Ollama": OllamaProvider,
        "HuggingFace": HuggingFaceProvider,
        "Together": TogetherProvider,
    }
    
    @classmethod
    def get_provider(cls, provider_name: str) -> ModelProvider:
        """Get instance of model provider"""
        provider_class = cls._providers.get(provider_name)
        if provider_class:
            return provider_class()
        raise ValueError(f"Unknown provider: {provider_name}")
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[ModelProvider]) -> None:
        """Register new model provider"""
        cls._providers[name] = provider_class
