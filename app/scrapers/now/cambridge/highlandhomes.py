import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class HighlandHomesCambridgeNowScraper(BaseScraper):
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

    def is_quick_move_in(self, card):
        """Check if this card represents a quick move-in home."""
        # Quick move-in homes have addresses (not plan names) and specific home tags
        home_tag = card.find('span', class_='home-tag')
        home_identifier = card.find('span', class_='homeIdentifier')
        
        if home_identifier:
            identifier_text = home_identifier.get_text(strip=True)
            # If it's an address (contains street number and doesn't end with "Plan"), it's a quick move-in home
            if re.search(r'^\d+\s+[A-Za-z\s]+(?:Court|Street|Avenue|Drive|Lane|Boulevard|Way|Place|Circle)', identifier_text):
                return True
        
        # Also check for specific tags that indicate quick move-in homes
        if home_tag:
            tag_text = home_tag.get_text(strip=True)
            if 'Complete' in tag_text or 'Est. Completion' in tag_text:
                return True
        
        return False

    def is_floor_plan(self, card):
        """Check if this card represents a floor plan."""
        # Floor plans have "Starting at" text and plan names ending with "Plan"
        starting_at = card.find('span', class_='homeStartingAt')
        home_identifier = card.find('span', class_='homeIdentifier')
        
        if starting_at and home_identifier:
            identifier_text = home_identifier.get_text(strip=True)
            # If it ends with "Plan", it's a floor plan
            if identifier_text.endswith('Plan'):
                return True
        
        return False

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[HighlandHomesCambridgeNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[HighlandHomesCambridgeNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[HighlandHomesCambridgeNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all home containers (both quick move-in and floor plans)
            home_containers = soup.find_all('a', class_='home-container')
            print(f"[HighlandHomesCambridgeNowScraper] Found {len(home_containers)} home containers")
            
            # Also look for floor plans in the plans card-grid section
            plans_section = soup.find('div', class_='plans card-grid')
            if plans_section:
                plan_containers = plans_section.find_all('a', class_='home-container homePlan')
                print(f"[HighlandHomesCambridgeNowScraper] Found {len(plan_containers)} additional plan containers")
                home_containers.extend(plan_containers)
            
            print(f"[HighlandHomesCambridgeNowScraper] Total containers to process: {len(home_containers)}")
            
            for idx, container in enumerate(home_containers):
                try:
                    print(f"[HighlandHomesCambridgeNowScraper] Processing container {idx+1}")
                    
                    # Debug: Print what we're looking at
                    home_identifier = container.find('span', class_='homeIdentifier')
                    if home_identifier:
                        print(f"[HighlandHomesCambridgeNowScraper] Container {idx+1} identifier: '{home_identifier.get_text(strip=True)}'")
                    
                    # Check if this is a quick move-in home
                    if self.is_quick_move_in(container):
                        print(f"[HighlandHomesCambridgeNowScraper] Processing quick move-in home {idx+1}")
                        
                        # Extract address
                        home_identifier = container.find('span', class_='homeIdentifier')
                        if not home_identifier:
                            print(f"[HighlandHomesCambridgeNowScraper] Skipping container {idx+1}: No home identifier found")
                            continue
                        
                        address = home_identifier.get_text(strip=True)
                        if not address:
                            print(f"[HighlandHomesCambridgeNowScraper] Skipping container {idx+1}: Empty address")
                            continue
                        
                        # Check for duplicate addresses
                        if address in seen_addresses:
                            print(f"[HighlandHomesCambridgeNowScraper] Skipping container {idx+1}: Duplicate address '{address}'")
                            continue
                        
                        seen_addresses.add(address)
                        
                        # Extract price
                        price_span = container.find('span', class_='price')
                        if not price_span:
                            print(f"[HighlandHomesCambridgeNowScraper] Skipping container {idx+1}: No price found")
                            continue
                        
                        current_price = self.parse_price(price_span.get_text())
                        if not current_price:
                            print(f"[HighlandHomesCambridgeNowScraper] Skipping container {idx+1}: No current price found")
                            continue
                        
                        # Extract plan name from homeUpgrades
                        home_upgrades = container.find('p', class_='homeUpgrades')
                        plan_name = ""
                        if home_upgrades:
                            plan_text = home_upgrades.get_text(strip=True)
                            # Extract plan name (e.g., "London Plan with 6 upgrades" -> "London Plan")
                            plan_match = re.search(r'^([A-Za-z\s]+)\s+Plan', plan_text)
                            if plan_match:
                                plan_name = plan_match.group(1).strip()
                        
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
                        
                        # Extract square footage from homeSqFootage
                        home_sqft = container.find('div', class_='homeSqFootage')
                        if home_sqft:
                            numeral = home_sqft.find('span', class_='numeral')
                            if numeral:
                                sqft = self.parse_sqft(numeral.get_text())
                        
                        if not sqft:
                            print(f"[HighlandHomesCambridgeNowScraper] Skipping container {idx+1}: No square footage found")
                            continue
                        
                        # Calculate price per sqft
                        price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                        
                        plan_data = {
                            "price": current_price,
                            "sqft": sqft,
                            "stories": stories or "1",
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name or address,
                            "company": "Highland Homes",
                            "community": "Cambridge",
                            "type": "now",
                            "beds": beds,
                            "baths": baths,
                            "address": address,
                            "original_price": None,
                            "price_cut": ""
                        }
                        
                        print(f"[HighlandHomesCambridgeNowScraper] Quick Move-in Home {idx+1}: {plan_data}")
                        listings.append(plan_data)
                    
                    # Check if this is a floor plan
                    elif self.is_floor_plan(container):
                        print(f"[HighlandHomesCambridgeNowScraper] Processing floor plan {idx+1}")
                        
                        # Extract plan name
                        home_identifier = container.find('span', class_='homeIdentifier')
                        if not home_identifier:
                            print(f"[HighlandHomesCambridgeNowScraper] Skipping container {idx+1}: No home identifier found")
                            continue
                        
                        plan_name = home_identifier.get_text(strip=True)
                        if not plan_name:
                            print(f"[HighlandHomesCambridgeNowScraper] Skipping container {idx+1}: Empty plan name")
                            continue
                        
                        # Check for duplicate plan names
                        if plan_name in seen_plan_names:
                            print(f"[HighlandHomesCambridgeNowScraper] Skipping container {idx+1}: Duplicate plan name '{plan_name}'")
                            continue
                        
                        seen_plan_names.add(plan_name)
                        
                        # For floor plans, also check if it has the homePlan class
                        if 'homePlan' not in container.get('class', []):
                            print(f"[HighlandHomesCambridgeNowScraper] Container {idx+1} appears to be a floor plan but doesn't have homePlan class")
                        
                        # Extract price
                        price_span = container.find('span', class_='price')
                        if not price_span:
                            print(f"[HighlandHomesCambridgeNowScraper] Skipping container {idx+1}: No price found")
                            continue
                        
                        current_price = self.parse_price(price_span.get_text())
                        if not current_price:
                            print(f"[HighlandHomesCambridgeNowScraper] Skipping container {idx+1}: No current price found")
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
                        
                        # For floor plans, square footage might be in homeDetails as "base sq ft"
                        if not sqft:
                            print(f"[HighlandHomesCambridgeNowScraper] Skipping container {idx+1}: No square footage found")
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
                        
                        print(f"[HighlandHomesCambridgeNowScraper] Floor Plan {idx+1}: {plan_data}")
                        listings.append(plan_data)
                    
                    else:
                        print(f"[HighlandHomesCambridgeNowScraper] Container {idx+1}: Unknown type, attempting to determine...")
                        
                        # Try to determine type based on content
                        home_identifier = container.find('span', class_='homeIdentifier')
                        if home_identifier:
                            identifier_text = home_identifier.get_text(strip=True)
                            print(f"[HighlandHomesCambridgeNowScraper] Container {idx+1} identifier: '{identifier_text}'")
                            
                            # If it looks like an address, treat as quick move-in
                            if re.search(r'^\d+\s+[A-Za-z\s]+(?:Court|Street|Avenue|Drive|Lane|Boulevard|Way|Place|Circle)', identifier_text):
                                print(f"[HighlandHomesCambridgeNowScraper] Container {idx+1} appears to be a quick move-in home based on address format")
                                # Process as quick move-in home (you could add the logic here)
                            elif identifier_text.endswith('Plan'):
                                print(f"[HighlandHomesCambridgeNowScraper] Container {idx+1} appears to be a floor plan based on name")
                                # Process as floor plan (you could add the logic here)
                            else:
                                print(f"[HighlandHomesCambridgeNowScraper] Container {idx+1}: Cannot determine type, skipping")
                        
                        continue
                    
                except Exception as e:
                    print(f"[HighlandHomesCambridgeNowScraper] Error processing container {idx+1}: {e}")
                    continue
            
            print(f"[HighlandHomesCambridgeNowScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[HighlandHomesCambridgeNowScraper] Error: {e}")
            return []
