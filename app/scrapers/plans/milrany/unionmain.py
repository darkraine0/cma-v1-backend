import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class UnionMainMilranyPlanScraper(BaseScraper):
    URL = "https://unionmainhomes.com/floorplans-all/?nh=milrany-ranch"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract starting price from text."""
        match = re.search(r'from \$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "3" and "3.5" formats
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        # Default to 2 stories for these homes based on the data
        return "2"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[UnionMainMilranyPlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[UnionMainMilranyPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[UnionMainMilranyPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Try new structure first (e-loop-item)
            loop_items = soup.find_all('div', class_='e-loop-item')
            floorplan_items = [item for item in loop_items if 'floorplan' in item.get('class', [])]
            
            if floorplan_items:
                print(f"[UnionMainMilranyPlanScraper] Found {len(floorplan_items)} floorplan items (new structure)")
                for idx, item in enumerate(floorplan_items):
                    try:
                        print(f"[UnionMainMilranyPlanScraper] Processing item {idx+1}")
                        
                        # Extract plan name from h2 element
                        plan_name_elem = item.find('h2', class_='elementor-heading-title')
                        plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else None
                        
                        if not plan_name:
                            print(f"[UnionMainMilranyPlanScraper] Skipping item {idx+1}: No plan name found")
                            continue
                        
                        # Check for duplicate plan names
                        if plan_name in seen_plan_names:
                            print(f"[UnionMainMilranyPlanScraper] Skipping item {idx+1}: Duplicate plan name '{plan_name}'")
                            continue
                        
                        seen_plan_names.add(plan_name)
                        
                        # Extract price from h4 element
                        h4_elements = item.find_all('h4', class_='elementor-heading-title')
                        starting_price = None
                        for element in h4_elements:
                            text = element.get_text(strip=True)
                            if text.startswith('$') or 'from' in text.lower():
                                starting_price = self.parse_price(text)
                                if starting_price:
                                    break
                        
                        if not starting_price:
                            print(f"[UnionMainMilranyPlanScraper] Skipping item {idx+1}: No price found")
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
                            print(f"[UnionMainMilranyPlanScraper] Skipping item {idx+1}: No square footage found")
                            continue
                        
                        # Calculate price per sqft
                        price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                        
                        plan_data = {
                            "price": starting_price,
                            "sqft": sqft,
                            "stories": self.parse_stories(""),
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name,
                            "company": "UnionMain Homes",
                            "community": "Milrany",
                            "type": "plan",
                            "beds": beds if beds else "",
                            "baths": baths if baths else "",
                            "address": "",
                            "original_price": None,
                            "price_cut": ""
                        }
                        
                        print(f"[UnionMainMilranyPlanScraper] Item {idx+1}: {plan_data}")
                        listings.append(plan_data)
                        
                    except Exception as e:
                        print(f"[UnionMainMilranyPlanScraper] Error processing item {idx+1}: {e}")
                        continue
            else:
                # Fall back to old structure
                floor_plan_listings = soup.find_all('div', class_='single-fp')
                print(f"[UnionMainMilranyPlanScraper] Found {len(floor_plan_listings)} floor plan listings (old structure)")
                
                for idx, listing in enumerate(floor_plan_listings):
                    try:
                        print(f"[UnionMainMilranyPlanScraper] Processing listing {idx+1}")
                        
                        # Extract plan name from the title link
                        title_link = listing.find('h2', class_='item-title').find('a') if listing.find('h2', class_='item-title') else None
                        if not title_link:
                            print(f"[UnionMainMilranyPlanScraper] Skipping listing {idx+1}: No title link found")
                            continue
                        
                        plan_name = title_link.get_text(strip=True)
                        if not plan_name:
                            print(f"[UnionMainMilranyPlanScraper] Skipping listing {idx+1}: Empty plan name")
                            continue
                        
                        # Check for duplicate plan names
                        if plan_name in seen_plan_names:
                            print(f"[UnionMainMilranyPlanScraper] Skipping listing {idx+1}: Duplicate plan name '{plan_name}'")
                            continue
                        
                        seen_plan_names.add(plan_name)
                        
                        # Extract starting price
                        price_div = listing.find('div', class_='item-price')
                        if not price_div:
                            print(f"[UnionMainMilranyPlanScraper] Skipping listing {idx+1}: No price found")
                            continue
                        
                        starting_price = self.parse_price(price_div.get_text())
                        if not starting_price:
                            print(f"[UnionMainMilranyPlanScraper] Skipping listing {idx+1}: No starting price found")
                            continue
                        
                        # Extract beds, baths, and sqft from amenities
                        amenities = listing.find('ul', class_='item-amenities item-amenities-without-icons')
                        beds = ""
                        baths = ""
                        sqft = None
                        
                        if amenities:
                            amenity_items = amenities.find_all('li')
                            for item in amenity_items:
                                item_class = item.get('class', [])
                                if 'x-beds' in item_class:
                                    # Extract beds from span content
                                    span = item.find('span')
                                    if span:
                                        beds = self.parse_beds(span.get_text())
                                elif 'x-baths' in item_class:
                                    # Extract baths from span content
                                    span = item.find('span')
                                    if span:
                                        baths = self.parse_baths(span.get_text())
                                elif 'h-area' in item_class:
                                    # Extract square footage from span content
                                    span = item.find('span')
                                    if span:
                                        sqft = self.parse_sqft(span.get_text())
                        
                        if not sqft:
                            print(f"[UnionMainMilranyPlanScraper] Skipping listing {idx+1}: No square footage found")
                            continue
                        
                        # Calculate price per sqft
                        price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                        
                        plan_data = {
                            "price": starting_price,
                            "sqft": sqft,
                            "stories": self.parse_stories(""),
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name,
                            "company": "UnionMain Homes",
                            "community": "Milrany",
                            "type": "plan",
                            "beds": beds,
                            "baths": baths,
                            "address": "",
                            "original_price": None,
                            "price_cut": ""
                        }
                        
                        print(f"[UnionMainMilranyPlanScraper] Floor Plan {idx+1}: {plan_data}")
                        listings.append(plan_data)
                        
                    except Exception as e:
                        print(f"[UnionMainMilranyPlanScraper] Error processing listing {idx+1}: {e}")
                        continue
            
            print(f"[UnionMainMilranyPlanScraper] Successfully processed {len(listings)} floor plans")
            return listings
            
        except Exception as e:
            print(f"[UnionMainMilranyPlanScraper] Error: {e}")
            return []

