from typing import Dict, Any
import requests
from .base import ModelProvider

class HuggingFaceEndpointProvider(ModelProvider):
    def __init__(self):
        self.api_token = None
        self.endpoint_url = None
        
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the endpoint provider with token and URL"""
        self.api_token = config.get("api_token")
        self.endpoint_url = config.get("endpoint_url")
        if not self.api_token or not self.endpoint_url:
            raise ValueError("API token and endpoint URL are required")

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using HuggingFace inference endpoint"""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": kwargs.get("max_tokens", 512),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "do_sample": True
            }
        }
        
        try:
            response = requests.post(self.endpoint_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()[0]["generated_text"]
        except Exception as e:
            return f"Error calling endpoint: {str(e)}"
