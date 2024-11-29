import os
import re
import tempfile
import shutil
import json
import hashlib
import logging
from datetime import datetime

class FileManager:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.active_files = set()
        self.base_dir = os.path.expanduser("~/Desktop")
        self._ensure_base_directory()

    def _ensure_base_directory(self):
        """Ensure base directory exists"""
        try:
            os.makedirs(self.base_dir, exist_ok=True)
            logging.info(f"Base directory ensured at: {self.base_dir}")
        except Exception as e:
            logging.error(f"Failed to create base directory: {str(e)}")
            raise RuntimeError(f"Failed to create base directory: {str(e)}")

    def create_scraping_session(self):
        """Create a new scraping session directory"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            session_dir = os.path.join(self.base_dir, f"web_scraper_data_{timestamp}")
            os.makedirs(session_dir, exist_ok=True)
            logging.info(f"Created scraping session directory: {session_dir}")
            return session_dir
        except Exception as e:
            logging.error(f"Failed to create scraping session directory: {str(e)}")
            raise RuntimeError(f"Failed to create scraping session directory: {str(e)}")

    def create_website_directory(self, session_dir, url):
        """Create directory structure for a website"""
        try:
            if not url or not session_dir:
                raise ValueError("Invalid URL or session directory")
                
            # Create a safe directory name from the URL
            website_name = re.sub(r'[^\w\-_]', '_', url.split('//')[-1].split('/')[0])
            website_dir = os.path.join(session_dir, website_name)
            
            # Create subdirectories
            os.makedirs(os.path.join(website_dir, 'text'), exist_ok=True)
            os.makedirs(os.path.join(website_dir, 'images'), exist_ok=True)
            
            logging.info(f"Created website directory structure for: {url}")
            return website_dir
        except Exception as e:
            logging.error(f"Failed to create website directory for {url}: {str(e)}")
            raise RuntimeError(f"Failed to create website directory: {str(e)}")

    def store_content(self, website_dir, content, content_type='text'):
        """Store content in appropriate directory"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if content_type == 'text':
            file_path = os.path.join(website_dir, 'text', f'content_{timestamp}.html')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        elif content_type == 'image':
            file_path = os.path.join(website_dir, 'images', f'image_{timestamp}.jpg')
            with open(file_path, 'wb') as f:
                f.write(content)
                
        return file_path

    def store_temp_content(self, content):
        """Store content in temporary file and return path"""
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
