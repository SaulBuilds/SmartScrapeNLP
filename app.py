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
    websites = chat_response.get('websites', [])
    
    # Scrape websites and store content
    scraped_data = []
    for website in websites:
        content = web_crawler.scrape_website(website)
        if content:
            temp_path = file_manager.store_temp_content(content)
            scraped_data.append({
                'url': website,
                'temp_path': temp_path,
                'content': content
            })
    
    # Analyze and filter content
    analyzed_data = content_analyzer.analyze_content(scraped_data)
    
    # Clean up temporary files
    file_manager.cleanup_temp_files()
    
    return jsonify({
        'response': chat_response['message'],
        'analyzed_data': analyzed_data
    })

with app.app_context():
    import models
    db.create_all()
