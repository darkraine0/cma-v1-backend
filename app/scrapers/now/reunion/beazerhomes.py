import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class BeazerHomesReunionNowScraper(BaseScraper):
    URL = "https://www.beazer.com/dallas-tx/wildflower-ranch"
    
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
        match = re.search(r'(\d+(?:-\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[BeazerHomesReunionNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[BeazerHomesReunionNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[BeazerHomesReunionNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all inventory property cards - these are in div elements with class 'card_list_item' and data-product-type="inventoryproperty"
            inventory_cards = soup.find_all('div', attrs={'data-product-type': 'inventoryproperty'})
            print(f"[BeazerHomesReunionNowScraper] Found {len(inventory_cards)} inventory property cards")
            
            for idx, card in enumerate(inventory_cards):
                try:
                    print(f"[BeazerHomesReunionNowScraper] Processing inventory card {idx+1}")
                    
                    # Extract plan name from h2 element with class 'font24 bold'
                    plan_name_elem = card.find('h2', class_='font24 bold')
                    if not plan_name_elem:
                        print(f"[BeazerHomesReunionNowScraper] Skipping inventory card {idx+1}: No plan name found")
                        continue
                    
                    plan_name = plan_name_elem.get_text(strip=True)
                    if not plan_name:
                        print(f"[BeazerHomesReunionNowScraper] Skipping inventory card {idx+1}: Empty plan name")
                        continue
                    
                    # Extract address from p element with class 'specaddress-mobile'
                    address_elem = card.find('p', class_='specaddress-mobile')
                    if not address_elem:
                        print(f"[BeazerHomesReunionNowScraper] Skipping inventory card {idx+1}: No address found")
                        continue
                    
                    address_text = address_elem.get_text(strip=True)
                    # Clean up address - remove MLS# and other extra text
                    if 'MLS#' in address_text:
                        address = address_text.split('MLS#')[0].strip()
                        # Extract MLS number
                        mls_match = re.search(r'MLS#\s*(\d+)', address_text)
                        mls_number = mls_match.group(1) if mls_match else ""
                    else:
                        address = address_text
                        mls_number = ""
                    
                    if not address:
                        print(f"[BeazerHomesReunionNowScraper] Skipping inventory card {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[BeazerHomesReunionNowScraper] Skipping inventory card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract current price from p element with class 'font18 no-margin right-align'
                    price_elem = card.find('p', class_='font18 no-margin right-align')
                    if not price_elem:
                        print(f"[BeazerHomesReunionNowScraper] Skipping inventory card {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_elem.get_text())
                    if not current_price:
                        print(f"[BeazerHomesReunionNowScraper] Skipping inventory card {idx+1}: No current price found")
                        continue
                    
                    # Extract square footage from li elements
                    sqft = None
                    list_items = card.find_all('li')
                    for item in list_items:
                        item_text = item.get_text(strip=True)
                        if 'Sq. Ft.' in item_text:
                            sqft = self.parse_sqft(item_text)
                            break
                    
                    if not sqft:
                        print(f"[BeazerHomesReunionNowScraper] Skipping inventory card {idx+1}: No square footage found")
                        continue
                    
                    # Extract beds and baths from li elements
                    beds = ""
                    baths = ""
                    stories = "1"
                    
                    for item in list_items:
                        item_text = item.get_text(strip=True)
                        if 'Bedroom' in item_text:
                            beds = self.parse_beds(item_text)
                        elif 'Bathroom' in item_text:
                            baths = self.parse_baths(item_text)
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Combine plan name with address as requested by user
                    # Format: "Plan Name - Address" (e.g., "Meridian - 1444 Sun Garden Way")
                    combined_plan_name = f"{plan_name} - {address}"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": combined_plan_name,  # Combined plan name as requested
                        "company": "Beazer Homes",
                        "community": "Reunion",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "status": "Now",
                        "address": address,
                        "floor_plan": plan_name,
                        "mls_number": mls_number
                    }
                    
                    print(f"[BeazerHomesReunionNowScraper] Inventory card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[BeazerHomesReunionNowScraper] Error processing inventory card {idx+1}: {e}")
                    continue
            
            print(f"[BeazerHomesReunionNowScraper] Successfully processed {len(listings)} inventory cards")
            return listings
            
        except Exception as e:
            print(f"[BeazerHomesReunionNowScraper] Error: {e}")
            return []
