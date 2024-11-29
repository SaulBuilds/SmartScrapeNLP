import trafilatura
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import logging
from urllib.robotparser import RobotFileParser
import re
import os
import hashlib
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

class WebCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; IntelligentScraper/1.0)'
        }
        self.visited_urls = set()
        self.delay = 1  # Seconds between requests
        self.robots_cache = {}

    def _check_robots_txt(self, url):
        """Check if scraping is allowed by robots.txt"""
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            if robots_url not in self.robots_cache:
                rp = RobotFileParser()
                rp.set_url(robots_url)
                rp.read()
                self.robots_cache[robots_url] = rp
            
            return self.robots_cache[robots_url].can_fetch(self.headers['User-Agent'], url)
        except Exception as e:
            logger.warning(f"Failed to check robots.txt for {url}: {str(e)}")
            return True  # Allow by default if robots.txt check fails

    def _clean_content(self, content):
        """Clean and normalize the extracted content"""
        # Remove script and style elements
        content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', content, flags=re.DOTALL)
        # Remove HTML comments
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        # Remove empty lines
        content = re.sub(r'^\s*$\n', '', content, flags=re.MULTILINE)
        return content.strip()

    def extract_text_content(self, html_content):
        """Extract clean text content from HTML using BeautifulSoup"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Get all text elements
            paragraphs = []
            for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = element.get_text(strip=True)
                if text:  # Only add non-empty paragraphs
                    if element.name.startswith('h'):
                        paragraphs.append(f"\n# {text}\n")
                    else:
                        paragraphs.append(text)
            
            return '\n\n'.join(paragraphs)
        except Exception as e:
            logger.error(f"Error extracting text content: {str(e)}", exc_info=True)
            return None

    def extract_images(self, html_content, base_url):
        """Extract and download images from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            images = []
            
            for img in soup.find_all('img'):
                src = img.get('src')
                if not src:
                    continue
                
                # Get absolute URL
                img_url = urljoin(base_url, src)
                
                try:
                    # Download image
                    response = requests.get(img_url, headers=self.headers, timeout=10)
                    response.raise_for_status()
                    
                    # Verify it's an image
                    img_content = BytesIO(response.content)
                    img_obj = Image.open(img_content)
                    
                    # Get image format and generate filename
                    img_format = img_obj.format.lower() if img_obj.format else 'jpg'
                    img_hash = hashlib.md5(response.content).hexdigest()[:10]
                    filename = f"image_{img_hash}.{img_format}"
                    
                    # Add to images list
                    images.append({
                        'url': img_url,
                        'content': response.content,
                        'filename': filename,
                        'format': img_format,
                        'alt': img.get('alt', ''),
                        'size': len(response.content)
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to process image {img_url}: {str(e)}")
                    continue
            
            return images
            
        except Exception as e:
            logger.error(f"Error extracting images: {str(e)}", exc_info=True)
            return []

    def _normalize_url(self, base_url, relative_url):
        """Normalize relative URLs to absolute URLs"""
        try:
            return urljoin(base_url, relative_url)
        except Exception as e:
            logger.error(f"Error normalizing URL {relative_url} with base {base_url}: {str(e)}")
            return None

    def _extract_links(self, soup, base_url):
        """Extract and normalize all links from the page"""
        links = set()
        try:
            for anchor in soup.find_all('a', href=True):
                href = anchor['href']
                if href.startswith('#') or href.startswith('javascript:'):
                    continue
                    
                absolute_url = self._normalize_url(base_url, href)
                if absolute_url and self.is_valid_url(absolute_url):
                    links.add(absolute_url)
                    
            logger.info(f"Found {len(links)} valid links on {base_url}")
            return links
        except Exception as e:
            logger.error(f"Error extracting links from {base_url}: {str(e)}")
            return set()

    def scrape_website(self, url, progress_callback=None):
        """Scrape content from a given URL with enhanced content cleaning and error handling"""
        try:
            if not self.is_valid_url(url):
                raise ValueError(f"Invalid URL format: {url}")

            if url in self.visited_urls:
                logger.info(f"Skipping already visited URL: {url}")
                return None

            if not self._check_robots_txt(url):
                logger.warning(f"Robots.txt disallows scraping: {url}")
                return None

            # Respect rate limiting
            time.sleep(self.delay)
            self.visited_urls.add(url)
            
            logger.info(f"Starting to scrape: {url}")
            if progress_callback:
                progress_callback(f"Starting to scrape {url}", 0)
            
            # Try trafilatura first for main content extraction
            logger.info(f"Attempting to scrape content from: {url}")
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                main_content = trafilatura.extract(
                    downloaded,
                    include_images=True,
                    include_links=True,
                    output_format='html',
                    with_metadata=True
                )
                
                if main_content:
                    html_content = self._clean_content(main_content)
                    text_content = self.extract_text_content(html_content)
                    images = self.extract_images(html_content, url)
                    
                    logger.info(f"Successfully extracted content from {url}")
                    return {
                        'html': html_content,
                        'text': text_content,
                        'images': images,
                        'url': url
                    }

            # Fallback to BeautifulSoup if trafilatura fails
            logger.info(f"Trafilatura extraction failed, falling back to BeautifulSoup for {url}")
            logger.info(f"Downloading content from: {url}")
            if progress_callback:
                progress_callback(f"Downloading content from {url}", 20)
                
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Parsing content from: {url}")
            if progress_callback:
                progress_callback(f"Parsing content from {url}", 40)
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract links before cleaning
            links = self._extract_links(soup, url)
            logger.info(f"Found {len(links)} links on {url}")
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'header']):
                element.decompose()
                
            if progress_callback:
                progress_callback(f"Processing content from {url}", 60)
            
            # Extract main content
            main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': ['content', 'main', 'article']})
            
            if not main_content:
                main_content = soup.body if soup.body else soup
            
            html_content = str(main_content)
            html_content = self._clean_content(html_content)
            
            if not html_content.strip():
                logger.warning(f"No content extracted from {url}")
                return None
            
            text_content = self.extract_text_content(html_content)
            images = self.extract_images(html_content, url)
            
            logger.info(f"Successfully extracted content using fallback method from {url}")
            return {
                'html': html_content,
                'text': text_content,
                'images': images,
                'url': url
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}", exc_info=True)
            return None

    def is_valid_url(self, url):
        """Check if URL is valid and has proper scheme"""
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except Exception as e:
            logger.error(f"URL validation failed: {str(e)}")
            return False
