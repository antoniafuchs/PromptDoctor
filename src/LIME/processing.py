"""
processing.py
This file provides data processing utilities for LIME explanations in PromptDoctor, supporting model interpretability and visualization.
"""

import streamlit as st
import datetime
import os
import numpy as np
from typing import Dict, Any, Tuple
from LIME.lime_processor import LIMEProcessor

class XAIProcessor:
    def __init__(self):
        # Initialize session state for XAI
        if "xai_queue" not in st.session_state:
            st.session_state.xai_queue = []
        if "xai_processing" not in st.session_state:
            st.session_state.xai_processing = False
        if "xai_results" not in st.session_state:
            st.session_state.xai_results = {}
        self.lime_processor = LIMEProcessor()
        print("[XAI] Initialized with LIME processor")

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
        """Process XAI request with LIME"""
        self.debug_xai_processing(prompt, response, model_type)
        
        print("[XAI] Starting LIME analysis...")
        try:
            explanation = self.lime_processor.explain_text(prompt, model_type)
            
            if "error" in explanation:
                return {
                    "prompt": prompt,
                    "response": response,
                    "explanation": f"Analysis failed: {explanation['error']}",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "status": "error",
                    "html": "<p>Error generating visualization</p>"
                }
            
            result = {
                "prompt": prompt,
                "response": response,
                "explanation": self._format_explanation(explanation),
                "timestamp": datetime.datetime.now().isoformat(),
                "importance": {
                    "words": explanation["words"],
                    "scores": explanation["scores"]
                },
                "html": explanation["html"],
                "html_path": explanation.get("html_path"),
                "status": "success"
            }
            
            print(f"[XAI] LIME analysis complete. HTML saved to: {explanation.get('html_path')}")
            return result
            
        except Exception as e:
            print(f"[XAI] Analysis failed: {str(e)}")
            return {
                "prompt": prompt,
                "response": response,
                "explanation": f"Analysis failed: {str(e)}",
                "timestamp": datetime.datetime.now().isoformat(),
                "status": "error",
                "html": "<p>Error generating visualization</p>"
            }

    def _format_explanation(self, explanation: Dict[str, Any]) -> str:
        """Format LIME explanation for display"""
        if not explanation["words"]:
            return "No explanation available"
            
        formatted = "Key words and their impact:\n\n"
        for word, score in zip(explanation["words"], explanation["scores"]):
            impact = "POSITIVE" if score > 0 else "NEGATIVE"
            formatted += f"{word}: {impact} impact ({abs(score):.3f})\n"
        
        return formatted

    def queue_xai_request(self, prompt: str, response: str, model_type: str) -> None:
        """Queue a new XAI request"""
        st.session_state.xai_queue.append((prompt, response, model_type))
        print(f"[XAI] Queued new request. Queue size: {len(st.session_state.xai_queue)}")

    def process_queue(self) -> None:
        """Process queued XAI requests without blocking"""
        if st.session_state.xai_processing or not st.session_state.xai_queue:
            return
            
        st.session_state.xai_processing = True
        try:
            prompt, response, model_type = st.session_state.xai_queue[0]
            result = self.process_xai_request(prompt, response, model_type)
            
            if result["status"] == "success":
                st.session_state.xai_queue.pop(0)
                st.session_state.xai_results[prompt] = result
            else:
                # Keep in queue for retry if failed
                print(f"[XAI] Analysis failed, will retry: {result['explanation']}")
                
        except Exception as e:
            print(f"[XAI] Queue processing error: {str(e)}")
        finally:
            st.session_state.xai_processing = False
            
    def process_queue_immediately(self) -> Dict[str, Any]:
        """Process the first item in queue immediately and return the result"""
        if not st.session_state.xai_queue:
            print("[XAI] No items in queue to process immediately")
            return None
            
        try:
            prompt, response, model_type = st.session_state.xai_queue[0]
            result = self.process_xai_request(prompt, response, model_type)
            
            if result["status"] == "success":
                st.session_state.xai_queue.pop(0)
                st.session_state.xai_results[prompt] = result
                print(f"[XAI] Analysis complete and added to results. Results count: {len(st.session_state.xai_results)}")
                return result
            else:
                print(f"[XAI] Immediate analysis failed: {result['explanation']}")
                return result
                
        except Exception as e:
            print(f"[XAI] Immediate processing error: {str(e)}")
            return {
                "status": "error",
                "explanation": f"Analysis failed: {str(e)}",
                "html": "<p>Error processing explanation</p>"
            }

    def get_html_results_dir(self) -> str:
        """Return the path to the HTML results directory"""
        return self.lime_processor.html_dir
