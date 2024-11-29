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
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "intelligent_scraper_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///scraper.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Initialize components
llm_handler = LLMHandler()
file_manager = FileManager()
web_crawler = WebCrawler()
content_analyzer = ContentAnalyzer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    
    # Get topic and relevant websites from LLM
    chat_response = llm_handler.process_user_input(user_message)
    
    return jsonify({
        'response': chat_response['message'],
        'websites': chat_response.get('websites', [])
    })

@app.route('/api/scrape', methods=['POST'])
def scrape():
    try:
        websites = request.json.get('websites', [])
        
        if not websites:
            return jsonify({
                'error': 'No websites provided',
                'message': 'Please select at least one website to scrape'
            }), 400
        
        logging.info(f"Starting scraping process for {len(websites)} websites")
        
        # Create new session directory
        session_dir = file_manager.create_scraping_session()
        
        # Scrape and analyze websites
        scraped_data = []
        analyzed_data = []
        errors = []
        
        for website in websites:
            try:
                if not web_crawler.is_valid_url(website):
                    errors.append({
                        'url': website,
                        'error': 'Invalid URL format'
                    })
                    continue
                
                logging.info(f"Scraping website: {website}")
                content = web_crawler.scrape_website(website)
                
                if not content:
                    errors.append({
                        'url': website,
                        'error': 'Failed to fetch content'
                    })
                    continue
                
                # Create website directory
                website_dir = file_manager.create_website_directory(session_dir, website)
                
                # Store main content
                content_path = file_manager.store_content(website_dir, content, 'text')
                logging.info(f"Stored content for {website}")
                
                scraped_data.append({
                    'url': website,
                    'content': content,
                    'content_path': content_path
                })
                
                # Extract and store images
                images = content_analyzer._process_images(content)
                for img in images:
                    try:
                        img_url = img['url']
                        img_content = web_crawler.download_image(img_url)
                        if img_content:
                            img_path = file_manager.store_content(website_dir, img_content, 'image')
                            img['stored_path'] = img_path
                    except Exception as e:
                        logging.error(f"Error downloading image {img_url}: {str(e)}")
                        errors.append({
                            'url': img_url,
                            'error': f"Failed to download image: {str(e)}"
                        })
            
            except Exception as e:
                logging.error(f"Error processing website {website}: {str(e)}")
                errors.append({
                    'url': website,
                    'error': str(e)
                })
        
        # Analyze content
        if scraped_data:
            try:
                analyzed_data = content_analyzer.analyze_content(scraped_data)
                logging.info("Content analysis completed successfully")
            except Exception as e:
                logging.error(f"Error analyzing content: {str(e)}")
                return jsonify({
                    'error': 'Content analysis failed',
                    'message': str(e),
                    'errors': errors
                }), 500
        
        return jsonify({
            'analyzed_data': analyzed_data,
            'session_dir': session_dir,
            'errors': errors,
            'message': 'Scraping completed with {} successful sites'.format(len(analyzed_data))
        })
        
    except Exception as e:
        logging.error(f"Scraping process failed: {str(e)}")
        return jsonify({
            'error': 'Scraping process failed',
            'message': str(e)
        }), 500

with app.app_context():
    import models
    db.create_all()
