import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class UnionMainWaldenPondWestPlanScraper(BaseScraper):
    URL = "https://unionmainhomes.com/communities/walden-pond/"
    
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
        return "2"  # Default to 2 stories for single family homes

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[UnionMainWaldenPondWestPlanScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            response = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[UnionMainWaldenPondWestPlanScraper] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[UnionMainWaldenPondWestPlanScraper] Request failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all loop items with floorplan class (search entire soup like Cambridge scraper)
            loop_items = soup.find_all('div', class_='e-loop-item')
            floorplan_items = [item for item in loop_items if 'floorplan' in item.get('class', [])]
            print(f"[UnionMainWaldenPondWestPlanScraper] Found {len(floorplan_items)} floorplan items")
            
            plans = []
            
            for idx, item in enumerate(floorplan_items):
                try:
                    # Extract plan name from h2 element
                    plan_name_elem = item.find('h2', class_='elementor-heading-title')
                    plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else None
                    
                    if not plan_name:
                        print(f"[UnionMainWaldenPondWestPlanScraper] Skipping item {idx+1}: No plan name found")
                        continue
                    
                    # Extract price from h4 elements
                    # Look for price container with structure: old price -> arrow -> new price
                    # The new price is the last price in the sequence
                    h4_elements = item.find_all('h4', class_='elementor-heading-title')
                    price = None
                    original_price = None
                    
                    # Find all price values in h4 elements
                    price_values = []
                    for element in h4_elements:
                        text = element.get_text(strip=True)
                        parsed_price = self.parse_price(text)
                        if parsed_price:
                            price_values.append(parsed_price)
                    
                    # If there are multiple prices, the last one is the new price
                    # and the first one is the original price
                    if len(price_values) > 1:
                        original_price = price_values[0]
                        price = price_values[-1]  # Last price is the new price
                    elif len(price_values) == 1:
                        price = price_values[0]
                    
                    if not price:
                        print(f"[UnionMainWaldenPondWestPlanScraper] Skipping item {idx+1}: No price found")
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
                    
                    if not sqft:
                        print(f"[UnionMainWaldenPondWestPlanScraper] Skipping item {idx+1}: Missing square footage (sqft: {sqft})")
                        continue
                    
                    # Extract plan link - the link wraps the entire card
                    link_elem = item.find('a', href=True)
                    plan_url = link_elem.get('href') if link_elem else None
                    if plan_url:
                        if not plan_url.startswith('http'):
                            plan_url = f"https://unionmainhomes.com{plan_url}"
                    else:
                        # Fallback: try to construct URL from plan name
                        plan_slug = plan_name.lower().replace(' ', '-')
                        plan_url = f"https://unionmainhomes.com/communities/walden-pond/plans/{plan_slug}/"
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": self.parse_stories(""),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "UnionMain Homes",
                        "community": "Walden Pond West",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": None,  # Plans don't have specific addresses
                        "original_price": original_price,
                        "price_cut": "",
                        "status": "available",
                        "url": plan_url
                    }
                    
                    print(f"[UnionMainWaldenPondWestPlanScraper] Item {idx+1}: {plan_name} - ${price:,} - {sqft:,} sqft - {beds} beds - {baths} baths")
                    plans.append(plan_data)
                    
                except Exception as e:
                    print(f"[UnionMainWaldenPondWestPlanScraper] Error processing item {idx+1}: {e}")
                    continue
            
            print(f"[UnionMainWaldenPondWestPlanScraper] Successfully processed {len(plans)} plans")
            return plans
            
        except Exception as e:
            print(f"[UnionMainWaldenPondWestPlanScraper] Error: {e}")
            return []
