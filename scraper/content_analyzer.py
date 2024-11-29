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
        """Extract and clean text content with improved handling"""
        try:
            # Remove script and style elements
            content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', content, flags=re.DOTALL)
            
            # Remove HTML comments
            content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
            
            # Remove HTML tags while preserving structure
            text = re.sub(r'<br[^>]*>', '\n', content)
            text = re.sub(r'</p>', '\n\n', text)
            text = re.sub(r'<[^>]+>', '', text)
            
            # Clean up whitespace
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n\s*\n+', '\n\n', text)
            text = text.strip()
            
            # Remove non-printable characters
            text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            return ""

    def _calculate_relevance(self, text):
        # Simple relevance scoring using TF-IDF
        try:
            tfidf_matrix = self.vectorizer.fit_transform([text])
            return float(np.mean(tfidf_matrix.toarray()))
        except:
            return 0.0

    def _process_images(self, content):
        """Process images with enhanced metadata extraction"""
        images = []
        img_pattern = r'<img[^>]+(?:src="([^">]+)"|alt="([^">]+)"|title="([^">]+)"|width="([^">]+)"|height="([^">]+)")'
        
        # Find all image tags and their attributes
        matches = re.finditer(img_pattern, content)
        processed_urls = set()
        
        for match in matches:
            try:
                img_url = next((g for g in match.groups() if g), '')
                if not img_url or img_url in processed_urls:
                    continue
                    
                processed_urls.add(img_url)
                
                metadata = {
                    'source': img_url,
                    'alt_text': match.group(2) or '',
                    'title': match.group(3) or '',
                    'width': match.group(4) or '',
                    'height': match.group(5) or '',
                    'file_type': img_url.split('.')[-1].lower() if '.' in img_url else 'unknown',
                    'processed': True
                }
                
                # Calculate relevance score based on metadata completeness
                metadata_score = sum(1 for v in metadata.values() if v) / len(metadata)
                
                images.append({
                    'url': img_url,
                    'type': 'image',
                    'relevance_score': metadata_score,
                    'metadata': metadata
                })
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
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
