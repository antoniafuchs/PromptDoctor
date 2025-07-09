import streamlit as st
import sys
import os
import logging
import traceback

def init_torch():
    """
    Initialize PyTorch with safety measures to avoid path errors
    """
    try:
        # First disable JIT which is often a source of path errors
        os.environ["PYTORCH_JIT"] = "0"
        
        # Also set CUDA device order for consistency
        os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        
        # Import PyTorch with error handling
        try:
            import torch
            # Use simple functions that don't involve custom classes
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[INFO] PyTorch initialized on device: {device}")
            
            # Disable gradients for inference (saves memory and avoids some errors)
            torch.set_grad_enabled(False)
            
            # Set resource limits
            if device == "cpu":
                torch.set_num_threads(4)  # Limit CPU threads to avoid resource issues
                
            # Return success
            return True
        except ImportError:
            print("[WARNING] PyTorch not installed")
            return False
        except Exception as e:
            print(f"[ERROR] PyTorch initialization error: {str(e)}")
            print(traceback.format_exc())
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed during PyTorch environment setup: {str(e)}")
        return False

def safe_get_device():
    """
    Safely determine compute device without triggering path errors
    """
    try:
        # Disable JIT before importing torch
        os.environ["PYTORCH_JIT"] = "0"
        
        # Try to import torch safely
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except:
        # Default to CPU if anything goes wrong
        return "cpu"
