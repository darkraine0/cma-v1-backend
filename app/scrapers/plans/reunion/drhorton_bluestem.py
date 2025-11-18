import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class DRHortonBluestemPlanScraper(BaseScraper):
    URL = "https://www.drhorton.com/texas/fort-worth/rhome/bluestem"
    
    def parse_price(self, text):
        """Extract price from text like 'Starting in the $349s'."""
        # Extract the number from "Starting in the $349s"
        match = re.search(r'\$(\d+)s', text)
        if match:
            # Convert to full price (e.g., $349s -> $349,000)
            price_str = match.group(1) + "000"
            return int(price_str)
        return None

    def parse_sqft(self, text):
        """Extract square footage from text."""
        # Remove commas and extract number
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DRHortonBluestemPlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DRHortonBluestemPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[DRHortonBluestemPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plans = set()  # Track plan names to prevent duplicates
            
            # Find the floorplan items container
            floorplan_container = soup.find('div', id='floorplanItems')
            if not floorplan_container:
                print(f"[DRHortonBluestemPlanScraper] No floorplan container found")
                return []
            
            # Find all toggle items (floor plans)
            toggle_items = floorplan_container.find_all('div', class_='toggle-item')
            print(f"[DRHortonBluestemPlanScraper] Found {len(toggle_items)} toggle items")
            
            for idx, item in enumerate(toggle_items):
                try:
                    print(f"[DRHortonBluestemPlanScraper] Processing item {idx+1}")
                    
                    # Extract plan name from h2 element
                    plan_element = item.find('h2', class_='pr-case')
                    if not plan_element:
                        print(f"[DRHortonBluestemPlanScraper] Skipping item {idx+1}: No plan name found")
                        continue
                    
                    plan_name = plan_element.get_text(strip=True)
                    if not plan_name:
                        print(f"[DRHortonBluestemPlanScraper] Skipping item {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plans:
                        print(f"[DRHortonBluestemPlanScraper] Skipping item {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plans.add(plan_name)
                    
                    # Extract price from h3 element
                    price_element = item.find('h3')
                    if not price_element:
                        print(f"[DRHortonBluestemPlanScraper] Skipping item {idx+1}: No price found")
                        continue
                    
                    price_text = price_element.get_text(strip=True)
                    current_price = self.parse_price(price_text)
                    if not current_price:
                        print(f"[DRHortonBluestemPlanScraper] Skipping item {idx+1}: Could not parse price from '{price_text}'")
                        continue
                    
                    # Extract stats from p elements with class 'stats'
                    stats_elements = item.find_all('p', class_='stats')
                    beds = ""
                    baths = ""
                    garage = ""
                    stories = ""
                    sqft = None
                    
                    for stats_element in stats_elements:
                        stats_text = stats_element.get_text(strip=True)
                        
                        # Parse the stats text which contains multiple values separated by |
                        # Format: "4 Bed | 2 Bath | 2 Garage" and "1 Story | 1,662 Sq. Ft."
                        parts = [part.strip() for part in stats_text.split('|')]
                        
                        for part in parts:
                            if 'Bed' in part:
                                beds = self.parse_beds(part)
                            elif 'Bath' in part:
                                baths = self.parse_baths(part)
                            elif 'Garage' in part:
                                garage = self.parse_garage(part)
                            elif 'Story' in part:
                                stories = self.parse_stories(part)
                            elif 'Sq. Ft.' in part:
                                sqft = self.parse_sqft(part)
                    
                    if not sqft:
                        print(f"[DRHortonBluestemPlanScraper] Skipping item {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "DR Horton",
                        "community": "Reunion",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "garage": garage,
                        "address": "",
                        "original_price": None,
                        "price_cut": "",
                        "floor_plan_link": ""
                    }
                    
                    print(f"[DRHortonBluestemPlanScraper] Item {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[DRHortonBluestemPlanScraper] Error processing item {idx+1}: {e}")
                    continue
            
            print(f"[DRHortonBluestemPlanScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[DRHortonBluestemPlanScraper] Error: {e}")
            return []

    def get_company_name(self) -> str:
        """Return company name."""
        return "DR Horton"

    def get_community_name(self) -> str:
        """Return community name."""
        return "Reunion"
