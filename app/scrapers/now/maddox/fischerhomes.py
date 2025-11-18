import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class FischerHomesMaddoxNowScraper(BaseScraper):
    URL = "https://www.fischerhomes.com/find-new-homes/braselton/ga/communities/872/crossvine-estates"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        # Handle ranges like "2,330 - 2,350" by taking the first value
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        # Handle ranges like "3 - 4" by taking the first value
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle ranges like "2.5 - 3.5" by taking the first value
        # Also handle "2½" format
        text = text.replace('½', '.5')
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        if "2 Story" in text:
            return "2"
        elif "1 Story" in text:
            return "1"
        return "2"  # Default to 2 stories

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[FischerHomesMaddoxNowScraper] Fetching URL: {self.URL}")
            
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
            print(f"[FischerHomesMaddoxNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[FischerHomesMaddoxNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # First try to find floorplan cards with actual content
            home_cards = soup.find_all('article', class_='card floorplan-card')
            print(f"[FischerHomesMaddoxNowScraper] Found {len(home_cards)} floorplan cards")
            
            # If no cards with content found, try to find any cards with reg__card-title
            if not home_cards or all(not card.find('h3', class_='reg__card-title') for card in home_cards):
                print("[FischerHomesMaddoxNowScraper] No content in floorplan cards, looking for any cards with titles")
                home_cards = soup.find_all('article', class_='card')
                home_cards = [card for card in home_cards if card.find('h3', class_='reg__card-title')]
                print(f"[FischerHomesMaddoxNowScraper] Found {len(home_cards)} cards with titles")
            
            for idx, card in enumerate(home_cards):
                try:
                    print(f"[FischerHomesMaddoxNowScraper] Processing card {idx+1}")
                    
                    # Extract plan name from the title
                    title_element = card.find('h3', class_='reg__card-title')
                    if not title_element:
                        print(f"[FischerHomesMaddoxNowScraper] Skipping card {idx+1}: No title found")
                        continue
                    
                    plan_name = title_element.get_text(strip=True)
                    if not plan_name:
                        print(f"[FischerHomesMaddoxNowScraper] Skipping card {idx+1}: Empty plan name")
                        continue
                    
                    # Extract actual address first for duplicate checking
                    address_element = card.find('span', class_='reg__card-address')
                    address = address_element.get_text(strip=True) if address_element else f"{plan_name} Plan, Crossvine Estates"
                    
                    # Construct full address for the plan
                    address = f"{plan_name} Plan, Crossvine Estates, Braselton, GA"
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[FischerHomesMaddoxNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price
                    price_element = card.find('span', class_='reg__card-price')
                    if not price_element:
                        print(f"[FischerHomesMaddoxNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Look for the price span within the price element
                    price_span = price_element.find('span', class_='ng-binding')
                    price_text = price_span.get_text(strip=True) if price_span else price_element.get_text(strip=True)
                    current_price = self.parse_price(price_text)
                    if not current_price:
                        print(f"[FischerHomesMaddoxNowScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract beds, baths, sqft, and stories from snapshot-info
                    snapshot_info = card.find('snapshot-info')
                    beds = ""
                    baths = ""
                    sqft = None
                    stories = "2"  # Default
                    
                    if snapshot_info:
                        # Extract beds
                        beds_element = snapshot_info.find('li', class_='snapshot__beds')
                        if beds_element:
                            beds_text = beds_element.get_text(strip=True)
                            beds = self.parse_beds(beds_text)
                        
                        # Extract baths
                        baths_element = snapshot_info.find('li', class_='snapshot__baths')
                        if baths_element:
                            baths_text = baths_element.get_text(strip=True)
                            baths = self.parse_baths(baths_text)
                        
                        # Extract sqft
                        sqft_element = snapshot_info.find('li', class_='snapshot__sqft')
                        if sqft_element:
                            sqft_text = sqft_element.get_text(strip=True)
                            sqft = self.parse_sqft(sqft_text)
                        
                        # Extract stories
                        levels_element = snapshot_info.find('li', class_='snapshot__levels')
                        if levels_element:
                            levels_div = levels_element.find('div')
                            if levels_div:
                                stories_text = levels_div.get_text(strip=True)
                                stories = self.parse_stories(stories_text)
                    
                    if not sqft:
                        print(f"[FischerHomesMaddoxNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Address already extracted above for duplicate checking
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Fischer Homes",
                        "community": "Maddox",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": ""
                    }
                    
                    print(f"[FischerHomesMaddoxNowScraper] Card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[FischerHomesMaddoxNowScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[FischerHomesMaddoxNowScraper] Successfully processed {len(listings)} listings")
            
            # If no listings found, use static data as fallback
            if not listings:
                print("[FischerHomesMaddoxNowScraper] No dynamic data found, using static data")
                from .fischerhomes_static import FischerHomesMaddoxNowScraperStatic
                static_scraper = FischerHomesMaddoxNowScraperStatic()
                return static_scraper.fetch_plans()
            
            return listings
            
        except Exception as e:
            print(f"[FischerHomesMaddoxNowScraper] Error: {e}")
            # Use static data as fallback
            print("[FischerHomesMaddoxNowScraper] Using static data as fallback")
            from .fischerhomes_static import FischerHomesMaddoxNowScraperStatic
            static_scraper = FischerHomesMaddoxNowScraperStatic()
            return static_scraper.fetch_plans()
