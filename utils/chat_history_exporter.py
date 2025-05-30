import os
import json
import pandas as pd
from datetime import datetime
import logging
from typing import List, Dict, Optional, Any
import traceback

# Configure logging
logger = logging.getLogger('chat_history_exporter')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class ChatHistoryExporter:
    """Utility for exporting and managing chat histories"""
    
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.merged_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'merged_data')
        self.chat_dir = os.path.join(self.data_dir, 'chat_history')
        
        # Ensure all directories exist
        for directory in [self.data_dir, self.merged_dir, self.chat_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def export_all_chat_history(self) -> str:
        """Export all chat history to a merged JSON file and return the path"""
        try:
            # Get all individual chat history files
            chat_files = []
            for root, _, files in os.walk(self.chat_dir):
                for file in files:
                    if file.endswith('.json'):
                        chat_files.append(os.path.join(root, file))
            
            # Read all chat histories
            all_chats = []
            for file_path in chat_files:
                try:
                    with open(file_path, 'r') as f:
                        chat_data = json.load(f)
                        all_chats.append(chat_data)
                except Exception as e:
                    logger.error(f"Error reading chat file {file_path}: {str(e)}")
            
            # Group by user_id and task_id
            chat_by_user_task = {}
            for chat in all_chats:
                user_id = chat.get('user_id', 'unknown')
                task_id = chat.get('task_id', 0)
                key = f"{user_id}_{task_id}"
                
                if key not in chat_by_user_task:
                    chat_by_user_task[key] = chat
                else:
                    # Compare timestamps and use the newer one
                    existing_timestamp = datetime.fromisoformat(chat_by_user_task[key].get('timestamp', '2000-01-01T00:00:00'))
                    new_timestamp = datetime.fromisoformat(chat.get('timestamp', '2000-01-01T00:00:00'))
                    
                    if new_timestamp > existing_timestamp:
                        chat_by_user_task[key] = chat
            
            # Create final merged list
            merged_chats = list(chat_by_user_task.values())
            
            # Save to merged JSON file
            merged_file = os.path.join(self.merged_dir, 'chat_history.json')
            with open(merged_file, 'w') as f:
                json.dump(merged_chats, f, indent=2)
            
            logger.info(f"Exported {len(merged_chats)} chat histories to {merged_file}")
            return merged_file
            
        except Exception as e:
            error_msg = f"Error exporting chat history: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return ""
    
    def get_chat_history_for_user(self, user_id: str) -> List[Dict]:
        """Get all chat history for a specific user"""
        try:
            merged_file = os.path.join(self.merged_dir, 'chat_history.json')
            if not os.path.exists(merged_file):
                return []
            
            with open(merged_file, 'r') as f:
                all_chats = json.load(f)
            
            # Filter to only include this user's chats
            user_chats = [chat for chat in all_chats if chat.get('user_id') == user_id]
            return user_chats
            
        except Exception as e:
            logger.error(f"Error getting chat history for user {user_id}: {str(e)}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about all chat histories"""
        try:
            merged_file = os.path.join(self.merged_dir, 'chat_history.json')
            if not os.path.exists(merged_file):
                return {"error": "No chat history found"}
            
            with open(merged_file, 'r') as f:
                all_chats = json.load(f)
            
            # Calculate statistics
            total_users = len(set(chat.get('user_id') for chat in all_chats))
            total_chats = len(all_chats)
            total_messages = sum(len(chat.get('messages', [])) for chat in all_chats)
            
            # Count by role
            user_messages = 0
            assistant_messages = 0
            system_messages = 0
            
            for chat in all_chats:
                for message in chat.get('messages', []):
                    role = message.get('role', '')
                    if role == 'user':
                        user_messages += 1
                    elif role == 'assistant':
                        assistant_messages += 1
                    elif role == 'system':
                        system_messages += 1
            
            # Count by task
            tasks = {}
            for chat in all_chats:
                task_id = chat.get('task_id', 0)
                if task_id not in tasks:
                    tasks[task_id] = 0
                tasks[task_id] += 1
            
            return {
                "total_users": total_users,
                "total_chats": total_chats,
                "total_messages": total_messages,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "system_messages": system_messages,
                "tasks": tasks,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting chat statistics: {str(e)}")
            return {"error": str(e)}

# Helper function to easily access chat exporter
def get_chat_exporter():
    return ChatHistoryExporter()
