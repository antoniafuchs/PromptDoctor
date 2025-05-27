import streamlit as st
import sys
import os

def init_torch():
    """
    Safely initialize PyTorch to avoid runtime errors with streamlit's watcher.
    This prevents the "no running event loop" and "torch._classes" errors.
    """
    try:
        # Only import torch inside this function to control when it's loaded
        import torch
        
        # Set environment variables to reduce warnings and improve compatibility
        os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
        
        # Basic configuration to reduce memory usage
        if torch.cuda.is_available():
            # Configure CUDA for lower memory usage
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        
        # Initialize empty models dictionary if not exists
        if 'loaded_models' not in st.session_state:
            st.session_state.loaded_models = {}
            
        # Return success message
        return "PyTorch initialized successfully"
        
    except ImportError:
        print("[WARNING] PyTorch not available. Some features may be limited.")
        return "PyTorch not available"
    except Exception as e:
        # Print error but don't stop execution
        print(f"[WARNING] Error initializing PyTorch: {str(e)}")
        return f"Error initializing PyTorch: {str(e)}"

def get_device():
    """
    Get the best available device for PyTorch operations.
    Returns 'cuda', 'mps' (Mac M1/M2), or 'cpu' based on availability.
    """
    try:
        import torch
        
        if torch.cuda.is_available():
            return 'cuda'
        elif hasattr(torch, 'backends') and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            # For Apple Silicon (M1/M2)
            return 'mps'
        else:
            return 'cpu'
    except:
        return 'cpu'
