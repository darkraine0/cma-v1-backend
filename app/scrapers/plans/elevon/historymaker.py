import requests
from bs4 import BeautifulSoup
import re
from ...base import BaseScraper
from typing import List, Dict

class HistoryMakerElevonPlanScraper(BaseScraper):
    URL = "https://elevontx.com/builder/historymaker-homes/"

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
            print(f"[HistoryMakerElevonPlanScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = requests.get(self.URL, headers=headers, timeout=10)
            print(f"[HistoryMakerElevonPlanScraper] Response status: {resp.status_code}")
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = []
            
            # Use the correct selector that actually works
            cards = soup.find_all('div', class_="ct-div-block collectable listing")
            print(f"[HistoryMakerElevonPlanScraper] Found {len(cards)} home cards.")
            
            for idx, card in enumerate(cards):
                try:
                    # Extract data from data attributes
                    price = card.get('data-price')
                    sqft = card.get('data-sqft')
                    stories = card.get('data-stories')
                    
                    if not price or not sqft:
                        print(f"[HistoryMakerElevonPlanScraper] Skipping card {idx+1}: Missing price or sqft.")
                        continue
                    
                    # Get plan name from headline
                    headline = card.find('h4', class_='ct-headline')
                    plan_name = headline.get_text(strip=True) if headline else ""
                    
                    if not plan_name:
                        print(f"[HistoryMakerElevonPlanScraper] Skipping card {idx+1}: Missing plan name.")
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
                        "company": "HistoryMaker Homes",
                        "community": "Elevon",
                        "type": "plan"
                    }
                    print(f"[HistoryMakerElevonPlanScraper] Card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                except Exception as e:
                    print(f"[HistoryMakerElevonPlanScraper] Error processing card {idx+1}: {e}")
                    continue
            
            return listings
        except Exception as e:
            print(f"[HistoryMakerElevonPlanScraper] Error: {e}")
            return [] 