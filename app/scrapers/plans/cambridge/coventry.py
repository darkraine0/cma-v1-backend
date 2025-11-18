import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class CoventryCambridgePlanScraper(BaseScraper):
    URL = "https://www.coventryhomes.com/new-homes/tx/celina/cambridge-crossing/"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract base price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "2" and "2/1" formats
        match = re.search(r'(\d+(?:/\d+)?)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[CoventryCambridgePlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[CoventryCambridgePlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[CoventryCambridgePlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            plans = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all floor plan model cards - look for model-card divs that contain floor plan info
            # These are different from the quick move-in model cards
            model_cards = soup.find_all('div', class_='model-card')
            print(f"[CoventryCambridgePlanScraper] Found {len(model_cards)} total model cards")
            
            for idx, card in enumerate(model_cards):
                try:
                    print(f"[CoventryCambridgePlanScraper] Processing model card {idx+1}")
                    
                    # Check if this is a floor plan (has model name) vs quick move-in (has address)
                    model_name_elem = card.find('div', class_='model-name')
                    if not model_name_elem:
                        print(f"[CoventryCambridgePlanScraper] Skipping card {idx+1}: No model name found (likely quick move-in)")
                        continue
                    
                    plan_name = model_name_elem.get_text(strip=True)
                    if not plan_name:
                        print(f"[CoventryCambridgePlanScraper] Skipping card {idx+1}: Empty model name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[CoventryCambridgePlanScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract base price from the price bar
                    price_bar = card.find('a', class_='price-bar')
                    if not price_bar:
                        print(f"[CoventryCambridgePlanScraper] Skipping card {idx+1}: No price bar found")
                        continue
                    
                    price_text = price_bar.get_text(strip=True)
                    base_price = self.parse_price(price_text)
                    if not base_price:
                        print(f"[CoventryCambridgePlanScraper] Skipping card {idx+1}: Could not parse price from '{price_text}'")
                        continue
                    
                    # Extract square footage, beds, and baths from the model info bar
                    info_bar = card.find('ul', class_='model-info-bar')
                    if not info_bar:
                        print(f"[CoventryCambridgePlanScraper] Skipping card {idx+1}: No info bar found")
                        continue
                    
                    info_items = info_bar.find_all('li')
                    sqft = None
                    beds = ""
                    baths = ""
                    
                    for item in info_items:
                        item_text = item.get_text(strip=True)
                        if 'AREA (SQFT)' in item_text:
                            sqft = self.parse_sqft(item_text)
                        elif 'Beds' in item_text:
                            beds = self.parse_beds(item_text)
                        elif 'Baths' in item_text:
                            baths = self.parse_baths(item_text)
                    
                    if not sqft:
                        print(f"[CoventryCambridgePlanScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(base_price / sqft, 2) if sqft > 0 else None
                    
                    # Determine stories based on plan name or size (some plans are 2-story)
                    stories = "2" if sqft > 2500 else "1"  # Larger plans tend to be 2-story
                    
                    plan_data = {
                        "price": base_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Coventry Homes",
                        "community": "Cambridge",
                        "type": "plan",  # This is for floor plans, not quick move-ins
                        "beds": beds,
                        "baths": baths,
                        "address": plan_name  # Use plan name as address for floor plans
                    }
                    
                    print(f"[CoventryCambridgePlanScraper] Floor Plan: {plan_data}")
                    plans.append(plan_data)
                    
                except Exception as e:
                    print(f"[CoventryCambridgePlanScraper] Error processing model card {idx+1}: {e}")
                    continue
            
            print(f"[CoventryCambridgePlanScraper] Successfully processed {len(plans)} unique floor plans")
            return plans
            
        except Exception as e:
            print(f"[CoventryCambridgePlanScraper] Error: {e}")
            return []
