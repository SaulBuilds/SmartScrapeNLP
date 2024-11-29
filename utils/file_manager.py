import os
import tempfile
import shutil
import json
import hashlib
from datetime import datetime

class FileManager:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.active_files = set()

    def store_temp_content(self, content):
        """Store content in temporary file and return path"""
        # Create unique filename based on content hash
        content_hash = hashlib.md5(content.encode()).hexdigest()
        temp_path = os.path.join(self.temp_dir, f"{content_hash}.html")
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.active_files.add(temp_path)
        return temp_path

    def save_processed_data(self, data, topic):
        """Save processed data as JSON"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"processed_{topic}_{timestamp}.json"
        
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        return output_path

    def cleanup_temp_files(self):
        """Remove temporary files and directory"""
        for file_path in self.active_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error removing file {file_path}: {str(e)}")
        
        self.active_files.clear()
        
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Error removing temporary directory: {str(e)}")

    def __del__(self):
        """Cleanup on object destruction"""
        self.cleanup_temp_files()
