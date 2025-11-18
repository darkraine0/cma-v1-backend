import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class BeazerHomesBrookvillePlanScraper(BaseScraper):
    URL = "https://www.beazer.com/dallas-tx/brookville-estates"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        # Handle ranges like "2,431 - 2,778" or single values like "1,875"
        if ' - ' in text:
            # Take the first number for ranges
            match = re.search(r'([\d,]+)', text)
        else:
            match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract starting price from text."""
        match = re.search(r'From \$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        # Handle ranges like "3 - 4" or single values like "4"
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
        # Handle ranges like "2.5 - 3" or single values like "2.5"
        if ' - ' in text:
            match = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', text)
            if match:
                return f"{match.group(1)}-{match.group(2)}"
        else:
            match = re.search(r'(\d+(?:\.\d+)?)', text)
            if match:
                return match.group(1)
        return ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        # Default to 1 story for these homes based on the data
        return "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[BeazerHomesBrookvillePlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[BeazerHomesBrookvillePlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[BeazerHomesBrookvillePlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all plan cards - these are in div elements with class 'card_list_item' and data-product-type="plan"
            plan_cards = soup.find_all('div', attrs={'data-product-type': 'plan'})
            print(f"[BeazerHomesBrookvillePlanScraper] Found {len(plan_cards)} plan cards")
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[BeazerHomesBrookvillePlanScraper] Processing plan card {idx+1}")
                    
                    # Extract plan name from h2 element with class 'font24 bold'
                    plan_name_elem = card.find('h2', class_='font24 bold')
                    if not plan_name_elem:
                        print(f"[BeazerHomesBrookvillePlanScraper] Skipping plan card {idx+1}: No plan name found")
                        continue
                    
                    plan_name = plan_name_elem.get_text(strip=True)
                    if not plan_name:
                        print(f"[BeazerHomesBrookvillePlanScraper] Skipping plan card {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[BeazerHomesBrookvillePlanScraper] Skipping plan card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract starting price from p element with class 'font18 no-margin right-align'
                    price_elem = card.find('p', class_='font18 no-margin right-align')
                    if not price_elem:
                        print(f"[BeazerHomesBrookvillePlanScraper] Skipping plan card {idx+1}: No price found")
                        continue
                    
                    starting_price = self.parse_price(price_elem.get_text())
                    if not starting_price:
                        print(f"[BeazerHomesBrookvillePlanScraper] Skipping plan card {idx+1}: No starting price found")
                        continue
                    
                    # Extract square footage from li elements
                    sqft = None
                    list_items = card.find_all('li')
                    for item in list_items:
                        item_text = item.get_text(strip=True)
                        if 'Sq. Ft.' in item_text:
                            sqft = self.parse_sqft(item_text)
                            break
                    
                    if not sqft:
                        print(f"[BeazerHomesBrookvillePlanScraper] Skipping plan card {idx+1}: No square footage found")
                        continue
                    
                    # Extract beds and baths from li elements
                    beds = ""
                    baths = ""
                    stories = "1"
                    
                    for item in list_items:
                        item_text = item.get_text(strip=True)
                        if 'Bedroom' in item_text:
                            beds = self.parse_beds(item_text)
                        elif 'Bathroom' in item_text:
                            baths = self.parse_baths(item_text)
                    
                    # Calculate price per sqft
                    price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                    
                    plan_data = {
                        "price": starting_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Beazer Homes",
                        "community": "Brookville",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "status": "Plan",
                        "address": "",
                        "floor_plan": plan_name
                    }
                    
                    print(f"[BeazerHomesBrookvillePlanScraper] Plan card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[BeazerHomesBrookvillePlanScraper] Error processing plan card {idx+1}: {e}")
                    continue
            
            print(f"[BeazerHomesBrookvillePlanScraper] Successfully processed {len(listings)} plan cards")
            return listings
            
        except Exception as e:
            print(f"[BeazerHomesBrookvillePlanScraper] Error: {e}")
            return []
