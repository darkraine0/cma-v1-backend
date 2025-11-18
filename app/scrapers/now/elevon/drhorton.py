import requests
from bs4 import BeautifulSoup
import re
from ...base import BaseScraper
from typing import List, Dict

class DRHortonElevonNowScraper(BaseScraper):
    URL = "https://www.drhorton.com/texas/dallas/lavon/elevon"

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
            cards = soup.find_all('a', class_="CoveoResultLink available-home-card")
            for idx, card in enumerate(cards):
                card_content = card.find('div', class_='card-content')
                if not card_content:
                    continue
                h2 = card_content.find('h2')
                price = self.parse_price(h2.get_text() if h2 else "")
                if price is None:
                    continue
                h3 = card_content.find('h3')
                plan_name = h3.get_text(strip=True) if h3 else ""
                p_tags = card_content.find_all('p')
                sqft = None
                stories = None
                for p in p_tags:
                    text = p.get_text(" ", strip=True)
                    if 'Sq. Ft.' in text:
                        sqft = self.parse_sqft(text)
                    if 'Story' in text:
                        stories = self.parse_stories(text)
                price_per_sqft = round(price / sqft, 2) if price and sqft else None
                plan_data = {
                    "price": price,
                    "sqft": sqft,
                    "stories": stories,
                    "price_per_sqft": price_per_sqft,
                    "plan_name": plan_name,
                    "company": "DR Horton",
                    "community": "Elevon",
                    "type": "now"
                }
                listings.append(plan_data)
            return listings
        except Exception:
            return [] 