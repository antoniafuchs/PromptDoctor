import streamlit as st
import sys
import os

def init_torch():
    """
    Safely initialize PyTorch to avoid runtime errors with streamlit's watcher.
    This prevents the "no running event loop" and "torch._classes" errors.
    
    PyTorch is used for:
    1. LIME explainer (explainable AI for medical terms)
    2. HuggingFace model inference
    3. XAI functionality
    """
    try:
        # Set environment variables to reduce warnings and improve compatibility
        os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
        
        # Initialize empty models dictionary if not exists
        if 'loaded_models' not in st.session_state:
            st.session_state.loaded_models = {}
            
        # We avoid importing torch at the module level to prevent Streamlit watcher issues
        # All torch imports are done inside functions where they're actually needed
        
        # Check if CUDA is available without crashing
        try:
            # Import torch only inside this block to avoid module-level import
            import torch
            has_cuda = torch.cuda.is_available()
            # Perform very basic configuration only when needed
            if has_cuda:
                print("[INFO] CUDA is available, optimizing settings")
        except Exception as e:
            print(f"[WARNING] Error checking CUDA: {e}")
            
        # Return success message
        return "PyTorch initialized successfully"
        
    except Exception as e:
        # Print error but don't stop execution
        print(f"[WARNING] Error in init_torch: {str(e)}")
        return f"Error initializing PyTorch: {str(e)}"

def get_device():
    """
    Get the best available device for PyTorch operations.
    Returns 'cuda', 'mps' (Mac M1/M2), or 'cpu' based on availability.
    
    This helps optimize model performance by using hardware acceleration when available.
    """
    try:
        # Import torch locally to avoid module-level import issues
        import torch
        
        # Check for CUDA (NVIDIA GPUs)
        if torch.cuda.is_available():
            return 'cuda'
        # Check for MPS (Apple Silicon M1/M2 GPUs)
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return 'mps'
        # Fall back to CPU
        else:
            return 'cpu'
    except Exception as e:
        print(f"[WARNING] Error determining PyTorch device: {e}")
        return 'cpu'
