from typing import Dict, List, Optional
from abc import ABC, abstractmethod

class ModelProvider(ABC):
    @abstractmethod
    def get_available_models(self) -> List[Dict[str, str]]:
        """Return list of available models with name and display_name"""
        pass
    
    @abstractmethod
    def generate_response(self, messages: List[Dict], system_prompt: str) -> str:
        """Generate response from the model"""
        pass
    
    @abstractmethod
    def initialize_model(self, model_name: str) -> None:
        """Initialize specific model"""
        pass
