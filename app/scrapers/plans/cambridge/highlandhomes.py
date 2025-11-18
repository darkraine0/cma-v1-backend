import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class HighlandHomesCambridgePlanScraper(BaseScraper):
    URL = "https://www.highlandhomes.com/dfw/celina/cambridge-crossing"
    
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
        match = re.search(r'(\d+(?:-\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "3" and "3-4" formats
        match = re.search(r'(\d+(?:-\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[HighlandHomesCambridgePlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[HighlandHomesCambridgePlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[HighlandHomesCambridgePlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all home containers that are floor plans
            home_containers = soup.find_all('a', class_='home-container')
            print(f"[HighlandHomesCambridgePlanScraper] Found {len(home_containers)} home containers")
            
            for idx, container in enumerate(home_containers):
                try:
                    print(f"[HighlandHomesCambridgePlanScraper] Processing container {idx+1}")
                    
                    # Check if this is a floor plan (has "Starting at" text)
                    starting_at = container.find('span', class_='homeStartingAt')
                    if not starting_at:
                        print(f"[HighlandHomesCambridgePlanScraper] Skipping container {idx+1}: Not a floor plan")
                        continue
                    
                    print(f"[HighlandHomesCambridgePlanScraper] Processing floor plan {idx+1}")
                    
                    # Extract plan name
                    home_identifier = container.find('span', class_='homeIdentifier')
                    if not home_identifier:
                        print(f"[HighlandHomesCambridgePlanScraper] Skipping container {idx+1}: No home identifier found")
                        continue
                    
                    plan_name = home_identifier.get_text(strip=True)
                    if not plan_name:
                        print(f"[HighlandHomesCambridgePlanScraper] Skipping container {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[HighlandHomesCambridgePlanScraper] Skipping container {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract price
                    price_span = container.find('span', class_='price')
                    if not price_span:
                        print(f"[HighlandHomesCambridgePlanScraper] Skipping container {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_span.get_text())
                    if not current_price:
                        print(f"[HighlandHomesCambridgePlanScraper] Skipping container {idx+1}: No current price found")
                        continue
                    
                    # Extract beds, baths, stories, and sqft from homeDetails
                    home_details = container.find('div', class_='homeDetails')
                    beds = ""
                    baths = ""
                    stories = ""
                    sqft = None
                    
                    if home_details:
                        detail_items = home_details.find_all('div', class_='homeDetailItem')
                        for item in detail_items:
                            numeral = item.find('span', class_='numeral')
                            label = item.find('span', class_='label')
                            if numeral and label:
                                value = numeral.get_text(strip=True)
                                label_text = label.get_text(strip=True).lower()
                                
                                if 'bed' in label_text:
                                    beds = self.parse_beds(value)
                                elif 'bath' in label_text:
                                    baths = self.parse_baths(value)
                                elif 'stor' in label_text:
                                    stories = self.parse_stories(value)
                                elif 'sq ft' in label_text:
                                    sqft = self.parse_sqft(value)
                    
                    if not sqft:
                        print(f"[HighlandHomesCambridgePlanScraper] Skipping container {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories or "1",
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Highland Homes",
                        "community": "Cambridge",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",
                        "original_price": None,
                        "price_cut": ""
                    }
                    
                    print(f"[HighlandHomesCambridgePlanScraper] Floor Plan {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[HighlandHomesCambridgePlanScraper] Error processing container {idx+1}: {e}")
                    continue
            
            print(f"[HighlandHomesCambridgePlanScraper] Successfully processed {len(listings)} floor plans")
            return listings
            
        except Exception as e:
            print(f"[HighlandHomesCambridgePlanScraper] Error: {e}")
            return []
