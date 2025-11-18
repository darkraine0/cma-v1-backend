import requests
import re
import json
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class HighlandHomesBrookvilleNowScraper(BaseScraper):
    URL = "https://www.highlandhomes.com/dfw/forney/devonshire"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        # Handle "Call" case
        if 'Call' in text:
            return None
        
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle formats like "3/1" (3 full, 1 half)
        if '/' in text:
            match = re.search(r'(\d+)/(\d+)', text)
            if match:
                full_baths = int(match.group(1))
                half_baths = int(match.group(2))
                total_baths = full_baths + (half_baths * 0.5)
                return str(total_baths)
        
        # Handle single number
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def parse_garages(self, text):
        """Extract number of garages from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def find_javascript_data(self, soup):
        """Try to find home data in JavaScript variables."""
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string:
                script_content = script.string
                
                # Look for various JavaScript patterns that might contain home data
                patterns = [
                    r'window\.homes\s*=\s*(\[.*?\]);',
                    r'window\.listings\s*=\s*(\[.*?\]);',
                    r'window\.inventory\s*=\s*(\[.*?\]);',
                    r'window\.properties\s*=\s*(\[.*?\]);',
                    r'var\s+homes\s*=\s*(\[.*?\]);',
                    r'var\s+listings\s*=\s*(\[.*?\]);',
                    r'var\s+inventory\s*=\s*(\[.*?\]);',
                    r'var\s+properties\s*=\s*(\[.*?\]);',
                    r'const\s+homes\s*=\s*(\[.*?\]);',
                    r'const\s+listings\s*=\s*(\[.*?\]);',
                    r'const\s+inventory\s*=\s*(\[.*?\]);',
                    r'const\s+properties\s*=\s*(\[.*?\]);',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, script_content, re.DOTALL | re.IGNORECASE)
                    for match in matches:
                        try:
                            data = json.loads(match)
                            if isinstance(data, list) and len(data) > 0:
                                print(f"[HighlandHomesBrookvilleNowScraper] Found JavaScript data with {len(data)} items")
                                return data
                        except json.JSONDecodeError:
                            continue
        
        return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[HighlandHomesBrookvilleNowScraper] Fetching URL: {self.URL}")
            
            # Use headers that avoid compression issues
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "identity",  # Avoid compression to prevent corrupted content
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[HighlandHomesBrookvilleNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[HighlandHomesBrookvilleNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # First, try to find data in JavaScript variables
            js_data = self.find_javascript_data(soup)
            if js_data:
                print(f"[HighlandHomesBrookvilleNowScraper] Processing JavaScript data")
                # Process the JavaScript data
                for item in js_data:
                    try:
                        # Extract data from JavaScript object
                        address = item.get('address') or item.get('street') or item.get('location') or ''
                        plan_name = item.get('plan') or item.get('planName') or item.get('model') or ''
                        price = item.get('price') or item.get('listPrice') or item.get('currentPrice')
                        sqft = item.get('sqft') or item.get('squareFeet') or item.get('size')
                        beds = item.get('beds') or item.get('bedrooms') or item.get('bed')
                        baths = item.get('baths') or item.get('bathrooms') or item.get('bath')
                        stories = item.get('stories') or item.get('floors') or '1'
                        garages = item.get('garages') or item.get('garage') or ''
                        status = item.get('status') or item.get('availability') or 'Now'
                        
                        if address and plan_name and price and sqft:
                            # Check for duplicate addresses
                            if address in seen_addresses:
                                continue
                            seen_addresses.add(address)
                            
                            # Calculate price per sqft
                            price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                            
                            plan_data = {
                                "price": price,
                                "sqft": sqft,
                                "stories": str(stories),
                                "price_per_sqft": price_per_sqft,
                                "plan_name": plan_name,
                                "company": "Highland Homes",
                                "community": "Brookville",
                                "type": "now",
                                "beds": str(beds),
                                "baths": str(baths),
                                "status": status,
                                "address": address,
                                "floor_plan": plan_name,
                                "garages": str(garages)
                            }
                            
                            print(f"[HighlandHomesBrookvilleNowScraper] JavaScript item: {plan_data}")
                            listings.append(plan_data)
                    except Exception as e:
                        print(f"[HighlandHomesBrookvilleNowScraper] Error processing JavaScript item: {e}")
                        continue
            
            # If no JavaScript data found, try to scrape from the static HTML
            if not listings:
                print(f"[HighlandHomesBrookvilleNowScraper] No JavaScript data found, trying static HTML")
                
                # Look for the moveInReadyContainer which contains the actual inventory homes
                move_in_ready_container = soup.find('div', id='moveInReadyContainer')
                if move_in_ready_container:
                    print(f"[HighlandHomesBrookvilleNowScraper] Found moveInReadyContainer")
                    
                    # Look for home containers within this section
                    home_containers = move_in_ready_container.find_all('div', class_='home-container-column-block')
                    print(f"[HighlandHomesBrookvilleNowScraper] Found {len(home_containers)} home containers in moveInReadyContainer")
                    
                    for idx, container in enumerate(home_containers):
                        try:
                            print(f"[HighlandHomesBrookvilleNowScraper] Processing home container {idx+1}")
                            
                            # Extract address from span with class 'homeIdentifier'
                            address_elem = container.find('span', class_='homeIdentifier')
                            if not address_elem:
                                print(f"[HighlandHomesBrookvilleNowScraper] Skipping home container {idx+1}: No address found")
                                continue
                            
                            address = address_elem.get_text(strip=True)
                            if not address:
                                print(f"[HighlandHomesBrookvilleNowScraper] Skipping home container {idx+1}: Empty address")
                                continue
                            
                            # Check for duplicate addresses
                            if address in seen_addresses:
                                print(f"[HighlandHomesBrookvilleNowScraper] Skipping home container {idx+1}: Duplicate address '{address}'")
                                continue
                            
                            seen_addresses.add(address)
                            
                            # Extract plan name from the container - look for plan name text
                            plan_name = ""
                            # Look for plan name in the container text
                            container_text = container.get_text()
                            # Extract plan name before "with X upgrades" or other text
                            # Look for patterns like "Canterbury Plan", "Panamera Plan", etc.
                            plan_match = re.search(r'([A-Za-z\s]+Plan)(?:\s+with\s+\d+\s+upgrades)?', container_text)
                            if plan_match:
                                plan_name = plan_match.group(1).strip()
                            else:
                                # Alternative pattern: look for plan names that end with "Plan"
                                plan_match = re.search(r'([A-Za-z]+)\s+Plan', container_text)
                                if plan_match:
                                    plan_name = plan_match.group(1) + " Plan"
                            
                            if not plan_name:
                                print(f"[HighlandHomesBrookvilleNowScraper] Skipping home container {idx+1}: No plan name found")
                                continue
                            
                            # Extract price from the container text
                            current_price = None
                            price_match = re.search(r'\$([\d,]+)', container_text)
                            if price_match:
                                current_price = int(price_match.group(1).replace(",", ""))
                            
                            if not current_price:
                                print(f"[HighlandHomesBrookvilleNowScraper] Skipping home container {idx+1}: No current price found")
                                continue
                            
                            # Extract square footage from the container text
                            sqft = None
                            sqft_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*sq\s*ft', container_text)
                            if sqft_match:
                                sqft = int(sqft_match.group(1).replace(",", ""))
                            
                            if not sqft:
                                print(f"[HighlandHomesBrookvilleNowScraper] Skipping home container {idx+1}: No square footage found")
                                continue
                            
                            # Extract beds, baths, stories, and garages from the container text
                            beds = ""
                            baths = ""
                            stories = "1"
                            garages = ""
                            
                            # Extract beds
                            beds_match = re.search(r'(\d+)\s*beds?', container_text)
                            if beds_match:
                                beds = beds_match.group(1)
                            
                            # Extract baths (handle formats like "3/1")
                            baths_match = re.search(r'(\d+)/(\d+)\s*baths?', container_text)
                            if baths_match:
                                full_baths = int(baths_match.group(1))
                                half_baths = int(baths_match.group(2))
                                total_baths = full_baths + (half_baths * 0.5)
                                baths = str(total_baths)
                            else:
                                # Look for single number of baths
                                baths_match = re.search(r'(\d+)\s*baths?', container_text)
                                if baths_match:
                                    baths = baths_match.group(1)
                            
                            # Extract stories
                            stories_match = re.search(r'(\d+)\s*stories?', container_text)
                            if stories_match:
                                stories = stories_match.group(1)
                            
                            # Extract garages
                            garages_match = re.search(r'(\d+)\s*garages?', container_text)
                            if garages_match:
                                garages = garages_match.group(1)
                            
                            # Calculate price per sqft
                            price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                            
                            plan_data = {
                                "price": current_price,
                                "sqft": sqft,
                                "stories": stories,
                                "price_per_sqft": price_per_sqft,
                                "plan_name": plan_name,
                                "company": "Highland Homes",
                                "community": "Brookville",
                                "type": "now",
                                "beds": beds,
                                "baths": baths,
                                "status": "Now",
                                "address": address,
                                "floor_plan": plan_name,
                                "garages": garages
                            }
                            
                            print(f"[HighlandHomesBrookvilleNowScraper] Home container {idx+1}: {plan_data}")
                            listings.append(plan_data)
                            
                        except Exception as e:
                            print(f"[HighlandHomesBrookvilleNowScraper] Error processing home container {idx+1}: {e}")
                            continue
                else:
                    print(f"[HighlandHomesBrookvilleNowScraper] No moveInReadyContainer element found")
                    
                    # Fallback: try to find any elements with "Complete & Move-in Ready" text
                    move_in_ready_elements = soup.find_all(string=lambda text: text and 'move-in ready' in text.lower())
                    if move_in_ready_elements:
                        print(f"[HighlandHomesBrookvilleNowScraper] Found {len(move_in_ready_elements)} 'Move-in Ready' elements")
                        # Look for the container that holds these elements
                        for elem in move_in_ready_elements:
                            container = elem.parent
                            for _ in range(5):  # Go up to 5 levels to find the main container
                                if container.parent:
                                    container = container.parent
                                    if container.name == 'div' and container.get('class'):
                                        if 'home-container-column-block' in container.get('class', []):
                                            print(f"[HighlandHomesBrookvilleNowScraper] Found home container with class: {container.get('class')}")
                                            break
            
            print(f"[HighlandHomesBrookvilleNowScraper] Successfully processed {len(listings)} home containers")
            return listings
            
        except Exception as e:
            print(f"[HighlandHomesBrookvilleNowScraper] Error: {e}")
            return []
