import requests
from bs4 import BeautifulSoup
import re
from ...base import BaseScraper
from typing import List, Dict

class UnionMainElevonPlanScraper(BaseScraper):
    URL = "https://unionmainhomes.com/communities/elevon/"

    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract base price from text."""
        # Try "from $X" pattern first
        match = re.search(r'from \$([\d,]+)', text)
        if match:
            return int(match.group(1).replace(",", ""))
        # Fall back to "$X" pattern (without "from")
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def is_floor_plan(self, title):
        """Check if the title represents a floor plan (not an address)."""
        # Floor plans have names like "Burnet", "Blackburn", "Chisholm"
        # Addresses have patterns like "1160 Butterfly Dale Dr." or "216 Hope Orchard"
        address_pattern = r'\d+\s+[A-Za-z\s]+(?:Ln|Ct|St|Dr|Ave|Blvd|Dale|Orchard|Cove|Pl|Bridge|Holly)\.?'
        return not re.search(address_pattern, title, re.IGNORECASE)

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[UnionMainElevonPlanScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[UnionMainElevonPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[UnionMainElevonPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            plans = []
            seen_plan_names = set()
            
            # Try new structure first (e-loop-item)
            loop_items = soup.find_all('div', class_='e-loop-item')
            floorplan_items = [item for item in loop_items if 'floorplan' in item.get('class', [])]
            
            if floorplan_items:
                print(f"[UnionMainElevonPlanScraper] Found {len(floorplan_items)} floorplan items (new structure)")
                for idx, item in enumerate(floorplan_items):
                    try:
                        print(f"[UnionMainElevonPlanScraper] Processing item {idx+1}")
                        
                        # Extract plan name from h2 element
                        plan_name_elem = item.find('h2', class_='elementor-heading-title')
                        plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else None
                        
                        if not plan_name:
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: No plan name found")
                            continue
                        
                        # Check if this is actually a floor plan (not an address)
                        if not self.is_floor_plan(plan_name):
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: This is an address, not a floor plan: {plan_name}")
                            continue
                        
                        # Check for duplicate plan names
                        if plan_name in seen_plan_names:
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: Duplicate plan name '{plan_name}'")
                            continue
                        
                        seen_plan_names.add(plan_name)
                        
                        # Extract price from h4 elements
                        # Look for price container with structure: old price -> arrow -> new price
                        # The new price is the last price in the sequence
                        h4_elements = item.find_all('h4', class_='elementor-heading-title')
                        base_price = None
                        original_price = None
                        
                        # Find all price values in h4 elements
                        price_values = []
                        for element in h4_elements:
                            text = element.get_text(strip=True)
                            # Try both parse_price patterns (with $ and with "from $")
                            parsed_price = self.parse_price(text)
                            if parsed_price:
                                price_values.append(parsed_price)
                        
                        # If there are multiple prices, the last one is the new price
                        # and the first one is the original price
                        if len(price_values) > 1:
                            original_price = price_values[0]
                            base_price = price_values[-1]  # Last price is the new price
                        elif len(price_values) == 1:
                            base_price = price_values[0]
                        
                        if not base_price:
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: No price found")
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
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: No square footage found")
                            continue
                        
                        # Calculate price per sqft
                        price_per_sqft = round(base_price / sqft, 2) if sqft > 0 else None
                        
                        plan_data = {
                            "price": base_price,
                            "sqft": sqft,
                            "stories": "2",
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name,
                            "company": "UnionMain Homes",
                            "community": "Elevon",
                            "type": "plan",
                            "beds": beds if beds else "",
                            "baths": baths if baths else "",
                            "address": plan_name
                        }
                        
                        print(f"[UnionMainElevonPlanScraper] Floor Plan: {plan_data}")
                        plans.append(plan_data)
                        
                    except Exception as e:
                        print(f"[UnionMainElevonPlanScraper] Error processing item {idx+1}: {e}")
                        continue
            else:
                # Fall back to old structure
                plan_items = soup.find_all('div', class_='single-fp')
                print(f"[UnionMainElevonPlanScraper] Found {len(plan_items)} total items (old structure)")
                
                for idx, item in enumerate(plan_items):
                    try:
                        print(f"[UnionMainElevonPlanScraper] Processing item {idx+1}")
                        
                        # Extract plan name
                        title_elem = item.find('h2', class_='item-title')
                        if not title_elem:
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: No title found")
                            continue
                        
                        plan_name = title_elem.get_text(strip=True)
                        if not plan_name:
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: Empty plan name")
                            continue
                        
                        # Check if this is actually a floor plan (not an address from the Now tab)
                        if not self.is_floor_plan(plan_name):
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: This is an address, not a floor plan: {plan_name}")
                            continue
                        
                        # Extract base price
                        price_elem = item.find('div', class_='item-price')
                        if not price_elem:
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: No price found")
                            continue
                        
                        price_text = price_elem.get_text(strip=True)
                        base_price = self.parse_price(price_text)
                        if not base_price:
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: Could not parse price from '{price_text}'")
                            continue
                        
                        # Extract square footage
                        area_elem = item.find('li', class_='h-area')
                        if not area_elem:
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: No square footage found")
                            continue
                        
                        sqft_text = area_elem.get_text(strip=True)
                        sqft = self.parse_sqft(sqft_text)
                        if not sqft:
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: Could not parse sqft from '{sqft_text}'")
                            continue
                        
                        # Extract bedrooms
                        beds_elem = item.find('li', class_='x-beds')
                        beds = self.parse_beds(beds_elem.get_text(strip=True)) if beds_elem else ""
                        
                        # Extract bathrooms
                        baths_elem = item.find('li', class_='x-baths')
                        baths = self.parse_baths(baths_elem.get_text(strip=True)) if baths_elem else ""
                        
                        # Calculate price per sqft
                        price_per_sqft = round(base_price / sqft, 2) if sqft > 0 else None
                        
                        # Extract address/community info
                        address_elem = item.find('address', class_='item-address')
                        address = address_elem.get_text(strip=True) if address_elem else plan_name
                        
                        plan_data = {
                            "price": base_price,
                            "sqft": sqft,
                            "stories": "2",
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name,
                            "company": "UnionMain Homes",
                            "community": "Elevon",
                            "type": "plan",
                            "beds": beds,
                            "baths": baths,
                            "address": address
                        }
                        
                        print(f"[UnionMainElevonPlanScraper] Floor Plan: {plan_data}")
                        plans.append(plan_data)
                        
                    except Exception as e:
                        print(f"[UnionMainElevonPlanScraper] Error processing item {idx+1}: {e}")
                        continue
            
            print(f"[UnionMainElevonPlanScraper] Successfully processed {len(plans)} floor plans")
            return plans
        except Exception as e:
            print(f"[UnionMainElevonPlanScraper] Error: {e}")
            return [] 