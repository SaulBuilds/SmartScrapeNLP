import os
import logging
from datetime import datetime
import shutil
import stat
import json

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self):
        self.base_dir = os.path.join(os.getcwd(), 'data')
        self._ensure_base_directory()

    def _ensure_base_directory(self):
        """Create base directory if it doesn't exist with proper permissions"""
        try:
            if not os.path.exists(self.base_dir):
                os.makedirs(self.base_dir, mode=0o755, exist_ok=True)
                logger.info(f"Created base directory: {self.base_dir}")
            else:
                # Ensure proper permissions
                os.chmod(self.base_dir, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                logger.info(f"Updated permissions for base directory: {self.base_dir}")
        except Exception as e:
            logger.error(f"Failed to create/update base directory: {str(e)}", exc_info=True)
            raise Exception(f"Failed to initialize file system: {str(e)}")

    def create_session_directory(self):
        """Create a new directory for the current scraping session with proper permissions"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_dir = os.path.join(self.base_dir, f'session_{timestamp}')
        
        try:
            if os.path.exists(session_dir):
                logger.warning(f"Session directory already exists: {session_dir}")
                # Ensure unique directory name
                counter = 1
                while os.path.exists(f"{session_dir}_{counter}"):
                    counter += 1
                session_dir = f"{session_dir}_{counter}"
            
            # Create main session directory
            os.makedirs(session_dir, mode=0o755)
            logger.info(f"Created session directory: {session_dir}")
            
            # Create subdirectories for different content types
            subdirs = ['html', 'text', 'images']
            for subdir in subdirs:
                subdir_path = os.path.join(session_dir, subdir)
                os.makedirs(subdir_path, mode=0o755)
                os.chmod(subdir_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                logger.info(f"Created {subdir} directory: {subdir_path}")
            
            # Ensure proper permissions for main directory
            os.chmod(session_dir, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            
            return session_dir
        except Exception as e:
            logger.error(f"Failed to create session directory: {str(e)}", exc_info=True)
            raise Exception(f"Failed to create session directory: {str(e)}")

    def save_content(self, session_dir, filename, content, content_type='html'):
        """Save content to a file in the session directory with proper error handling"""
        try:
            if not os.path.exists(session_dir):
                raise Exception(f"Session directory does not exist: {session_dir}")
            
            # Determine the appropriate subdirectory based on content type
            subdir = os.path.join(session_dir, content_type)
            if not os.path.exists(subdir):
                os.makedirs(subdir, mode=0o755)
                os.chmod(subdir, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            
            # Ensure filename is safe
            safe_filename = os.path.basename(filename)
            if safe_filename != filename:
                logger.warning(f"Sanitized filename from {filename} to {safe_filename}")
                safe_filename = filename
            
            filepath = os.path.join(subdir, safe_filename)
            
            # Handle different content types
            if content_type == 'images':
                with open(filepath, 'wb') as f:
                    f.write(content)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Set proper file permissions
            os.chmod(filepath, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            
            logger.info(f"Successfully saved {content_type} content to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save content: {str(e)}", exc_info=True)
            raise Exception(f"Failed to save content: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to save content: {str(e)}", exc_info=True)
            raise Exception(f"Failed to save content: {str(e)}")

    def get_folder_structure(self):
        """Get the current folder structure as a tree"""
        try:
            def create_tree(path):
                name = os.path.basename(path)
                if os.path.isfile(path):
                    return {
                        'name': name,
                        'type': 'file'
                    }
                else:
                    return {
                        'name': name,
                        'type': 'directory',
                        'children': sorted(
                            [create_tree(os.path.join(path, x)) 
                             for x in os.listdir(path)],
                            key=lambda x: (x['type'] == 'file', x['name'])
                        )
                    }
            
            if not os.path.exists(self.base_dir):
                return {'name': 'data', 'type': 'directory', 'children': []}
                
            return create_tree(self.base_dir)
            
        except Exception as e:
            logger.error(f"Failed to get folder structure: {str(e)}", exc_info=True)
            raise Exception(f"Failed to get folder structure: {str(e)}")

    def cleanup_temp_files(self):
        """Clean up temporary files older than 24 hours with proper error handling"""
        try:
            if not os.path.exists(self.base_dir):
                logger.warning("Base directory does not exist, skipping cleanup")
                return
                
            current_time = datetime.now()
            for item in os.listdir(self.base_dir):
                try:
                    item_path = os.path.join(self.base_dir, item)
                    if os.path.isdir(item_path):
                        # Get directory creation time
                        created_time = datetime.fromtimestamp(os.path.getctime(item_path))
                        # Remove if older than 24 hours
                        if (current_time - created_time).days >= 1:
                            shutil.rmtree(item_path)
                            logger.info(f"Cleaned up old session: {item_path}")
                except Exception as e:
                    logger.error(f"Failed to cleanup {item}: {str(e)}", exc_info=True)
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to cleanup temporary files: {str(e)}", exc_info=True)
            # Don't raise the exception here as this is a cleanup operation

    def __del__(self):
        """Cleanup on object destruction"""
        try:
            self.cleanup_temp_files()
        except Exception as e:
            logger.error(f"Failed during cleanup in destructor: {str(e)}", exc_info=True)
