import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class DRHortonBluestemNowScraper(BaseScraper):
    URL = "https://www.drhorton.com/texas/fort-worth/rhome/bluestem"
    
    def parse_price(self, text):
        """Extract current price from text like '$339,790'."""
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
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_lot_number(self, text):
        """Extract lot number from text."""
        match = re.search(r'Lot\s+(\d+)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DRHortonBluestemNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DRHortonBluestemNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[DRHortonBluestemNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find the available homes container
            available_homes_container = soup.find('div', id='available-homes')
            if not available_homes_container:
                print(f"[DRHortonBluestemNowScraper] No available homes container found")
                return []
            
            # Find all toggle items (available homes)
            toggle_items = available_homes_container.find_all('div', class_='toggle-item')
            print(f"[DRHortonBluestemNowScraper] Found {len(toggle_items)} toggle items")
            
            for idx, item in enumerate(toggle_items):
                try:
                    print(f"[DRHortonBluestemNowScraper] Processing item {idx+1}")
                    
                    # Check if this item is disabled (Under Contract)
                    link_element = item.find('a', class_='CoveoResultLink')
                    if not link_element or 'disabled' in link_element.get('class', []):
                        print(f"[DRHortonBluestemNowScraper] Skipping item {idx+1}: Disabled/Under Contract")
                        continue
                    
                    # Extract address from h3 element
                    address_element = item.find('h3')
                    if not address_element:
                        print(f"[DRHortonBluestemNowScraper] Skipping item {idx+1}: No address found")
                        continue
                    
                    address = address_element.get_text(strip=True)
                    if not address:
                        print(f"[DRHortonBluestemNowScraper] Skipping item {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[DRHortonBluestemNowScraper] Skipping item {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price from h2 element
                    price_element = item.find('h2')
                    if not price_element:
                        print(f"[DRHortonBluestemNowScraper] Skipping item {idx+1}: No price found")
                        continue
                    
                    price_text = price_element.get_text(strip=True)
                    current_price = self.parse_price(price_text)
                    if not current_price:
                        print(f"[DRHortonBluestemNowScraper] Skipping item {idx+1}: Could not parse price from '{price_text}'")
                        continue
                    
                    # Extract stats from p elements
                    stats_elements = item.find_all('p')
                    beds = ""
                    baths = ""
                    garage = ""
                    stories = ""
                    sqft = None
                    lot_number = ""
                    
                    for stats_element in stats_elements:
                        stats_text = stats_element.get_text(strip=True)
                        
                        # Parse the stats text which contains multiple values separated by |
                        # Format: "4 Bed | 2 Bath | 2 Garage" and "1 Story | 1,662 Sq. Ft. | Lot 40"
                        parts = [part.strip() for part in stats_text.split('|')]
                        
                        for part in parts:
                            if 'Bed' in part:
                                beds = self.parse_beds(part)
                            elif 'Bath' in part:
                                baths = self.parse_baths(part)
                            elif 'Garage' in part:
                                garage = self.parse_garage(part)
                            elif 'Story' in part:
                                stories = self.parse_stories(part)
                            elif 'Sq. Ft.' in part:
                                sqft = self.parse_sqft(part)
                            elif 'Lot' in part:
                                lot_number = self.parse_lot_number(part)
                    
                    if not sqft:
                        print(f"[DRHortonBluestemNowScraper] Skipping item {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Determine plan name from address or use a generic name
                    # For now, we'll use the address as the plan name since we don't have explicit plan names
                    plan_name = address
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "DR Horton",
                        "community": "Reunion",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "garage": garage,
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "floor_plan_link": "",
                        "lot_number": lot_number,
                        "status": "Now"
                    }
                    
                    print(f"[DRHortonBluestemNowScraper] Item {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[DRHortonBluestemNowScraper] Error processing item {idx+1}: {e}")
                    continue
            
            print(f"[DRHortonBluestemNowScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[DRHortonBluestemNowScraper] Error: {e}")
            return []

    def get_company_name(self) -> str:
        """Return company name."""
        return "DR Horton"

    def get_community_name(self) -> str:
        """Return community name."""
        return "Reunion"
