import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class StarlightHomesPickensBluffNowScraper(BaseScraper):
    URL = "https://www.starlighthomes.com/atlanta/mt-tabor-ridge"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[StarlightHomesPickensBluffNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[StarlightHomesPickensBluffNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[StarlightHomesPickensBluffNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            
            # For now, return empty list since no "now" data was provided
            # This can be updated when "now" data structure is available
            print("[StarlightHomesPickensBluffNowScraper] No 'now' data structure provided, returning empty list")
            print("[StarlightHomesPickensBluffNowScraper] This scraper can be updated when 'now' data is available")
            
            return listings
            
        except Exception as e:
            print(f"[StarlightHomesPickensBluffNowScraper] Error: {e}")
            return []
