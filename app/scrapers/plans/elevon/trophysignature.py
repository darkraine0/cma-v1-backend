import requests
from bs4 import BeautifulSoup
import re
from ...base import BaseScraper
from typing import List, Dict

class TrophySignatureElevonPlanScraper(BaseScraper):
    URL = "https://elevontx.com/builder/trophy-signature-homes/"

    def parse_sqft(self, text):
        match = re.search(r'([\d,]+)\s*sq\.?\s*ft', text, re.IGNORECASE)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_stories(self, text):
        match = re.search(r'(\d+(\.\d+)?)\s*story', text, re.IGNORECASE)
        return float(match.group(1)) if match else None

    def fetch_plans(self) -> List[Dict]:
        try:
            resp = requests.get(self.URL, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = []
            
            # Use the correct selector that actually works
            cards = soup.find_all('div', class_="ct-div-block collectable listing")
            
            for card in cards:
                try:
                    # Extract data from data attributes
                    price = card.get('data-price')
                    sqft = card.get('data-sqft')
                    stories = card.get('data-stories')
                    
                    if not price or not sqft:
                        continue
                    
                    # Get plan name from headline
                    headline = card.find('h4', class_='ct-headline')
                    plan_name = headline.get_text(strip=True) if headline else ""
                    
                    if not plan_name:
                        continue
                    
                    # Convert to integers
                    price_int = int(price)
                    sqft_int = int(sqft)
                    price_per_sqft = round(price_int / sqft_int, 2) if sqft_int > 0 else None
                    
                    plan_data = {
                        "price": price_int,
                        "sqft": sqft_int,
                        "stories": str(stories),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Trophy Signature Homes",
                        "community": "Elevon",
                        "type": "plan"
                    }
                    listings.append(plan_data)
                except Exception:
                    continue
            
            return listings
        except Exception:
            return [] 