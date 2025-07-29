"""
torch_setup.py
This file provides utilities for setting up and configuring PyTorch in PromptDoctor, supporting model training and inference.
"""

import torch
import asyncio
from contextlib import contextmanager

@contextmanager
def torch_event_loop():
    """Context manager to handle PyTorch event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        loop.close()

def init_torch():
    """Initialize PyTorch settings"""
    # Ensure torch classes are registered
    torch.classes._jit_internal._init()
    # Disable grad for inference
    torch.set_grad_enabled(False)
    print("[PyTorch] Initialized successfully")
