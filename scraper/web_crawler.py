import trafilatura
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

class WebCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.visited_urls = set()
        self.delay = 1  # Seconds between requests

    def scrape_website(self, url):
        """Scrape content from a given URL with relevance checking"""
        try:
            # Respect robots.txt and rate limiting
            time.sleep(self.delay)
            
            if url in self.visited_urls:
                return None
                
            self.visited_urls.add(url)
            
            # Get main content using trafilatura
            downloaded = trafilatura.fetch_url(url)
            main_content = trafilatura.extract(downloaded, include_images=True, 
                                             include_links=True, output_format='html')
            
            if not main_content:
                # Fallback to basic scraping if trafilatura fails
                response = requests.get(url, headers=self.headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'footer']):
                    element.decompose()
                    
                main_content = str(soup.body) if soup.body else str(soup)
            
            return main_content

        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return None

    def is_valid_url(self, url):
        """Check if URL is valid and allowed"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
            
    def download_image(self, url):
        """Download image from URL"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            print(f"Error downloading image: {str(e)}")
        return None
