import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.xai.processing import XAIProcessor
from utils.model_config import ModelConfig

async def test_xai():
    processor = XAIProcessor()
    model_config = ModelConfig()
    
    # Test with DistilGPT2
    model, tokenizer = model_config.load_hf_model("distilgpt2")
    
    if model and tokenizer:
        print("Model loaded successfully")
        
        # Test processing
        result = await processor._process_async(
            prompt="Test input",
            response="Test response",
            model_type="HuggingFace",
            method="lime"
        )
        print(f"Processing result: {result}")

def test_model_initialization():
    model_name = "distilbert/distilgpt2"  # Example model
    model, tokenizer = ModelConfig.initialize_hf_model(model_name)
    
    # Test tokenization with padding
    texts = ["Patient has fever", "Doctor recommends rest"]
    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        return_tensors="pt"
    )
    
    print("Tokenizer pad token:", tokenizer.pad_token)
    print("Model pad token ID:", model.config.pad_token_id)
    print("Input shape:", inputs.input_ids.shape)
    
    return model, tokenizer

if __name__ == "__main__":
    asyncio.run(test_xai())
    test_model_initialization()
