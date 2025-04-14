import streamlit as st
import datetime
from typing import Dict, Any, Tuple

class XAIProcessor:
    def __init__(self):
        # Initialize session state for XAI
        if "xai_queue" not in st.session_state:
            st.session_state.xai_queue = []
        if "xai_processing" not in st.session_state:
            st.session_state.xai_processing = False
        if "xai_results" not in st.session_state:
            st.session_state.xai_results = {}

    def debug_xai_processing(self, prompt: str, response: str, model_type: str) -> None:
        """Debug function for XAI processing"""
        print("\n=== XAI Processing Debug ===")
        print(f"Time: {datetime.datetime.now().isoformat()}")
        print(f"Prompt: {prompt[:100]}...")
        print(f"Response: {response[:100]}...")
        print(f"Model: {model_type}")
        print("Queue Status:")
        print(f"- Current queue size: {len(st.session_state.xai_queue)}")
        print(f"- Processing active: {st.session_state.xai_processing}")
        print(f"- Stored results: {len(st.session_state.xai_results)}")
        print("========================\n")

    def process_xai_request(self, prompt: str, response: str, model_type: str) -> Dict[str, Any]:
        """Process XAI request with debug info"""
        self.debug_xai_processing(prompt, response, model_type)
        
        print("[XAI] Starting processing...")
        import time
        time.sleep(2)  # Simulate processing
        
        result = {
            "prompt": prompt,
            "response": response,
            "explanation": f"Debug explanation for: {prompt[:50]}...",
            "timestamp": datetime.datetime.now().isoformat(),
            "debug_info": {
                "queue_size": len(st.session_state.xai_queue),
                "processing_time": 2.0,
                "model_type": model_type
            }
        }
        
        print("[XAI] Processing complete")
        print(f"[XAI] Result size: {len(str(result))} chars")
        return result

    def queue_xai_request(self, prompt: str, response: str, model_type: str) -> None:
        """Queue a new XAI request"""
        st.session_state.xai_queue.append((prompt, response, model_type))
        print(f"[XAI] Queued new request. Queue size: {len(st.session_state.xai_queue)}")

    def process_queue(self) -> None:
        """Process queued XAI requests"""
        if st.session_state.xai_processing or not st.session_state.xai_queue:
            return
            
        st.session_state.xai_processing = True
        try:
            prompt, response, model_type = st.session_state.xai_queue.pop(0)
            print(f"[XAI] Processing request for: {prompt[:50]}...")
            
            result = self.process_xai_request(prompt, response, model_type)
            st.session_state.xai_results[prompt] = result
            
        except Exception as e:
            print(f"[XAI] Error processing explanation: {str(e)}")
        finally:
            st.session_state.xai_processing = False
