import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class DavidWeekleyHomesWildflowerRanchNowScraper(BaseScraper):
    URL = "https://www.davidweekleyhomes.com/new-homes/tx/dallas-ft-worth/justin/treeline"
    
    def parse_price(self, text):
        """Extract price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find the quick-move-ins section
            quick_move_ins = soup.find('div', id='quick-move-ins')
            if not quick_move_ins:
                print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Quick move-ins section not found")
                return []
            
            # Find all plan cards in the quick move-ins section
            plan_cards = quick_move_ins.find_all('div', class_='plan-card')
            print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Found {len(plan_cards)} plan cards")
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Processing card {idx+1}")
                    
                    # Extract plan title
                    plan_title = card.find('h2', class_='plan-title')
                    if not plan_title:
                        print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Skipping card {idx+1}: No plan title found")
                        continue
                    
                    plan_name = plan_title.get_text(strip=True)
                    if not plan_name:
                        print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Skipping card {idx+1}: Empty plan name")
                        continue
                    
                    # Extract address
                    plan_address = card.find('span', class_='plan-address')
                    if not plan_address:
                        print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Skipping card {idx+1}: No address found")
                        continue
                    
                    address = plan_address.get_text(strip=True)
                    if not address:
                        print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Skipping card {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price
                    price_element = card.find('h4', class_='card-black')
                    if not price_element:
                        print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_element.get_text())
                    if not current_price:
                        print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract square footage
                    sqft_elements = card.find_all('h4', class_='card-black')
                    sqft = None
                    for element in sqft_elements:
                        text = element.get_text(strip=True)
                        if 'Sq. Ft:' in text:
                            sqft = self.parse_sqft(text)
                            break
                    
                    if not sqft:
                        print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Extract beds, baths, stories, and garage from second-level properties
                    second_level = card.find('div', class_='second-level-properties')
                    beds = ""
                    baths = ""
                    stories = "1"
                    garage = ""
                    
                    if second_level:
                        features = second_level.find_all('div', class_='feature')
                        for feature in features:
                            title = feature.find('div', class_='title')
                            value = feature.find('div', class_='value')
                            
                            if title and value:
                                title_text = title.get_text(strip=True).lower()
                                value_text = value.get_text(strip=True)
                                
                                if 'bedroom' in title_text:
                                    beds = self.parse_beds(value_text)
                                elif 'full bath' in title_text:
                                    baths = self.parse_baths(value_text)
                                elif 'story' in title_text:
                                    stories = self.parse_stories(value_text)
                                elif 'garage' in title_text:
                                    garage = self.parse_garage(value_text)
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "David Weekley Homes",
                        "community": "Wildflower Ranch",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": ""
                    }
                    
                    print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[DavidWeekleyHomesWildflowerRanchNowScraper] Error: {e}")
            return []

    def get_company_name(self) -> str:
        """Return company name."""
        return "David Weekley Homes"

    def get_community_name(self) -> str:
        """Return community name."""
        return "Wildflower Ranch"
