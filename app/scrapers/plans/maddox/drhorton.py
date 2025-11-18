import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from ...price_utils import parse_price_with_thousands
from typing import List, Dict

class DRHortonMaddoxPlanScraper(BaseScraper):
    URL = "https://www.drhorton.com/georgia/atlanta/hoschton/twin-lakes"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)\s*Sq\.?\s*Ft\.?', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract starting price from text."""
        # Use the utility function to handle thousands notation
        return parse_price_with_thousands(text)

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)\s*Bed', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)\s*Bath', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+(?:\.\d+)?)\s*Story', text)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        match = re.search(r'(\d+)\s*Garage', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DRHortonMaddoxPlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DRHortonMaddoxPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[DRHortonMaddoxPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find the floor plan items section
            floorplan_section = soup.find('div', {'id': 'floorplanItems'})
            if not floorplan_section:
                print(f"[DRHortonMaddoxPlanScraper] Floor plan section not found")
                return []
            
            # Find all toggle items (floor plan cards)
            toggle_items = floorplan_section.find_all('div', class_='toggle-item')
            print(f"[DRHortonMaddoxPlanScraper] Found {len(toggle_items)} floor plan items")
            
            for idx, item in enumerate(toggle_items):
                try:
                    print(f"[DRHortonMaddoxPlanScraper] Processing item {idx+1}")
                    
                    # Find the card content
                    card = item.find('div', class_='card')
                    if not card:
                        print(f"[DRHortonMaddoxPlanScraper] Skipping item {idx+1}: No card found")
                        continue
                    
                    card_content = card.find('div', class_='card-content')
                    if not card_content:
                        print(f"[DRHortonMaddoxPlanScraper] Skipping item {idx+1}: No card content found")
                        continue
                    
                    # Extract plan name
                    plan_name_h2 = card_content.find('h2', class_='pr-case')
                    if not plan_name_h2:
                        print(f"[DRHortonMaddoxPlanScraper] Skipping item {idx+1}: No plan name found")
                        continue
                    
                    plan_name = plan_name_h2.get_text(strip=True)
                    if not plan_name:
                        print(f"[DRHortonMaddoxPlanScraper] Skipping item {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[DRHortonMaddoxPlanScraper] Skipping item {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract starting price
                    price_h3 = card_content.find('h3')
                    if not price_h3:
                        print(f"[DRHortonMaddoxPlanScraper] Skipping item {idx+1}: No price found")
                        continue
                    
                    starting_price = self.parse_price(price_h3.get_text())
                    if not starting_price:
                        print(f"[DRHortonMaddoxPlanScraper] Skipping item {idx+1}: No starting price found")
                        continue
                    
                    # Extract stats from p tags
                    stats_p_tags = card_content.find_all('p', class_='stats')
                    beds = ""
                    baths = ""
                    garage = ""
                    stories = ""
                    sqft = None
                    
                    for p_tag in stats_p_tags:
                        text = p_tag.get_text(" ", strip=True)
                        
                        # Extract beds
                        beds_match = self.parse_beds(text)
                        if beds_match:
                            beds = beds_match
                        
                        # Extract baths
                        baths_match = self.parse_baths(text)
                        if baths_match:
                            baths = baths_match
                        
                        # Extract garage
                        garage_match = self.parse_garage(text)
                        if garage_match:
                            garage = garage_match
                        
                        # Extract stories
                        stories_match = self.parse_stories(text)
                        if stories_match:
                            stories = stories_match
                        
                        # Extract square footage
                        sqft_match = self.parse_sqft(text)
                        if sqft_match:
                            sqft = sqft_match
                    
                    if not sqft:
                        print(f"[DRHortonMaddoxPlanScraper] Skipping item {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                    
                    # Extract address (same as plan name for floor plans)
                    address = plan_name
                    
                    plan_data = {
                        "price": starting_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "DR Horton",
                        "community": "Maddox",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": ""
                    }
                    
                    print(f"[DRHortonMaddoxPlanScraper] Item {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[DRHortonMaddoxPlanScraper] Error processing item {idx+1}: {e}")
                    continue
            
            print(f"[DRHortonMaddoxPlanScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[DRHortonMaddoxPlanScraper] Error: {e}")
            return []

