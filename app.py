import os
import logging
from flask import Flask, render_template, request, jsonify, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from scraper.web_crawler import WebCrawler
from utils.llm_handler import LLMHandler
from utils.file_manager import FileManager
from scraper.content_analyzer import ContentAnalyzer
import json
import time
import shutil
from queue import Queue
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "intelligent_scraper_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///scraper.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Initialize components
llm_handler = LLMHandler()
web_crawler = WebCrawler()
content_analyzer = ContentAnalyzer()
file_manager = FileManager()

# Message queue for SSE
message_queues = {}

def send_sse_message(client_id, message, event_type='log', level='info'):
    if client_id in message_queues:
        message_queues[client_id].put({
            'event': event_type,
            'data': json.dumps({
                'message': message,
                'level': level
            })
        })

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/stream')
def stream():
    """SSE endpoint for real-time updates"""
    def event_stream(client_id):
        message_queues[client_id] = Queue()
        try:
            while True:
                if client_id in message_queues:
                    try:
                        message = message_queues[client_id].get(timeout=30)
                        yield f"event: {message['event']}\ndata: {message['data']}\n\n"
                    except:
                        yield f"event: ping\ndata: keepalive\n\n"
                else:
                    break
                time.sleep(0.5)
        finally:
            if client_id in message_queues:
                del message_queues[client_id]

    client_id = request.headers.get('X-Client-Id', str(time.time()))
    return Response(
        event_stream(client_id),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages and return relevant websites"""
    client_id = request.headers.get('X-Client-Id', str(time.time()))
    try:
        message = request.json.get('message')
        if not message:
            logger.warning("Empty message received in chat endpoint")
            return jsonify({'error': 'No message provided', 'details': 'Message content is required'}), 400
            
        logger.info(f"Processing chat message: {message[:50]}...")
        send_sse_message(client_id, "Processing your request...", 'log', 'info')
        
        # Process user input using LLM
        result = llm_handler.process_user_input(message)
        if not result or 'error' in result:
            error_msg = result.get('message', 'Unknown error in LLM processing')
            logger.error(f"LLM processing failed: {error_msg}")
            send_sse_message(client_id, f"Error: {error_msg}", 'log', 'error')
            return jsonify({
                'error': 'LLM processing failed',
                'details': error_msg
            }), 500
        
        logger.info(f"LLM suggested {len(result['websites'])} websites")
        send_sse_message(client_id, f"Found {len(result['websites'])} relevant websites", 'log', 'info')
        
        return jsonify({
            'response': result['message'],
            'websites': result['websites']
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Chat processing error: {error_msg}", exc_info=True)
        send_sse_message(client_id, f"Error: {error_msg}", 'log', 'error')
        return jsonify({
            'error': 'Failed to process chat message',
            'details': error_msg,
            'type': type(e).__name__
        }), 500

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """Handle website scraping requests"""
    client_id = request.headers.get('X-Client-Id', str(time.time()))
    
    try:
        websites = request.json.get('websites', [])
        if not websites:
            logger.warning("No websites provided for scraping")
            return jsonify({
                'error': 'No websites provided',
                'details': 'At least one website URL is required'
            }), 400
            
        logger.info(f"Starting scraping process for {len(websites)} websites")
        send_sse_message(client_id, f"Starting to process {len(websites)} websites", 'log', 'info')
        
        # Create session directory
        try:
            session_dir = file_manager.create_session_directory()
            if not session_dir:
                raise Exception("Failed to create session directory")
        except Exception as e:
            logger.error(f"Session directory creation failed: {str(e)}", exc_info=True)
            send_sse_message(client_id, "Failed to initialize scraping session", 'log', 'error')
            return jsonify({
                'error': 'Session initialization failed',
                'details': str(e)
            }), 500
            
        analyzed_data = []
        errors = []
        
        total_websites = len(websites)
        for index, url in enumerate(websites, 1):
            try:
                progress = (index - 1) / total_websites * 100
                send_sse_message(
                    client_id,
                    f"Processing {url}",
                    'progress',
                    {'progress': progress, 'message': f"Scraping {url}"}
                )
                
                logger.info(f"Scraping website: {url}")
                
                # Validate URL
                if not web_crawler.is_valid_url(url):
                    raise ValueError(f"Invalid URL format: {url}")
                
                # Scrape website
                content = web_crawler.scrape_website(url)
                if not content:
                    error_msg = 'Failed to scrape content'
                    errors.append({
                        'url': url,
                        'error': error_msg,
                        'type': 'content_extraction_error'
                    })
                    logger.error(f"Error scraping {url}: {error_msg}")
                    send_sse_message(client_id, f"Failed to scrape {url}", 'log', 'error')
                    continue
                
                # Save content in different formats
                try:
                    # Save HTML content
                    file_manager.save_content(
                        session_dir,
                        f"content_{index}.html",
                        content['html'],
                        'html'
                    )
                    send_sse_message(
                        client_id,
                        f"Saved HTML content from {url}",
                        'progress',
                        {'progress': progress + 25, 'message': f"Saving HTML content from {url}"}
                    )

                    # Save text content
                    if content['text']:
                        file_manager.save_content(
                            session_dir,
                            f"content_{index}.txt",
                            content['text'],
                            'text'
                        )
                        send_sse_message(
                            client_id,
                            f"Saved text content from {url}",
                            'progress',
                            {'progress': progress + 50, 'message': f"Saving text content from {url}"}
                        )

                    # Save images
                    for img_idx, img in enumerate(content['images']):
                        file_manager.save_content(
                            session_dir,
                            img['filename'],
                            img['content'],
                            'images'
                        )
                    if content['images']:
                        send_sse_message(
                            client_id,
                            f"Saved {len(content['images'])} images from {url}",
                            'progress',
                            {'progress': progress + 75, 'message': f"Saving images from {url}"}
                        )

                except Exception as e:
                    logger.error(f"Failed to save content for {url}: {str(e)}")
                    send_sse_message(client_id, f"Failed to save content from {url}", 'log', 'error')
                
                # Analyze content
                logger.info(f"Analyzing content from {url}")
                result = content_analyzer.analyze_content([{
                    'url': url,
                    'content': content
                }])
                
                if result:
                    analyzed_data.extend(result)
                    send_sse_message(
                        client_id,
                        f"Successfully analyzed {url}",
                        'log',
                        'info'
                    )
                    
            except ValueError as e:
                error_msg = str(e)
                errors.append({'url': url, 'error': error_msg, 'type': 'validation_error'})
                logger.error(f"Validation error for {url}: {error_msg}")
                send_sse_message(client_id, f"Error: {error_msg}", 'log', 'error')
                
            except Exception as e:
                error_msg = str(e)
                errors.append({'url': url, 'error': error_msg, 'type': type(e).__name__})
                logger.error(f"Error processing {url}: {error_msg}", exc_info=True)
                send_sse_message(
                    client_id,
                    f"Error processing {url}: {error_msg}",
                    'log',
                    'error'
                )
                
        if not analyzed_data and errors:
            logger.error("All websites failed to process")
            return jsonify({
                'error': 'Content analysis failed',
                'details': 'All websites failed to process',
                'errors': errors
            }), 500
            
        send_sse_message(
            client_id,
            "Scraping completed",
            'progress',
            {'progress': 100, 'status': 'complete'}
        )
        
        logger.info(f"Scraping completed. Processed {len(analyzed_data)} websites successfully")
        
        return jsonify({
            'analyzed_data': analyzed_data,
            'session_dir': session_dir,
            'errors': errors,
            'message': 'Scraping completed successfully',
            'stats': {
                'total': len(websites),
                'successful': len(analyzed_data),
                'failed': len(errors)
            }
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Scraping process failed: {error_msg}", exc_info=True)
        send_sse_message(client_id, f"Fatal error: {error_msg}", 'log', 'error')
        return jsonify({
            'error': 'Scraping process failed',
            'details': error_msg,
            'type': type(e).__name__
        }), 500

@app.route('/api/folder-structure')
def get_folder_structure():
    """Get the current folder structure"""
    try:
        structure = file_manager.get_folder_structure()
        return jsonify(structure)
    except Exception as e:
        logger.error(f"Failed to get folder structure: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to get folder structure',
            'details': str(e)
        }), 500

@app.route('/api/download')
def download_file():
    """Download a single file"""
    try:
        file_path = request.args.get('path')
        if not file_path:
            return jsonify({'error': 'No file path provided'}), 400
            
        # Ensure the file is within the data directory
        abs_path = os.path.abspath(os.path.join(file_manager.base_dir, file_path))
        if not abs_path.startswith(file_manager.base_dir):
            return jsonify({'error': 'Invalid file path'}), 403
            
        if not os.path.isfile(abs_path):
            return jsonify({'error': 'File not found'}), 404
            
        return send_file(abs_path, as_attachment=True)
    except Exception as e:
        logger.error(f"File download failed: {str(e)}", exc_info=True)
        return jsonify({'error': 'Download failed', 'details': str(e)}), 500

@app.route('/api/download-folder')
def download_folder():
    """Download a folder as ZIP"""
    try:
        folder_path = request.args.get('path')
        if not folder_path:
            return jsonify({'error': 'No folder path provided'}), 400
            
        # Ensure the folder is within the data directory
        abs_path = os.path.abspath(os.path.join(file_manager.base_dir, folder_path))
        if not abs_path.startswith(file_manager.base_dir):
            return jsonify({'error': 'Invalid folder path'}), 403
            
        if not os.path.isdir(abs_path):
            return jsonify({'error': 'Folder not found'}), 404
            
        # Create a temporary file for the ZIP
        temp_file = os.path.join(file_manager.base_dir, f'temp_{int(time.time())}.zip')
        try:
            shutil.make_archive(temp_file[:-4], 'zip', abs_path)
            return send_file(temp_file, as_attachment=True, download_name=f"{os.path.basename(folder_path)}.zip")
        finally:
            # Clean up temp file in background
            def cleanup():
                time.sleep(1)  # Wait for file to be sent
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            Thread(target=cleanup).start()
    except Exception as e:
        logger.error(f"Folder download failed: {str(e)}", exc_info=True)
        return jsonify({'error': 'Download failed', 'details': str(e)}), 500
with app.app_context():
    import models
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
