import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class UnionMainWildflowerRanchPlanScraper(BaseScraper):
    URL = "https://unionmainhomes.com/communities/wildflower-ranch/"
    
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
        if "2 Story" in text:
            return "2"
        elif "Single Story" in text:
            return "1"
        return "2"  # Default to 2 stories

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[UnionMainWildflowerRanchPlanScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            response = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[UnionMainWildflowerRanchPlanScraper] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[UnionMainWildflowerRanchPlanScraper] Request failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the floorplans section
            floorplans_section = soup.find('div', id='floorplans')
            if not floorplans_section:
                print(f"[UnionMainWildflowerRanchPlanScraper] No floorplans section found")
                return []
            
            # Find all loop items with floorplan class
            loop_items = floorplans_section.find_all('div', class_='e-loop-item')
            floorplan_items = [item for item in loop_items if 'floorplan' in item.get('class', [])]
            print(f"[UnionMainWildflowerRanchPlanScraper] Found {len(floorplan_items)} floorplan items")
            
            listings = []
            
            for idx, item in enumerate(floorplan_items):
                try:
                    # Extract plan name from h2 element
                    plan_name_elem = item.find('h2', class_='elementor-heading-title')
                    plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else None
                    
                    if not plan_name:
                        print(f"[UnionMainWildflowerRanchPlanScraper] Skipping item {idx+1}: No plan name found")
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
                        print(f"[UnionMainWildflowerRanchPlanScraper] Skipping item {idx+1}: Missing property details (beds: {beds}, baths: {baths}, sqft: {sqft})")
                        continue
                    
                    # Extract plan link
                    link_elem = item.find('a', href=re.compile(r'/communities/wildflower-ranch/plans/'))
                    plan_url = link_elem.get('href') if link_elem else None
                    
                    # Extract price from h4 element (if available)
                    h4_elements = item.find_all('h4', class_='elementor-heading-title')
                    price = None
                    for element in h4_elements:
                        text = element.get_text(strip=True)
                        if text.startswith('$'):
                            price = self.parse_price(text)
                            break
                    
                    price_per_sqft = round(price / sqft, 2) if (price and sqft) else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": self.parse_stories(""),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "UnionMain Homes",
                        "community": "Wildflower Ranch",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",  # Plans don't have addresses
                        "design_number": plan_name,  # Use plan name as design number
                        "url": plan_url
                    }
                    
                    print(f"[UnionMainWildflowerRanchPlanScraper] Item {idx+1}: {plan_data['plan_name']} - {sqft:,} sqft, {beds} bed, {baths} bath")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[UnionMainWildflowerRanchPlanScraper] Error processing item {idx+1}: {e}")
                    continue
            
            print(f"[UnionMainWildflowerRanchPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[UnionMainWildflowerRanchPlanScraper] Error: {e}")
            return []
