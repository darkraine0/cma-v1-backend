import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class BeazerHomesBrookvilleNowScraper(BaseScraper):
    URL = "https://www.beazer.com/dallas-tx/brookville-estates"
    
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
        match = re.search(r'(\d+(?:-\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[BeazerHomesBrookvilleNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[BeazerHomesBrookvilleNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[BeazerHomesBrookvilleNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all address elements - these are the actual home listings
            address_elements = soup.find_all('p', class_='specaddress-mobile')
            print(f"[BeazerHomesBrookvilleNowScraper] Found {len(address_elements)} address elements")
            
            for idx, addr_elem in enumerate(address_elements):
                try:
                    print(f"[BeazerHomesBrookvilleNowScraper] Processing address {idx+1}")
                    
                    # Extract address
                    address = addr_elem.get_text(strip=True)
                    # Clean up address - remove MLS# and other extra text
                    if 'MLS#' in address:
                        address = address.split('MLS#')[0].strip()
                    
                    if not address:
                        print(f"[BeazerHomesBrookvilleNowScraper] Skipping address {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[BeazerHomesBrookvilleNowScraper] Skipping address {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Find the parent container that contains this address and other home data
                    home_container = addr_elem
                    for _ in range(10):  # Go up 10 levels max
                        home_container = home_container.parent
                        if not home_container:
                            break
                        
                        # Check if this container has multiple pieces of home information
                        container_text = home_container.get_text()
                        has_price = bool(re.search(r'\$[\d,]+', container_text))
                        has_sqft = bool(re.search(r'[\d,]+\s*Sq\.?\s*Ft\.', container_text, re.IGNORECASE))
                        has_bed_bath = bool(re.search(r'\d+\s*(?:Bedroom|Bathroom|Bedrooms|Bathrooms)', container_text, re.IGNORECASE))
                        
                        # If container has at least 2 pieces of home info, it's likely a home container
                        if sum([has_price, has_sqft, has_bed_bath]) >= 2:
                            break
                    
                    # Extract plan name from the home container
                    plan_name = ""
                    plan_elem = home_container.find('a', class_='OneLinkNoTx')
                    if plan_elem:
                        plan_name = plan_elem.get_text(strip=True)
                    
                    # If no plan name found, try to extract from the container text
                    if not plan_name:
                        plan_match = re.search(r'\b(Brooks|Smith|Johnson|Williams|Brown|Jones|Garcia|Miller)\b', container_text)
                        if plan_match:
                            plan_name = plan_match.group(1)
                    
                    if not plan_name:
                        print(f"[BeazerHomesBrookvilleNowScraper] Skipping address {idx+1}: No plan name found")
                        continue
                    
                    # Combine plan name with address as requested by user
                    # Format: "Plan Name - Address" (e.g., "Brooks - 218 Freedom Trail")
                    combined_plan_name = f"{plan_name} - {address}"
                    
                    # Extract price from the home container
                    current_price = None
                    price_elem = home_container.find('p', class_=['font18', 'no-margin', 'right-align'])
                    if price_elem:
                        current_price = self.parse_price(price_elem.get_text())
                    
                    if not current_price:
                        print(f"[BeazerHomesBrookvilleNowScraper] Skipping address {idx+1}: No current price found")
                        continue
                    
                    # Extract square footage from the home container
                    sqft = None
                    list_items = home_container.find_all('li')
                    for item in list_items:
                        item_text = item.get_text(strip=True)
                        if 'Sq. Ft.' in item_text:
                            sqft = self.parse_sqft(item_text)
                            break
                    
                    if not sqft:
                        print(f"[BeazerHomesBrookvilleNowScraper] Skipping address {idx+1}: No square footage found")
                        continue
                    
                    # Extract beds and baths from the home container
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
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": combined_plan_name,  # Combined plan name as requested
                        "company": "Beazer Homes",
                        "community": "Brookville",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "status": "Now",
                        "address": address,
                        "floor_plan": plan_name
                    }
                    
                    print(f"[BeazerHomesBrookvilleNowScraper] Address {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[BeazerHomesBrookvilleNowScraper] Error processing address {idx+1}: {e}")
                    continue
            
            print(f"[BeazerHomesBrookvilleNowScraper] Successfully processed {len(listings)} addresses")
            return listings
            
        except Exception as e:
            print(f"[BeazerHomesBrookvilleNowScraper] Error: {e}")
            return []
