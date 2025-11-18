import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class UnionMainEdgewaterPlanScraper(BaseScraper):
    URL = "https://unionmainhomes.com/floorplans-all/?nh=edgewater"
    
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
        # Handle both "3" and "3.5" formats
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        # Default to 2 stories for these homes based on the data
        return "2"

    def get_status(self, container):
        """Extract the status of the home."""
        status_label = container.find('span', class_='label-status')
        if status_label:
            status_text = status_label.get_text(strip=True).lower()
            if 'move-in ready' in status_text:
                return "move-in ready"
            elif 'under construction' in status_text:
                return "under construction"
            elif 'coming soon' in status_text:
                return "coming soon"
        return "unknown"

    def get_price_cut(self, container):
        """Extract price cut information if available."""
        price_diff = container.find('span', class_='price_diff')
        if price_diff:
            price_cut_text = price_diff.get_text(strip=True)
            # Extract the amount from "Price cut: $47,375"
            match = re.search(r'Price cut: \$([\d,]+)', price_cut_text)
            if match:
                return match.group(1)
        return ""

    def get_move_in_date(self, container):
        """Extract move-in date if available."""
        move_in_li = container.find('li', class_=re.compile(r'h-move-in'))
        if move_in_li:
            move_in_text = move_in_li.get_text(strip=True)
            # Extract month from "Nov move-in" or "Oct move-in"
            match = re.search(r'(\w+)\s+move-in', move_in_text)
            if match:
                return match.group(1)
        return ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[UnionMainEdgewaterPlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[UnionMainEdgewaterPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[UnionMainEdgewaterPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Try new structure first (e-loop-item)
            loop_items = soup.find_all('div', class_='e-loop-item')
            floorplan_items = [item for item in loop_items if 'floorplan' in item.get('class', [])]
            
            if floorplan_items:
                print(f"[UnionMainEdgewaterPlanScraper] Found {len(floorplan_items)} floorplan items (new structure)")
                for idx, item in enumerate(floorplan_items):
                    try:
                        print(f"[UnionMainEdgewaterPlanScraper] Processing item {idx+1}")
                        
                        # Extract plan name from h2 element
                        plan_name_elem = item.find('h2', class_='elementor-heading-title')
                        plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else None
                        
                        if not plan_name:
                            print(f"[UnionMainEdgewaterPlanScraper] Skipping item {idx+1}: No plan name found")
                            continue
                        
                        # Check for duplicate plan names
                        if plan_name in seen_plan_names:
                            print(f"[UnionMainEdgewaterPlanScraper] Skipping item {idx+1}: Duplicate plan name '{plan_name}'")
                            continue
                        
                        seen_plan_names.add(plan_name)
                        
                        # Extract price from h4 element
                        h4_elements = item.find_all('h4', class_='elementor-heading-title')
                        current_price = None
                        for element in h4_elements:
                            text = element.get_text(strip=True)
                            if text.startswith('$'):
                                current_price = self.parse_price(text)
                                if current_price:
                                    break
                        
                        if not current_price:
                            print(f"[UnionMainEdgewaterPlanScraper] Skipping item {idx+1}: No price found")
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
                            print(f"[UnionMainEdgewaterPlanScraper] Skipping item {idx+1}: No square footage found")
                            continue
                        
                        # Calculate price per sqft
                        price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                        
                        # Extract image URL if available
                        image_url = ""
                        listing_thumb = item.find('div', class_='listing-thumb')
                        if listing_thumb:
                            style_attr = listing_thumb.get('style', '')
                            url_match = re.search(r'url\(([^)]+)\)', style_attr)
                            if url_match:
                                image_url = url_match.group(1)
                        
                        plan_data = {
                            "price": current_price,
                            "sqft": sqft,
                            "stories": self.parse_stories(""),
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name,
                            "company": "UnionMain Homes",
                            "community": "Edgewater",
                            "type": "plan",
                            "beds": beds if beds else "",
                            "baths": baths if baths else "",
                            "address": plan_name,
                            "original_price": None,
                            "price_cut": "",
                            "image_url": image_url
                        }
                        
                        print(f"[UnionMainEdgewaterPlanScraper] Item {idx+1}: {plan_data}")
                        listings.append(plan_data)
                        
                    except Exception as e:
                        print(f"[UnionMainEdgewaterPlanScraper] Error processing item {idx+1}: {e}")
                        continue
            else:
                # Fall back to old structure
                plan_listings = soup.find_all('div', class_=lambda x: x and 'single-fp slide' in x)
                print(f"[UnionMainEdgewaterPlanScraper] Found {len(plan_listings)} plan listings (old structure)")
                
                for idx, listing in enumerate(plan_listings):
                    try:
                        print(f"[UnionMainEdgewaterPlanScraper] Processing plan {idx+1}")
                        
                        # Extract plan name from the title link
                        title_link = listing.find('h2', class_='item-title').find('a') if listing.find('h2', class_='item-title') else None
                        if not title_link:
                            print(f"[UnionMainEdgewaterPlanScraper] Skipping plan {idx+1}: No title link found")
                            continue
                        
                        plan_name = title_link.get_text(strip=True)
                        if not plan_name:
                            print(f"[UnionMainEdgewaterPlanScraper] Skipping plan {idx+1}: Empty plan name")
                            continue
                        
                        # Check for duplicate plan names
                        if plan_name in seen_plan_names:
                            print(f"[UnionMainEdgewaterPlanScraper] Skipping plan {idx+1}: Duplicate plan name '{plan_name}'")
                            continue
                        
                        seen_plan_names.add(plan_name)
                        
                        # Extract price
                        price_div = listing.find('div', class_='item-price')
                        if not price_div:
                            print(f"[UnionMainEdgewaterPlanScraper] Skipping plan {idx+1}: No price found")
                            continue
                        
                        current_price = self.parse_price(price_div.get_text())
                        if not current_price:
                            print(f"[UnionMainEdgewaterPlanScraper] Skipping plan {idx+1}: No current price found")
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
                                    span = item.find('span')
                                    if span:
                                        beds = self.parse_beds(span.get_text())
                                elif 'x-baths' in item_class:
                                    span = item.find('span')
                                    if span:
                                        baths = self.parse_baths(span.get_text())
                                elif 'h-area' in item_class:
                                    span = item.find('span')
                                    if span:
                                        sqft = self.parse_sqft(span.get_text())
                        
                        if not sqft:
                            print(f"[UnionMainEdgewaterPlanScraper] Skipping plan {idx+1}: No square footage found")
                            continue
                        
                        # Calculate price per sqft
                        price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                        
                        # Extract image URL if available
                        image_url = ""
                        listing_thumb = listing.find('div', class_='listing-thumb')
                        if listing_thumb:
                            style_attr = listing_thumb.get('style', '')
                            url_match = re.search(r'url\(([^)]+)\)', style_attr)
                            if url_match:
                                image_url = url_match.group(1)
                        
                        plan_data = {
                            "price": current_price,
                            "sqft": sqft,
                            "stories": self.parse_stories(""),
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name,
                            "company": "UnionMain Homes",
                            "community": "Edgewater",
                            "type": "plan",
                            "beds": beds,
                            "baths": baths,
                            "address": plan_name,
                            "original_price": None,
                            "price_cut": "",
                            "image_url": image_url
                        }
                        
                        print(f"[UnionMainEdgewaterPlanScraper] Plan {idx+1}: {plan_data}")
                        listings.append(plan_data)
                        
                    except Exception as e:
                        print(f"[UnionMainEdgewaterPlanScraper] Error processing plan {idx+1}: {e}")
                        continue
            
            print(f"[UnionMainEdgewaterPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[UnionMainEdgewaterPlanScraper] Error: {e}")
            return []
