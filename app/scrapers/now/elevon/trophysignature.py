import requests
from bs4 import BeautifulSoup
import re
from ...base import BaseScraper
from typing import List, Dict

class TrophySignatureElevonNowScraper(BaseScraper):
    URL = "https://trophysignaturehomes.com/communities/dallas-ft-worth/lavon/elevon"

    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else None

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else None

    def parse_stories(self, text):
        """Default to 1 story for Trophy Signature Homes."""
        return "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[TrophySignatureElevonNowScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = requests.get(self.URL, headers=headers, timeout=10)
            print(f"[TrophySignatureElevonNowScraper] Response status: {resp.status_code}")
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = []
            
            # Find all home cards
            cards = soup.find_all('div', class_="card_wrapper")
            print(f"[TrophySignatureElevonNowScraper] Found {len(cards)} home cards.")
            
            if len(cards) == 0:
                print("[TrophySignatureElevonNowScraper] No home cards found.")
                return []
            
            for idx, card in enumerate(cards):
                try:
                    # Extract home title/address
                    title_elem = card.find('a', class_="HomeCard_title")
                    if not title_elem:
                        print(f"[TrophySignatureElevonNowScraper] Skipping card {idx+1}: Missing title.")
                        continue
                    
                    home_title = title_elem.get_text(strip=True)
                    # Extract just the street address (before the city/state/zip)
                    if ',' in home_title:
                        home_title = home_title.split(',')[0].strip()
                    # Remove any remaining city name that might be attached
                    if 'Lavon' in home_title:
                        home_title = home_title.replace('Lavon', '').strip()
                    
                    # Extract floor plan name from the floor plan link
                    floor_plan_elem = card.find('a', href=re.compile(r'/plan/elevon/'))
                    plan_name = ""
                    if floor_plan_elem:
                        plan_name = floor_plan_elem.get_text(strip=True)
                    
                    # Extract price from Current_price span
                    price_elem = card.find('div', class_="Current_price")
                    price = None
                    if price_elem:
                        price_span = price_elem.find('span')
                        if price_span:
                            price_text = price_span.get_text(strip=True)
                            price = self.parse_price(price_text)
                    
                    # Extract square footage from the list items
                    sqft = None
                    list_items = card.find_all('li')
                    for item in list_items:
                        text = item.get_text(strip=True)
                        if 'SQ FT' in text:
                            sqft_text = item.find('b')
                            if sqft_text:
                                sqft = self.parse_sqft(sqft_text.get_text(strip=True))
                                break
                    
                    # Extract bedrooms and bathrooms
                    beds = None
                    baths = None
                    for item in list_items:
                        text = item.get_text(strip=True)
                        if 'Beds' in text:
                            beds_elem = item.find('b')
                            if beds_elem:
                                beds = self.parse_beds(beds_elem.get_text(strip=True))
                        elif 'Baths' in text:
                            baths_elem = item.find('b')
                            if baths_elem:
                                baths = self.parse_baths(baths_elem.get_text(strip=True))
                    
                    # Extract completion date
                    completion_date = ""
                    for item in list_items:
                        text = item.get_text(strip=True)
                        if 'Est Completion Date:' in text:
                            # Get the text after the colon
                            completion_text = text.split('Est Completion Date:')[-1].strip()
                            completion_date = completion_text
                            break
                    
                    if not price or not sqft:
                        print(f"[TrophySignatureElevonNowScraper] Skipping card {idx+1}: Missing price or sqft.")
                        continue
                    
                    # Calculate price per square foot
                    price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                    
                    # Use the address as the project name for Trophy Signature Homes
                    final_plan_name = home_title
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": self.parse_stories(""),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": final_plan_name,
                        "company": "Trophy Signature Homes",
                        "community": "Elevon",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "completion_date": completion_date,
                        "address": home_title
                    }
                    print(f"[TrophySignatureElevonNowScraper] Card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                except Exception as e:
                    print(f"[TrophySignatureElevonNowScraper] Error processing card {idx+1}: {e}")
                    continue
            
            return listings
        except Exception as e:
            print(f"[TrophySignatureElevonNowScraper] Error: {e}")
            return [] 