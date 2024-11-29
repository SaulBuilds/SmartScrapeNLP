import os
import logging
from datetime import datetime
import shutil

class FileManager:
    def __init__(self):
        self.base_dir = os.path.join(os.getcwd(), 'data')
        self._ensure_base_directory()

    def _ensure_base_directory(self):
        """Create base directory if it doesn't exist"""
        try:
            os.makedirs(self.base_dir, exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create base directory: {str(e)}")

    def create_session_directory(self):
        """Create a new directory for the current scraping session"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_dir = os.path.join(self.base_dir, f'session_{timestamp}')
        try:
            os.makedirs(session_dir, exist_ok=True)
            return session_dir
        except Exception as e:
            logging.error(f"Failed to create session directory: {str(e)}")
            return None

    def save_content(self, session_dir, filename, content):
        """Save content to a file in the session directory"""
        try:
            filepath = os.path.join(session_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return filepath
        except Exception as e:
            logging.error(f"Failed to save content: {str(e)}")
            return None

    def cleanup_temp_files(self):
        """Clean up temporary files older than 24 hours"""
        try:
            current_time = datetime.now()
            for item in os.listdir(self.base_dir):
                item_path = os.path.join(self.base_dir, item)
                if os.path.isdir(item_path):
                    # Get directory creation time
                    created_time = datetime.fromtimestamp(os.path.getctime(item_path))
                    # Remove if older than 24 hours
                    if (current_time - created_time).days >= 1:
                        shutil.rmtree(item_path)
        except Exception as e:
            logging.error(f"Failed to cleanup temporary files: {str(e)}")

    def __del__(self):
        """Cleanup on object destruction"""
        self.cleanup_temp_files()