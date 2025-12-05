import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class DRHortonWildflowerRanchPlanScraper(BaseScraper):
    URL = "https://www.drhorton.com/texas/fort-worth/justin/treeline"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract starting price from text."""
        # Handle "Starting in the $409s" format - take the base price
        match = re.search(r'\$(\d+)s?', text)
        if match:
            base_price = int(match.group(1))
            # Convert to full price (e.g., $409s -> $409,000)
            return base_price * 1000
        return None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DRHortonWildflowerRanchPlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DRHortonWildflowerRanchPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[DRHortonWildflowerRanchPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plans = set()  # Track plan names to prevent duplicates
            
            # Find the floorplan section
            floorplan_section = soup.find('div', id='floorplanItems')
            if not floorplan_section:
                print("[DRHortonWildflowerRanchPlanScraper] Could not find floorplan section")
                return []
            
            # Find all plan cards
            plan_cards = floorplan_section.find_all('div', class_='toggle-item')
            print(f"[DRHortonWildflowerRanchPlanScraper] Found {len(plan_cards)} plan cards")
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[DRHortonWildflowerRanchPlanScraper] Processing card {idx+1}")
                    
                    # Extract plan name from h2 element within card-content
                    # First try to find within card-content, then fallback to direct find
                    card_content = card.find('div', class_='card-content')
                    if card_content:
                        plan_name_elem = card_content.find('h2')
                    else:
                        plan_name_elem = card.find('h2')
                    
                    if not plan_name_elem:
                        print(f"[DRHortonWildflowerRanchPlanScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    plan_name = plan_name_elem.get_text(strip=True)
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plans:
                        print(f"[DRHortonWildflowerRanchPlanScraper] Skipping card {idx+1}: Duplicate plan '{plan_name}'")
                        continue
                    
                    seen_plans.add(plan_name)
                    
                    # Extract starting price from h3 element within card-content
                    if card_content:
                        price_elem = card_content.find('h3')
                    else:
                        price_elem = card.find('h3')
                    
                    if not price_elem:
                        print(f"[DRHortonWildflowerRanchPlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    price_text = price_elem.get_text(strip=True)
                    starting_price = self.parse_price(price_text)
                    if not starting_price:
                        print(f"[DRHortonWildflowerRanchPlanScraper] Skipping card {idx+1}: No valid starting price found")
                        continue
                    
                    # Extract property details from p elements with class 'stats'
                    # Search within card-content if available, otherwise search the whole card
                    if card_content:
                        stats_elements = card_content.find_all('p', class_='stats')
                    else:
                        stats_elements = card.find_all('p', class_='stats')
                    beds = ""
                    baths = ""
                    sqft = None
                    stories = "1"  # Default
                    garage = ""
                    
                    for stats_elem in stats_elements:
                        stats_text = stats_elem.get_text(strip=True)
                        
                        # Look for beds/baths/garage pattern
                        if "Bed" in stats_text and "Bath" in stats_text:
                            # Extract beds
                            beds_match = re.search(r'(\d+(?:\.\d+)?)\s*Bed', stats_text)
                            if beds_match:
                                beds = beds_match.group(1)
                            
                            # Extract baths
                            baths_match = re.search(r'(\d+(?:\.\d+)?)\s*Bath', stats_text)
                            if baths_match:
                                baths = baths_match.group(1)
                            
                            # Extract garage
                            garage_match = re.search(r'(\d+)\s*Garage', stats_text)
                            if garage_match:
                                garage = garage_match.group(1)
                        
                        # Look for story/sqft pattern
                        elif "Story" in stats_text and "Sq. Ft." in stats_text:
                            # Extract stories
                            stories_match = re.search(r'(\d+)\s*Story', stats_text)
                            if stories_match:
                                stories = stories_match.group(1)
                            
                            # Extract sqft
                            sqft_match = re.search(r'([\d,]+)\s*Sq\.\s*Ft\.', stats_text)
                            if sqft_match:
                                sqft = self.parse_sqft(sqft_match.group(1))
                    
                    if not sqft:
                        print(f"[DRHortonWildflowerRanchPlanScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                    
                    # Extract plan URL - link wraps the card, so find it as parent or within toggle-item
                    link_elem = card.find_parent('a', class_='CoveoResultLink')
                    if not link_elem:
                        # Fallback: search within the toggle-item for the link
                        link_elem = card.find('a', class_='CoveoResultLink')
                    plan_url = link_elem.get('href') if link_elem else None
                    if plan_url and not plan_url.startswith('http'):
                        plan_url = f"https://www.drhorton.com{plan_url}"
                    
                    plan_data = {
                        "price": starting_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "DR Horton",
                        "community": "Wildflower Ranch",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",  # Plans don't have specific addresses
                        "design_number": plan_name,  # Use plan name as design number
                        "garage": garage,
                        "url": plan_url
                    }
                    
                    print(f"[DRHortonWildflowerRanchPlanScraper] Card {idx+1}: {plan_data['plan_name']} - Starting at ${starting_price:,} - {sqft:,} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[DRHortonWildflowerRanchPlanScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[DRHortonWildflowerRanchPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[DRHortonWildflowerRanchPlanScraper] Error: {e}")
            return []
