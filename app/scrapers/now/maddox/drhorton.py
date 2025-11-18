import requests
from bs4 import BeautifulSoup
import re
from ...base import BaseScraper
from ...price_utils import parse_price_with_thousands
from typing import List, Dict

class DRHortonMaddoxNowScraper(BaseScraper):
    URL = "https://www.drhorton.com/georgia/atlanta/hoschton/twin-lakes"

    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)\s*sq\.?\s*ft\.?', text, re.IGNORECASE)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        # Use the utility function to handle thousands notation
        return parse_price_with_thousands(text)

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)\s*bed', text, re.IGNORECASE)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)\s*bath', text, re.IGNORECASE)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+(?:\.\d+)?)\s*story', text, re.IGNORECASE)
        return str(match.group(1)) if match else ""

    def get_status(self, card):
        """Extract the status of the home."""
        h2 = card.find('h2')
        if h2:
            h2_text = h2.get_text(strip=True)
            if 'Under Contract' in h2_text:
                return "under contract"
            elif '$' in h2_text:
                return "available"
        return "unknown"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DRHortonMaddoxNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DRHortonMaddoxNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[DRHortonMaddoxNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all home listings in the section
            home_cards = soup.find_all('a', class_='CoveoResultLink available-home-card')
            print(f"[DRHortonMaddoxNowScraper] Found {len(home_cards)} home cards")
            
            for idx, card in enumerate(home_cards):
                try:
                    print(f"[DRHortonMaddoxNowScraper] Processing card {idx+1}")
                    
                    # Skip disabled cards (under contract)
                    if 'disabled' in card.get('class', []):
                        print(f"[DRHortonMaddoxNowScraper] Skipping card {idx+1}: Disabled (under contract)")
                        continue
                    
                    card_content = card.find('div', class_='card-content')
                    if not card_content:
                        print(f"[DRHortonMaddoxNowScraper] Skipping card {idx+1}: No card content found")
                        continue
                    
                    # Extract address from h3
                    h3 = card_content.find('h3')
                    if not h3:
                        print(f"[DRHortonMaddoxNowScraper] Skipping card {idx+1}: No address found")
                        continue
                    
                    address = h3.get_text(strip=True)
                    if not address:
                        print(f"[DRHortonMaddoxNowScraper] Skipping card {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[DRHortonMaddoxNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price from h2
                    h2 = card_content.find('h2')
                    if not h2:
                        print(f"[DRHortonMaddoxNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(h2.get_text())
                    if not current_price:
                        print(f"[DRHortonMaddoxNowScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract beds, baths, stories, and sqft from p tags
                    p_tags = card_content.find_all('p')
                    beds = ""
                    baths = ""
                    stories = ""
                    sqft = None
                    
                    for p in p_tags:
                        text = p.get_text(" ", strip=True)
                        if 'Bed' in text and not beds:
                            beds = self.parse_beds(text)
                        if 'Bath' in text and not baths:
                            baths = self.parse_baths(text)
                        if 'Story' in text and not stories:
                            stories = self.parse_stories(text)
                        if 'Sq. Ft.' in text and not sqft:
                            sqft = self.parse_sqft(text)
                    
                    if not sqft:
                        print(f"[DRHortonMaddoxNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Get status
                    status = self.get_status(card)
                    
                    # Create plan name from address (extract street number and name)
                    plan_name_match = re.search(r'(\d+)\s+([A-Za-z]+)', address)
                    plan_name = f"{plan_name_match.group(1)} {plan_name_match.group(2)}" if plan_name_match else address
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "DR Horton",
                        "community": "Maddox",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": ""
                    }
                    
                    # Add additional metadata
                    if status:
                        plan_data["status"] = status
                    
                    print(f"[DRHortonMaddoxNowScraper] Card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[DRHortonMaddoxNowScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[DRHortonMaddoxNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[DRHortonMaddoxNowScraper] Error: {e}")
            return []
