import torch

def init_torch():
    """Basic PyTorch initialization"""
    torch.set_grad_enabled(False)
    if torch.cuda.is_available():
        torch.set_default_tensor_type('torch.cuda.FloatTensor')
    else:
        torch.set_default_tensor_type('torch.FloatTensor')
    print("[PyTorch] Initialized successfully")
