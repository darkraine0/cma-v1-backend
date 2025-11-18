import requests
import re
import json
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class HighlandHomesBrookvillePlanScraper(BaseScraper):
    URL = "https://www.highlandhomes.com/dfw/forney/devonshire"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract starting price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        # Handle ranges like "3-4" or single values like "4"
        if ' - ' in text:
            match = re.search(r'(\d+)\s*-\s*(\d+)', text)
            if match:
                return f"{match.group(1)}-{match.group(2)}"
        else:
            match = re.search(r'(\d+)', text)
            if match:
                return match.group(1)
        return ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle ranges like "2-3" or single values like "3"
        if ' - ' in text:
            match = re.search(r'(\d+)\s*-\s*(\d+)', text)
            if match:
                return f"{match.group(1)}-{match.group(2)}"
        else:
            match = re.search(r'(\d+)', text)
            if match:
                return match.group(1)
        return ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def parse_garages(self, text):
        """Extract number of garages from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def get_plan_name_from_code(self, plan_code):
        """Convert plan code to proper plan name."""
        plan_names = {
            '861-DENT': 'Denton Plan',
            '861-DAVE': 'Davenport Plan',
            '861-ESCA': 'Escape Plan',
            '861-CANT': 'Canterbury Plan',
            '861-FLEE': 'Fleetwood Plan',
            '861-CHST': 'Chesterfield Plan',
            '861-MCLA': 'McLaren Plan',
            '861-Pana': 'Panamera Plan',
            '861-LOTU': 'Lotus Plan',
            '861-CAMB': 'Cambridge Plan',
            '861-MIDL': 'Middleton Plan',
            '861-LEYL': 'Leyland Plan',
            '861-REGI': 'Regent Plan',
            '861-SHEF': 'Sheffield Plan'
        }
        return plan_names.get(plan_code, plan_code)

    def find_javascript_plans(self, soup):
        """Try to find plan data in JavaScript variables."""
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string:
                script_content = script.string
                
                # Look for the availableIfps array that contains plan data
                if 'availableIfps' in script_content:
                    print(f"[HighlandHomesBrookvillePlanScraper] Found availableIfps in JavaScript")
                    
                    # Extract the availableIfps array
                    match = re.search(r'const\s+availableIfps\s*=\s*(\[.*?\]);', script_content, re.DOTALL)
                    if match:
                        try:
                            plans_data = json.loads(match.group(1))
                            if isinstance(plans_data, list) and len(plans_data) > 0:
                                print(f"[HighlandHomesBrookvillePlanScraper] Found {len(plans_data)} plans in JavaScript")
                                return plans_data
                        except json.JSONDecodeError:
                            print(f"[HighlandHomesBrookvillePlanScraper] Failed to parse availableIfps JSON")
                            continue
                    
                    # Alternative pattern if the above doesn't work
                    match = re.search(r'availableIfps\s*=\s*(\[.*?\]);', script_content, re.DOTALL)
                    if match:
                        try:
                            plans_data = json.loads(match.group(1))
                            if isinstance(plans_data, list) and len(plans_data) > 0:
                                print(f"[HighlandHomesBrookvillePlanScraper] Found {len(plans_data)} plans in JavaScript (alt pattern)")
                                return plans_data
                        except json.JSONDecodeError:
                            print(f"[HighlandHomesBrookvillePlanScraper] Failed to parse availableIfps JSON (alt pattern)")
                            continue
        
        return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[HighlandHomesBrookvillePlanScraper] Fetching URL: {self.URL}")
            
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
            print(f"[HighlandHomesBrookvillePlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[HighlandHomesBrookvillePlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # First, try to find data in JavaScript variables
            js_plans = self.find_javascript_plans(soup)
            if js_plans:
                print(f"[HighlandHomesBrookvillePlanScraper] Processing JavaScript plan data")
                
                for plan in js_plans:
                    try:
                        # Extract data from JavaScript object
                        plan_code = plan.get('name') or plan.get('planName') or plan.get('model') or ''
                        price = plan.get('calcPrice') or plan.get('price') or plan.get('startingPrice')
                        stories = plan.get('stories') or plan.get('floors') or '1'
                        garages = plan.get('garages') or plan.get('garage') or ''
                        
                        if plan_code and price:
                            # Convert plan code to proper plan name
                            plan_name = self.get_plan_name_from_code(plan_code)
                            
                            # Check for duplicate plan names
                            if plan_name in seen_plan_names:
                                continue
                            seen_plan_names.add(plan_name)
                            
                            # Extract SQFT from JavaScript data
                            sqft = None
                            if plan.get('squareFootage'):
                                try:
                                    sqft = int(plan.get('squareFootage'))
                                except (ValueError, TypeError):
                                    pass
                            
                            # Extract beds from JavaScript data
                            beds = ""
                            if plan.get('bedroomsRange'):
                                # Handle ranges like "3-4" by taking the first number
                                beds_match = re.search(r'(\d+)', plan.get('bedroomsRange'))
                                if beds_match:
                                    beds = beds_match.group(1)
                            
                            # Extract baths from JavaScript data
                            baths = ""
                            if plan.get('bathsRange') and plan.get('halfBathsRange'):
                                try:
                                    # Handle ranges like "2-3" by taking the first number
                                    full_baths_match = re.search(r'(\d+)', plan.get('bathsRange'))
                                    half_baths_match = re.search(r'(\d+)', plan.get('halfBathsRange'))
                                    
                                    if full_baths_match and half_baths_match:
                                        full_baths = int(full_baths_match.group(1))
                                        half_baths = int(half_baths_match.group(1))
                                        total_baths = full_baths + (half_baths * 0.5)
                                        baths = str(total_baths)
                                except (ValueError, TypeError):
                                    pass
                            
                            # Calculate price per sqft if we have both price and sqft
                            price_per_sqft = None
                            if price and sqft and sqft > 0:
                                price_per_sqft = round(price / sqft, 2)
                            
                            plan_data = {
                                "price": price,
                                "sqft": sqft,
                                "stories": str(stories),
                                "price_per_sqft": price_per_sqft,
                                "plan_name": plan_name,
                                "company": "Highland Homes",
                                "community": "Brookville",
                                "type": "plan",
                                "beds": str(beds) if beds else "",
                                "baths": str(baths) if baths else "",
                                "status": "Plan",
                                "address": "",
                                "floor_plan": plan_name,
                                "garages": str(garages) if garages else ""
                            }
                            
                            print(f"[HighlandHomesBrookvillePlanScraper] JavaScript plan: {plan_data}")
                            listings.append(plan_data)
                    except Exception as e:
                        print(f"[HighlandHomesBrookvillePlanScraper] Error processing JavaScript plan: {e}")
                        continue
            
            # If no JavaScript data found, try to scrape from the static HTML
            if not listings:
                print(f"[HighlandHomesBrookvillePlanScraper] No JavaScript data found, trying static HTML")
                
                # Find all plan cards - these are in div elements with class 'card-grid_item' and contain 'homePlan'
                # Look specifically in the plans-compare element for floor plans
                plans_compare = soup.find('div', class_='plans-compare')
                if plans_compare:
                    plan_cards = plans_compare.find_all('div', class_='card-grid_item')
                    print(f"[HighlandHomesBrookvillePlanScraper] Found {len(plan_cards)} plan cards in plans-compare")
                    
                    for idx, card in enumerate(plan_cards):
                        try:
                            print(f"[HighlandHomesBrookvillePlanScraper] Processing plan card {idx+1}")
                            
                            # Skip the last container which is just a CTA
                            if 'mobileOnlyHomeSwipeCTA' in card.get_text():
                                print(f"[HighlandHomesBrookvillePlanScraper] Skipping plan card {idx+1}: CTA container")
                                continue
                            
                            # Check if this is a plan card (contains homePlan class)
                            if not card.find('div', class_='homePlan'):
                                print(f"[HighlandHomesBrookvillePlanScraper] Skipping plan card {idx+1}: Not a plan card")
                                continue
                            
                            # Extract plan name from span with class 'homeIdentifier'
                            plan_name_elem = card.find('span', class_='homeIdentifier')
                            if not plan_name_elem:
                                print(f"[HighlandHomesBrookvillePlanScraper] Skipping plan card {idx+1}: No plan name found")
                                continue
                            
                            plan_name = plan_name_elem.get_text(strip=True)
                            if not plan_name:
                                print(f"[HighlandHomesBrookvillePlanScraper] Skipping plan card {idx+1}: Empty plan name")
                                continue
                            
                            # Check for duplicate plan names
                            if plan_name in seen_plan_names:
                                print(f"[HighlandHomesBrookvillePlanScraper] Skipping plan card {idx+1}: Duplicate plan name '{plan_name}'")
                                continue
                            
                            seen_plan_names.add(plan_name)
                            
                            # Extract starting price from span with class 'price'
                            starting_price = None
                            price_elem = card.find('span', class_='price')
                            if price_elem:
                                starting_price = self.parse_price(price_elem.get_text())
                            
                            if not starting_price:
                                print(f"[HighlandHomesBrookvillePlanScraper] Skipping plan card {idx+1}: No starting price found")
                                continue
                            
                            # Extract square footage from div with class 'homeDetails'
                            sqft = None
                            home_details = card.find('div', class_='homeDetails')
                            if home_details:
                                detail_items = home_details.find_all('div', class_='homeDetailItem')
                                for item in detail_items:
                                    item_text = item.get_text(strip=True)
                                    if 'base sq ft' in item_text:
                                        sqft = self.parse_sqft(item_text)
                                        break
                            
                            if not sqft:
                                print(f"[HighlandHomesBrookvillePlanScraper] Skipping plan card {idx+1}: No square footage found")
                                continue
                            
                            # Extract beds, baths, stories, and garages from div with class 'homeDetails'
                            beds = ""
                            baths = ""
                            stories = "1"
                            garages = ""
                            
                            if home_details:
                                detail_items = home_details.find_all('div', class_='homeDetailItem')
                                for item in detail_items:
                                    item_text = item.get_text(strip=True)
                                    if 'beds' in item_text:
                                        beds = self.parse_beds(item_text)
                                    elif 'full baths' in item_text:
                                        baths = self.parse_baths(item_text)
                                    elif 'stories' in item_text:
                                        stories = self.parse_stories(item_text)
                                    elif 'garages' in item_text:
                                        garages = self.parse_garages(item_text)
                            
                            # Calculate price per sqft
                            price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                            
                            plan_data = {
                                "price": starting_price,
                                "sqft": sqft,
                                "stories": stories,
                                "price_per_sqft": price_per_sqft,
                                "plan_name": plan_name,
                                "company": "Highland Homes",
                                "community": "Brookville",
                                "type": "plan",
                                "beds": beds,
                                "baths": baths,
                                "status": "Plan",
                                "address": "",
                                "floor_plan": plan_name,
                                "garages": garages
                            }
                            
                            print(f"[HighlandHomesBrookvillePlanScraper] Plan card {idx+1}: {plan_data}")
                            listings.append(plan_data)
                            
                        except Exception as e:
                            print(f"[HighlandHomesBrookvillePlanScraper] Error processing plan card {idx+1}: {e}")
                            continue
                else:
                    print(f"[HighlandHomesBrookvillePlanScraper] No plans-compare element found")
            
            print(f"[HighlandHomesBrookvillePlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[HighlandHomesBrookvillePlanScraper] Error: {e}")
            return []
