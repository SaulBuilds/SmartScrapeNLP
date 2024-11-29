"""
Intelligent Web Scraper Package

This package contains components for web scraping with AI-powered content analysis:
- WebCrawler: Handles the actual web scraping with rate limiting and content extraction
- ContentAnalyzer: Processes and analyzes scraped content using ML/NLP techniques
"""

from .web_crawler import WebCrawler
from .content_analyzer import ContentAnalyzer

__all__ = ['WebCrawler', 'ContentAnalyzer']
