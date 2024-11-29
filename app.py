import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from scraper.web_crawler import WebCrawler
from utils.llm_handler import LLMHandler
from utils.file_manager import FileManager
from scraper.content_analyzer import ContentAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages and return relevant websites"""
    try:
        message = request.json.get('message')
        if not message:
            return jsonify({'error': 'No message provided'}), 400
            
        # Process user input using LLM
        result = llm_handler.process_user_input(message)
        
        return jsonify({
            'response': result['message'],
            'websites': result['websites']
        })
        
    except Exception as e:
        logging.error(f"Chat processing error: {str(e)}")
        return jsonify({
            'error': 'Failed to process chat message',
            'message': str(e)
        }), 500

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """Handle website scraping requests"""
    try:
        websites = request.json.get('websites', [])
        if not websites:
            return jsonify({'error': 'No websites provided'}), 400
            
        # Create session directory
        session_dir = file_manager.create_session_directory()
        
        analyzed_data = []
        errors = []
        
        for url in websites:
            try:
                # Scrape website
                content = web_crawler.scrape_website(url)
                if not content:
                    errors.append({'url': url, 'error': 'Failed to scrape content'})
                    continue
                    
                # Analyze content
                result = content_analyzer.analyze_content([{'url': url, 'content': content}])
                if result:
                    analyzed_data.extend(result)
                    
            except Exception as e:
                errors.append({'url': url, 'error': str(e)})
                
        if not analyzed_data and errors:
            return jsonify({
                'error': 'Content analysis failed',
                'message': 'All websites failed to process',
                'errors': errors
            }), 500
            
        return jsonify({
            'analyzed_data': analyzed_data,
            'session_dir': session_dir,
            'errors': errors,
            'message': 'Scraping completed successfully'
        })
        
    except Exception as e:
        logging.error(f"Scraping process failed: {str(e)}")
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
        return jsonify({'error': str(e)}), 500

with app.app_context():
    import models
    db.create_all()