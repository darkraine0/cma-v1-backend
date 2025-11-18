import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class TrophySignatureBrookvilleNowScraper(BaseScraper):
    URL = "https://trophysignaturehomes.com/communities/dallas-ft-worth/forney/devonshire/homes"
    
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
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else None

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Default to 1 story for Trophy Signature Homes."""
        return "1"

    def extract_floor_plan(self, card):
        """Extract floor plan name from the card."""
        floor_plan_elem = card.find('a', href=re.compile(r'/plan/devonshire/'))
        if floor_plan_elem:
            return floor_plan_elem.get_text(strip=True)
        return ""

    def extract_community(self, card):
        """Extract community name from the card."""
        community_elem = card.find('a', href=re.compile(r'/communities/dallas-ft-worth/forney/devonshire'))
        if community_elem:
            return community_elem.get_text(strip=True)
        return "Devonshire"

    def extract_status(self, card):
        """Extract availability status from the card."""
        # Look for the Available Date or Est Completion Date information
        detail_list = card.find('ul', class_='HomeCard_list')
        if detail_list:
            detail_items = detail_list.find_all('li')
            for item in detail_items:
                item_text = item.get_text(strip=True)
                if 'Available Date:' in item_text:
                    # Extract the date part after "Available Date:"
                    date_part = item_text.split('Available Date:')[-1].strip()
                    return date_part
                elif 'Est Completion Date:' in item_text:
                    # Extract the date part after "Est Completion Date:"
                    date_part = item_text.split('Est Completion Date:')[-1].strip()
                    return date_part
        return "Now"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[TrophySignatureBrookvilleNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[TrophySignatureBrookvilleNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[TrophySignatureBrookvilleNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all home cards
            home_cards = soup.find_all('div', class_='card_wrapper')
            print(f"[TrophySignatureBrookvilleNowScraper] Found {len(home_cards)} home cards")
            
            for idx, card in enumerate(home_cards):
                try:
                    print(f"[TrophySignatureBrookvilleNowScraper] Processing card {idx+1}")
                    
                    # Extract home title/address
                    title_elem = card.find('a', class_="HomeCard_title")
                    if not title_elem:
                        print(f"[TrophySignatureBrookvilleNowScraper] Skipping card {idx+1}: Missing title.")
                        continue
                    
                    home_title = title_elem.get_text(strip=True)
                    # Extract just the street address (before the city/state/zip)
                    if ',' in home_title:
                        home_title = home_title.split(',')[0].strip()
                    # Remove any remaining city name that might be attached
                    if 'Forney' in home_title:
                        home_title = home_title.replace('Forney', '').strip()
                    
                    # Check for duplicate addresses
                    if home_title in seen_addresses:
                        print(f"[TrophySignatureBrookvilleNowScraper] Skipping card {idx+1}: Duplicate address '{home_title}'")
                        continue
                    
                    seen_addresses.add(home_title)
                    
                    # Extract floor plan name
                    floor_plan = self.extract_floor_plan(card)
                    
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
                    
                    # Extract availability status
                    status = self.extract_status(card)
                    
                    # Extract community
                    community = self.extract_community(card)
                    
                    if not price or not sqft:
                        print(f"[TrophySignatureBrookvilleNowScraper] Skipping card {idx+1}: Missing price or sqft.")
                        continue
                    
                    # Calculate price per square foot
                    price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                    
                    # Use the address as the plan name
                    final_plan_name = home_title
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": self.parse_stories(""),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": final_plan_name,
                        "company": "Trophy Signature Homes",
                        "community": "Brookville",  # Using Brookville as the community name
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "status": status,
                        "address": home_title,
                        "floor_plan": floor_plan,
                        "sub_community": community  # Devonshire as sub-community
                    }
                    
                    print(f"[TrophySignatureBrookvilleNowScraper] Card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[TrophySignatureBrookvilleNowScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[TrophySignatureBrookvilleNowScraper] Successfully processed {len(listings)} cards")
            return listings
            
        except Exception as e:
            print(f"[TrophySignatureBrookvilleNowScraper] Error: {e}")
            return []
