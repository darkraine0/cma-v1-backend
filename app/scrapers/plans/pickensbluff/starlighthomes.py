import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class StarlightHomesPickensBluffPlanScraper(BaseScraper):
    URL = "https://www.starlighthomes.com/atlanta/mt-tabor-ridge"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, price_element):
        """Extract starting price from price element."""
        # First try to get the total price from data-total-price attribute
        total_price = price_element.get('data-total-price')
        if total_price:
            return int(total_price)
        
        # Fallback to parsing the displayed price
        price_text = price_element.get_text(strip=True)
        match = re.search(r'\$([\d,]+)', price_text)
        return int(match.group(1).replace(",", "")) if match else None

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

    def parse_garage(self, text):
        """Extract garage count from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def get_homes_ready(self, card):
        """Extract homes ready count from neighborhood tag if present."""
        neighborhood_tag = card.find('div', class_='neighborhood__tag')
        if neighborhood_tag:
            tag_text = neighborhood_tag.get_text(strip=True)
            match = re.search(r'(\d+)\s+Homes?\s+Ready', tag_text)
            if match:
                return int(match.group(1))
        return 0

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[StarlightHomesPickensBluffPlanScraper] Fetching URL: {self.URL}")
            
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
            print(f"[StarlightHomesPickensBluffPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[StarlightHomesPickensBluffPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plans = set()  # Track plan names to prevent duplicates
            
            # Find the plan cards container
            cards_container = soup.find('div', class_='js-community-filter__cards')
            if not cards_container:
                print("[StarlightHomesPickensBluffPlanScraper] Could not find plan cards container")
                return []
            
            # Find all plan cards
            plan_cards = cards_container.find_all('div', class_='js-community-filter__card')
            print(f"[StarlightHomesPickensBluffPlanScraper] Found {len(plan_cards)} plan cards")
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[StarlightHomesPickensBluffPlanScraper] Processing card {idx+1}")
                    
                    # Find the plan card div
                    plan_card = card.find('div', class_='plan-card')
                    if not plan_card:
                        print(f"[StarlightHomesPickensBluffPlanScraper] Skipping card {idx+1}: No plan-card found")
                        continue
                    
                    # Extract plan name from heading
                    heading_elem = plan_card.find('div', class_='plan-card__heading')
                    if not heading_elem:
                        print(f"[StarlightHomesPickensBluffPlanScraper] Skipping card {idx+1}: No plan heading found")
                        continue
                    
                    plan_name_link = heading_elem.find('a')
                    if not plan_name_link:
                        print(f"[StarlightHomesPickensBluffPlanScraper] Skipping card {idx+1}: No plan name link found")
                        continue
                    
                    plan_name = plan_name_link.get_text(strip=True)
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plans:
                        print(f"[StarlightHomesPickensBluffPlanScraper] Skipping card {idx+1}: Duplicate plan '{plan_name}'")
                        continue
                    
                    seen_plans.add(plan_name)
                    
                    # Extract price
                    price_elem = plan_card.find('div', class_='price__main')
                    if not price_elem:
                        print(f"[StarlightHomesPickensBluffPlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    starting_price = self.parse_price(price_elem)
                    if not starting_price:
                        print(f"[StarlightHomesPickensBluffPlanScraper] Skipping card {idx+1}: No valid starting price found")
                        continue
                    
                    # Extract specs
                    specs_container = plan_card.find('div', class_='specs')
                    if not specs_container:
                        print(f"[StarlightHomesPickensBluffPlanScraper] Skipping card {idx+1}: No specs found")
                        continue
                    
                    beds = ""
                    baths = ""
                    stories = "1"  # Default
                    garage = ""
                    sqft = None
                    
                    # Find all spec items
                    spec_items = specs_container.find_all('div', class_='specs__item')
                    for spec_item in spec_items:
                        spec_text = spec_item.get_text(strip=True)
                        spec_class = ' '.join(spec_item.get('class', []))
                        
                        if 'specs__item--beds' in spec_class:
                            beds = self.parse_beds(spec_text)
                        elif 'specs__item--baths' in spec_class:
                            baths = self.parse_baths(spec_text)
                        elif 'specs__item--stories' in spec_class:
                            stories = self.parse_stories(spec_text)
                        elif 'specs__item--garage' in spec_class:
                            garage = self.parse_garage(spec_text)
                        elif 'specs__item--area' in spec_class:
                            sqft = self.parse_sqft(spec_text)
                    
                    if not sqft:
                        print(f"[StarlightHomesPickensBluffPlanScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                    
                    # Extract plan URL
                    plan_url = plan_name_link.get('href')
                    if plan_url and not plan_url.startswith('http'):
                        plan_url = f"https://www.starlighthomes.com{plan_url}"
                    
                    # Get homes ready count
                    homes_ready = self.get_homes_ready(plan_card)
                    
                    plan_data = {
                        "price": starting_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Starlight Homes",
                        "community": "Pickens Bluff",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",  # Plans don't have specific addresses
                        "design_number": plan_name,  # Use plan name as design number
                        "garage": garage,
                        "homes_ready": homes_ready,
                        "url": plan_url
                    }
                    
                    print(f"[StarlightHomesPickensBluffPlanScraper] Card {idx+1}: {plan_data['plan_name']} - Starting at ${starting_price:,} - {sqft:,} sqft - {homes_ready} homes ready")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[StarlightHomesPickensBluffPlanScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[StarlightHomesPickensBluffPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[StarlightHomesPickensBluffPlanScraper] Error: {e}")
            return []
