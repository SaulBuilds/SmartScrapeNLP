import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from scraper.web_crawler import WebCrawler
from utils.llm_handler import LLMHandler
from utils.file_manager import FileManager
from scraper.content_analyzer import ContentAnalyzer

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
    websites = request.json.get('websites', [])
    
    if not websites:
        return jsonify({'error': 'No websites provided'}), 400
    
    # Create new session directory
    session_dir = file_manager.create_scraping_session()
    
    # Scrape and analyze websites
    scraped_data = []
    analyzed_data = []
    
    for website in websites:
        if not web_crawler.is_valid_url(website):
            continue
            
        content = web_crawler.scrape_website(website)
        if not content:
            continue
            
        # Create website directory
        website_dir = file_manager.create_website_directory(session_dir, website)
        
        # Store main content
        content_path = file_manager.store_content(website_dir, content, 'text')
        
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
                print(f"Error downloading image {img_url}: {str(e)}")
    
    # Analyze content
    if scraped_data:
        analyzed_data = content_analyzer.analyze_content(scraped_data)
    
    return jsonify({
        'analyzed_data': analyzed_data,
        'session_dir': session_dir
    })

with app.app_context():
    import models
    db.create_all()
