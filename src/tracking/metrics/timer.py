"""
timer.py
This file provides timing utilities for measuring durations and performance of operations in PromptDoctor.
"""

from datetime import datetime
import time

class Timer:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.is_running = False

    def start(self):
        if not self.is_running:
            self.start_time = datetime.now()
            self.is_running = True

    def stop(self):
        if self.is_running and self.start_time is not None:
            self.end_time = datetime.now()
            self.is_running = False
            duration = (self.end_time - self.start_time).total_seconds()
            self.start_time = None
            self.end_time = None
            return duration
        return 0.0
