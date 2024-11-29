import os
import logging
from flask import Flask, render_template, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from scraper.web_crawler import WebCrawler
from utils.llm_handler import LLMHandler
from utils.file_manager import FileManager
from scraper.content_analyzer import ContentAnalyzer
import json
import time
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
    try:
        message = request.json.get('message')
        if not message:
            return jsonify({'error': 'No message provided'}), 400
            
        logger.info(f"Processing chat message: {message[:50]}...")
        
        # Process user input using LLM
        result = llm_handler.process_user_input(message)
        logger.info(f"LLM suggested {len(result['websites'])} websites")
        
        return jsonify({
            'response': result['message'],
            'websites': result['websites']
        })
        
    except Exception as e:
        logger.error(f"Chat processing error: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to process chat message',
            'message': str(e)
        }), 500

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """Handle website scraping requests"""
    client_id = request.headers.get('X-Client-Id', str(time.time()))
    
    try:
        websites = request.json.get('websites', [])
        if not websites:
            return jsonify({'error': 'No websites provided'}), 400
            
        logger.info(f"Starting scraping process for {len(websites)} websites")
        
        # Create session directory
        session_dir = file_manager.create_session_directory()
        if not session_dir:
            raise Exception("Failed to create session directory")
            
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
                
                # Scrape website
                content = web_crawler.scrape_website(url)
                if not content:
                    error_msg = 'Failed to scrape content'
                    errors.append({'url': url, 'error': error_msg})
                    logger.error(f"Error scraping {url}: {error_msg}")
                    send_sse_message(client_id, f"Failed to scrape {url}", 'log', 'error')
                    continue
                
                # Save raw content
                file_manager.save_content(
                    session_dir,
                    f"raw_{index}.html",
                    content
                )
                
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
                    
            except Exception as e:
                error_msg = str(e)
                errors.append({'url': url, 'error': error_msg})
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
                'message': 'All websites failed to process',
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
            'message': 'Scraping completed successfully'
        })
        
    except Exception as e:
        logger.error(f"Scraping process failed: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Scraping process failed',
            'message': str(e)
        }), 500

@app.route('/api/folder-structure')
def get_folder_structure():
    """Get the current folder structure"""
    try:
        structure = file_manager.get_folder_structure()
        return jsonify(structure)
    except Exception as e:
        logger.error(f"Failed to get folder structure: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

with app.app_context():
    import models
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
