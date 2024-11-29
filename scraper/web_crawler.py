import trafilatura
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import logging
from urllib.robotparser import RobotFileParser
import re

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

    def scrape_website(self, url):
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
                    cleaned_content = self._clean_content(main_content)
                    logger.info(f"Successfully extracted content from {url}")
                    return cleaned_content

            # Fallback to BeautifulSoup if trafilatura fails
            logger.info(f"Trafilatura extraction failed, falling back to BeautifulSoup for {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'header']):
                element.decompose()
            
            # Extract main content
            main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': ['content', 'main', 'article']})
            
            if not main_content:
                main_content = soup.body if soup.body else soup
            
            content = str(main_content)
            cleaned_content = self._clean_content(content)
            
            if not cleaned_content.strip():
                logger.warning(f"No content extracted from {url}")
                return None
                
            logger.info(f"Successfully extracted content using fallback method from {url}")
            return cleaned_content

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
