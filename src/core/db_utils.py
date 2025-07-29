"""
db_utils.py
This file provides utilities for interacting with the database in PromptDoctor, including connection management and query execution.
"""

import sqlite3
import uuid
from datetime import datetime
import os

class DBManager:
    def __init__(self, db_path='data/study.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            user_id TEXT PRIMARY KEY,
            group_assignment TEXT CHECK(group_assignment IN ('A', 'B')),
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        conn.close()
    
    def assign_user_to_group(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count current group sizes
        cursor.execute("SELECT COUNT(*) FROM participants WHERE group_assignment = 'A'")
        count_a = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM participants WHERE group_assignment = 'B'")
        count_b = cursor.fetchone()[0]
        
        # Assign to the group with fewer participants
        if count_a < count_b:
            group = 'A'
        elif count_b < count_a:
            group = 'B'
        else:
            group = 'A' if uuid.uuid4().int % 2 == 0 else 'B'
        
        # Create unique user ID and insert
        user_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO participants (user_id, group_assignment) VALUES (?, ?)",
            (user_id, group)
        )
        
        conn.commit()
        conn.close()
        return user_id, group

    def assign_group_to_user(self, user_id: str) -> str:
        """Assign a group to an existing user ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if user already has group
        cursor.execute("SELECT group_assignment FROM participants WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return existing[0]
        
        # Count group sizes for new assignment
        cursor.execute("SELECT COUNT(*) FROM participants WHERE group_assignment = 'A'")
        count_a = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM participants WHERE group_assignment = 'B'")
        count_b = cursor.fetchone()[0]
        
        # Assign to smaller group
        if count_a <= count_b:
            group = 'A'
        else:
            group = 'B'
        
        # Insert new assignment
        cursor.execute(
            "INSERT INTO participants (user_id, group_assignment) VALUES (?, ?)",
            (user_id, group)
        )
        
        conn.commit()
        conn.close()
        return group
