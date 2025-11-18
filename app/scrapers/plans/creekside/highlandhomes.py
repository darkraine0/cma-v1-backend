import requests
import re
import json
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class HighlandHomesCreeksidePlanScraper(BaseScraper):
    URLS = [
        "https://www.highlandhomes.com/dfw/royse-city/creekshaw"
    ]

    def parse_sqft(self, text):
        """Extract square footage from text."""
        if not text:
            return None
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text."""
        if not text:
            return None
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        if not text:
            return None
        # Handle ranges like "3-4" by taking the first number
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else None

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        if not text:
            return None
        # Handle ranges like "2-3" by taking the first number
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else None

    def parse_stories(self, text):
        """Extract number of stories from text."""
        if not text:
            return None
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else None

    def parse_lot_size(self, text):
        """Extract lot size from text."""
        # Not available in the provided HTML structure
        return None

    def find_javascript_plans(self, soup):
        """Try to find plan data in JavaScript variables."""
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string:
                script_content = script.string
                
                # Look for the availableIfps array that contains plan data
                if 'availableIfps' in script_content:
                    print(f"[HighlandHomesCreeksidePlanScraper] Found availableIfps in JavaScript")
                    
                    # Extract the availableIfps array
                    match = re.search(r'const\s+availableIfps\s*=\s*(\[.*?\]);', script_content, re.DOTALL)
                    if match:
                        try:
                            plans_data = json.loads(match.group(1))
                            if isinstance(plans_data, list) and len(plans_data) > 0:
                                print(f"[HighlandHomesCreeksidePlanScraper] Found {len(plans_data)} plans in JavaScript")
                                return plans_data
                        except json.JSONDecodeError:
                            print(f"[HighlandHomesCreeksidePlanScraper] Failed to parse availableIfps JSON")
                            continue
                    
                    # Alternative pattern if the above doesn't work
                    match = re.search(r'availableIfps\s*=\s*(\[.*?\]);', script_content, re.DOTALL)
                    if match:
                        try:
                            plans_data = json.loads(match.group(1))
                            if isinstance(plans_data, list) and len(plans_data) > 0:
                                print(f"[HighlandHomesCreeksidePlanScraper] Found {len(plans_data)} plans in JavaScript (alt pattern)")
                                return plans_data
                        except json.JSONDecodeError:
                            print(f"[HighlandHomesCreeksidePlanScraper] Failed to parse availableIfps JSON (alt pattern)")
                            continue
        
        return None

    def extract_plan_data(self, plan_card):
        """Extract data from a plan card div."""
        try:
            # Extract plan name from the home identifier
            plan_name = None
            plan_elem = plan_card.find('span', class_='homeIdentifier')
            if plan_elem:
                plan_name = plan_elem.get_text(strip=True)

            # Extract price
            price = None
            price_elem = plan_card.find('span', class_='price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self.parse_price(price_text)

            # Extract features from the home details
            beds = None
            baths = None
            stories = None
            sqft = None

            home_details = plan_card.find('div', class_='homeDetails')
            if home_details:
                detail_items = home_details.find_all('div', class_='homeDetailItem')
                for item in detail_items:
                    label_elem = item.find('span', class_='label')
                    numeral_elem = item.find('span', class_='numeral')
                    if label_elem and numeral_elem:
                        label = label_elem.get_text(strip=True).lower()
                        numeral = numeral_elem.get_text(strip=True)
                        
                        if 'bed' in label:
                            beds = self.parse_beds(numeral)
                        elif 'bath' in label and 'full' in label:
                            # For full baths, we'll use the numeral directly
                            baths = self.parse_baths(numeral)
                        elif 'stor' in label:
                            stories = self.parse_stories(numeral)
                        elif 'sq ft' in label or 'base sq ft' in label:
                            sqft = self.parse_sqft(numeral)

            # Extract lot size (not available in this structure)
            lot_size = None

            return {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "plan_name": plan_name,
                "beds": beds,
                "baths": baths,
                "lot_size": lot_size
            }

        except Exception as e:
            print(f"[HighlandHomesCreeksidePlanScraper] Error extracting plan data: {e}")
            return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[HighlandHomesCreeksidePlanScraper] Fetching URLs: {self.URLS}")
            
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

            all_plans = []
            seen_plan_names = set()  # Track plan names to prevent duplicates

            for url_idx, url in enumerate(self.URLS):
                try:
                    print(f"[HighlandHomesCreeksidePlanScraper] Processing URL {url_idx + 1}: {url}")

                    resp = requests.get(url, headers=headers, timeout=15)
                    print(f"[HighlandHomesCreeksidePlanScraper] URL {url_idx + 1} response status: {resp.status_code}")

                    if resp.status_code != 200:
                        print(f"[HighlandHomesCreeksidePlanScraper] URL {url_idx + 1} request failed with status {resp.status_code}")
                        continue

                    soup = BeautifulSoup(resp.content, 'html.parser')
                    
                    # First, try to find data in JavaScript variables
                    js_plans = self.find_javascript_plans(soup)
                    if js_plans:
                        print(f"[HighlandHomesCreeksidePlanScraper] Processing JavaScript plan data")
                        
                        for plan in js_plans:
                            try:
                                # Extract data from JavaScript object
                                plan_code = plan.get('name') or plan.get('planName') or plan.get('model') or ''
                                price = plan.get('calcPrice') or plan.get('price') or plan.get('startingPrice')
                                stories = plan.get('stories') or plan.get('floors') or '1'
                                
                                if plan_code and price:
                                    # Convert plan code to proper plan name
                                    plan_name = plan_code
                                    
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
                                    
                                    # Create the final plan data
                                    final_plan_data = {
                                        "price": price,
                                        "sqft": sqft,
                                        "stories": str(stories),
                                        "price_per_sqft": price_per_sqft,
                                        "plan_name": plan_name,
                                        "company": "Highland Homes",
                                        "community": "Creekside",
                                        "type": "plan",
                                        "beds": beds,
                                        "baths": baths,
                                        "lot_size": None
                                    }
                                    
                                    print(f"[HighlandHomesCreeksidePlanScraper] JavaScript plan: {final_plan_data}")
                                    all_plans.append(final_plan_data)
                                    
                            except Exception as e:
                                print(f"[HighlandHomesCreeksidePlanScraper] Error processing JavaScript plan: {e}")
                                continue
                    
                    # If no JavaScript data found, fall back to HTML parsing
                    if not js_plans:
                        print(f"[HighlandHomesCreeksidePlanScraper] No JavaScript data found, falling back to HTML parsing")
                        
                        # Look for plan cards in the plans-compare section
                        plans_section = soup.find('div', class_='plans-compare')
                        if plans_section:
                            plan_cards = plans_section.find_all('a', class_='homePlan')
                            print(f"[HighlandHomesCreeksidePlanScraper] URL {url_idx + 1}: Found {len(plan_cards)} plan cards in plans-compare section")
                        else:
                            # Fallback: look for any homePlan elements
                            plan_cards = soup.find_all('a', class_='homePlan')
                            print(f"[HighlandHomesCreeksidePlanScraper] URL {url_idx + 1}: Found {len(plan_cards)} plan cards (fallback)")

                        for card_idx, plan_card in enumerate(plan_cards):
                            try:
                                print(f"[HighlandHomesCreeksidePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Processing plan card")

                                # Extract data from the plan card
                                plan_data = self.extract_plan_data(plan_card)
                                if not plan_data:
                                    print(f"[HighlandHomesCreeksidePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Failed to extract plan data")
                                    continue

                                # Check for required fields - require plan_name
                                if not plan_data.get('plan_name'):
                                    print(f"[HighlandHomesCreeksidePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Missing plan name")
                                    continue

                                # Check for duplicate plans - use plan_name as unique identifier
                                plan_name = plan_data.get('plan_name')
                                if plan_name in seen_plan_names:
                                    print(f"[HighlandHomesCreeksidePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Duplicate plan {plan_name}")
                                    continue
                                seen_plan_names.add(plan_name)

                                # Calculate price per square foot if both price and sqft are available
                                price_per_sqft = None
                                if plan_data.get('price') and plan_data.get('sqft'):
                                    price_per_sqft = round(plan_data['price'] / plan_data['sqft'], 2) if plan_data['sqft'] > 0 else None

                                # Create the final plan data
                                final_plan_data = {
                                    "price": plan_data['price'],
                                    "sqft": plan_data['sqft'],
                                    "stories": plan_data['stories'],
                                    "price_per_sqft": price_per_sqft,
                                    "plan_name": plan_data['plan_name'],
                                    "company": "Highland Homes",
                                    "community": "Creekside",
                                    "type": "plan",
                                    "beds": plan_data['beds'],
                                    "baths": plan_data['baths'],
                                    "lot_size": plan_data['lot_size']
                                }

                                print(f"[HighlandHomesCreeksidePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: {final_plan_data}")
                                all_plans.append(final_plan_data)

                            except Exception as e:
                                print(f"[HighlandHomesCreeksidePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Error processing card: {e}")
                                continue

                except Exception as e:
                    print(f"[HighlandHomesCreeksidePlanScraper] Error processing URL {url_idx + 1}: {e}")
                    continue

            print(f"[HighlandHomesCreeksidePlanScraper] Successfully processed {len(all_plans)} total plans across all URLs")
            return all_plans

        except Exception as e:
            print(f"[HighlandHomesCreeksidePlanScraper] Error: {e}")
            return []
