import torch
import warnings
import asyncio

def init_torch():
    """Initialize PyTorch with proper warning handling and device settings"""
    try:
        # Suppress specific PyTorch deprecation warning
        warnings.filterwarnings(
            "ignore",
            message="torch.set_default_tensor_type()",
            category=UserWarning
        )
        
        # Set default device
        if torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
        torch.set_default_device(device)
        
        # Set default dtype
        torch.set_default_dtype(torch.float32)
        
        print(f"[PyTorch] Initialized successfully on {device}")
        return True
    except Exception as e:
        print(f"[PyTorch] Initialization error: {str(e)}")
        return False

def ensure_event_loop():
    """Ensure an event loop is running"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop
