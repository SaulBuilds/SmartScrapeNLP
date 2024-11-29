from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from PIL import Image
import io
import re

class ContentAnalyzer:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.relevance_threshold = 0.3

    def analyze_content(self, scraped_data):
        analyzed_results = []
        
        for item in scraped_data:
            # Extract text content
            text_content = self._extract_text(item['content'])
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance(text_content)
            
            if relevance_score >= self.relevance_threshold:
                # Process images if present
                images = self._process_images(item['content'])
                
                # Create structured output
                analyzed_results.append({
                    'url': item['url'],
                    'relevance_score': relevance_score,
                    'processed_text': text_content,
                    'images': images,
                    'metadata': self._extract_metadata(item['content'])
                })
        
        return analyzed_results

    def _extract_text(self, content):
        # Remove HTML tags and clean text
        text = re.sub(r'<[^>]+>', '', content)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _calculate_relevance(self, text):
        # Simple relevance scoring using TF-IDF
        try:
            tfidf_matrix = self.vectorizer.fit_transform([text])
            return float(np.mean(tfidf_matrix.toarray()))
        except:
            return 0.0

    def _process_images(self, content):
        images = []
        # Extract image data and process
        img_tags = re.findall(r'<img[^>]+src="([^">]+)"', content)
        
        for img_url in img_tags:
            try:
                images.append({
                    'url': img_url,
                    'type': 'image',
                    'metadata': {
                        'source': img_url,
                        'processed': True
                    }
                })
            except:
                continue
                
        return images

    def _extract_metadata(self, content):
        metadata = {
            'title': self._extract_tag_content(content, 'title'),
            'description': self._extract_meta_content(content, 'description'),
            'keywords': self._extract_meta_content(content, 'keywords'),
        }
        return metadata

    def _extract_tag_content(self, content, tag):
        match = re.search(f'<{tag}[^>]*>(.*?)</{tag}>', content, re.I|re.S)
        return match.group(1) if match else ''

    def _extract_meta_content(self, content, name):
        match = re.search(f'<meta[^>]+name="{name}"[^>]+content="([^"]*)"', content, re.I)
        return match.group(1) if match else ''
