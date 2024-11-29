from app import db
from datetime import datetime

class ScrapingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    results = db.Column(db.JSON)
    status = db.Column(db.String(50))

class WebsiteData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('scraping_session.id'))
    url = db.Column(db.String(500))
    relevance_score = db.Column(db.Float)
    content_hash = db.Column(db.String(64))
    processed_data = db.Column(db.JSON)
