import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class UnionMainElevonNowScraper(BaseScraper):
    URL = "https://unionmainhomes.com/communities/elevon/"
    
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
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        return "2"

    def get_status(self, container):
        """Extract the status of the home."""
        return "available"

    def get_price_cut(self, container):
        """Extract price cut information if available."""
        return ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[UnionMainElevonNowScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            response = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[UnionMainElevonNowScraper] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[UnionMainElevonNowScraper] Request failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all loop items with property class
            loop_items = soup.find_all('div', class_='e-loop-item')
            property_items = [item for item in loop_items if 'property' in item.get('class', [])]
            print(f"[UnionMainElevonNowScraper] Found {len(property_items)} property items")
            
            listings = []
            
            for idx, item in enumerate(property_items):
                try:
                    # Extract address/name from h2 element
                    address_elem = item.find('h2', class_='elementor-heading-title')
                    address = address_elem.get_text(strip=True) if address_elem else None
                    
                    if not address:
                        print(f"[UnionMainElevonNowScraper] Skipping item {idx+1}: No address found")
                        continue
                    
                    # Extract price from h4 element
                    h4_elements = item.find_all('h4', class_='elementor-heading-title')
                    price = None
                    for element in h4_elements:
                        text = element.get_text(strip=True)
                        if text.startswith('$'):
                            price = self.parse_price(text)
                            break
                    
                    if not price:
                        print(f"[UnionMainElevonNowScraper] Skipping item {idx+1}: No price found")
                        continue
                    
                    # Extract property details (beds, baths, sqft) from grid structure
                    beds = None
                    baths = None
                    sqft = None
                    
                    # Find the grid container that holds beds/baths/sqft
                    grid_container = item.find('div', class_='e-grid')
                    if grid_container:
                        # Find all containers with the bed/bath/sqft structure
                        detail_containers = grid_container.find_all('div', class_='e-flex', recursive=False)
                        
                        for container in detail_containers:
                            h4s = container.find_all('h4', class_='elementor-heading-title')
                            if len(h4s) >= 2:
                                value = h4s[0].get_text(strip=True)
                                label = h4s[1].get_text(strip=True)
                                
                                if label == 'BEDS':
                                    beds = value
                                elif label == 'BATHS':
                                    baths = value
                                elif label == 'SQFT':
                                    sqft = self.parse_sqft(value)
                    
                    if not all([beds, baths, sqft]):
                        print(f"[UnionMainElevonNowScraper] Skipping item {idx+1}: Missing property details (beds: {beds}, baths: {baths}, sqft: {sqft})")
                        continue
                    
                    # Extract property link
                    link_elem = item.find('a', href=re.compile(r'/communities/elevon/new-homes-for-sale/'))
                    property_url = link_elem.get('href') if link_elem else None
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    # Generate plan name from address
                    plan_name_match = re.search(r'(\d+)\s+([A-Za-z\s]+)', address)
                    plan_name = f"{plan_name_match.group(1)} {plan_name_match.group(2).strip()}" if plan_name_match else address
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": self.parse_stories(""),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "UnionMain Homes",
                        "community": "Elevon",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": self.get_price_cut(item),
                        "status": self.get_status(item),
                        "url": property_url
                    }
                    
                    print(f"[UnionMainElevonNowScraper] Item {idx+1}: {plan_data['plan_name']} - ${price:,} - {sqft:,} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[UnionMainElevonNowScraper] Error processing item {idx+1}: {e}")
                    continue
            
            print(f"[UnionMainElevonNowScraper] Successfully processed {len(listings)} properties")
            return listings
            
        except Exception as e:
            print(f"[UnionMainElevonNowScraper] Error: {e}")
            return []
