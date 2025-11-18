import requests
from bs4 import BeautifulSoup
import re
from ...base import BaseScraper
from typing import List, Dict

class UnionMainElevonPlanScraper(BaseScraper):
    URL = "https://elevontx.com/builder/unionmain-homes/"

    def parse_sqft(self, text):
        match = re.search(r'([\d,]+)\s*sq\.?\s*ft', text, re.IGNORECASE)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_stories(self, text):
        match = re.search(r'(\d+(\.\d+)?)\s*story', text, re.IGNORECASE)
        return float(match.group(1)) if match else None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[UnionMainElevonPlanScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = requests.get(self.URL, headers=headers, timeout=10)
            print(f"[UnionMainElevonPlanScraper] Response status: {resp.status_code}")
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = []
            
            # Try new structure first (e-loop-item) - in case the site was updated
            loop_items = soup.find_all('div', class_='e-loop-item')
            floorplan_items = [item for item in loop_items if 'floorplan' in item.get('class', [])]
            
            if floorplan_items:
                print(f"[UnionMainElevonPlanScraper] Found {len(floorplan_items)} floorplan items (new structure)")
                for idx, item in enumerate(floorplan_items):
                    try:
                        # Extract plan name from h2 element
                        plan_name_elem = item.find('h2', class_='elementor-heading-title')
                        plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else None
                        
                        if not plan_name:
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: No plan name found")
                            continue
                        
                        # Extract price from h4 element
                        h4_elements = item.find_all('h4', class_='elementor-heading-title')
                        price_int = None
                        for element in h4_elements:
                            text = element.get_text(strip=True)
                            if text.startswith('$'):
                                price_int = self.parse_price(text)
                                if price_int:
                                    break
                        
                        if not price_int:
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: No price found")
                            continue
                        
                        # Extract property details (beds, baths, sqft) from grid structure
                        sqft_int = None
                        stories = None
                        
                        # Find the grid container that holds beds/baths/sqft
                        grid_container = item.find('div', class_='e-grid')
                        if grid_container:
                            # Find all containers with the bed/bath/sqft structure
                            detail_containers = grid_container.find_all('div', class_='e-flex', recursive=False)
                            
                            for container in detail_containers:
                                h4s = container.find_all('h4', class_='elementor-heading-title')
                                if len(h4s) >= 2:
                                    value = h4s[0].get_text(strip=True)
                                    label = h4s[1].get_text(strip=True)
                                    
                                    if label == 'SQFT':
                                        sqft_int = self.parse_sqft(value)
                        
                        if not sqft_int:
                            print(f"[UnionMainElevonPlanScraper] Skipping item {idx+1}: No square footage found")
                            continue
                        
                        price_per_sqft = round(price_int / sqft_int, 2) if sqft_int > 0 else None
                        
                        plan_data = {
                            "price": price_int,
                            "sqft": sqft_int,
                            "stories": str(stories) if stories else "2",
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name,
                            "company": "UnionMain Homes",
                            "community": "Elevon",
                            "type": "plan"
                        }
                        print(f"[UnionMainElevonPlanScraper] Item {idx+1}: {plan_data}")
                        listings.append(plan_data)
                    except Exception as e:
                        print(f"[UnionMainElevonPlanScraper] Error processing item {idx+1}: {e}")
                        continue
            else:
                # Fall back to old structure (elevontx.com specific)
                cards = soup.find_all('div', class_="ct-div-block collectable listing")
                print(f"[UnionMainElevonPlanScraper] Found {len(cards)} home cards (old structure).")
                
                for idx, card in enumerate(cards):
                    try:
                        # Extract data from data attributes
                        price = card.get('data-price')
                        sqft = card.get('data-sqft')
                        stories = card.get('data-stories')
                        
                        if not price or not sqft:
                            print(f"[UnionMainElevonPlanScraper] Skipping card {idx+1}: Missing price or sqft.")
                            continue
                        
                        # Get plan name from headline
                        headline = card.find('h4', class_='ct-headline')
                        plan_name = headline.get_text(strip=True) if headline else ""
                        
                        if not plan_name:
                            print(f"[UnionMainElevonPlanScraper] Skipping card {idx+1}: Missing plan name.")
                            continue
                        
                        # Convert to integers
                        price_int = int(price)
                        sqft_int = int(sqft)
                        price_per_sqft = round(price_int / sqft_int, 2) if sqft_int > 0 else None
                        
                        plan_data = {
                            "price": price_int,
                            "sqft": sqft_int,
                            "stories": str(stories),
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name,
                            "company": "UnionMain Homes",
                            "community": "Elevon",
                            "type": "plan"
                        }
                        print(f"[UnionMainElevonPlanScraper] Card {idx+1}: {plan_data}")
                        listings.append(plan_data)
                    except Exception as e:
                        print(f"[UnionMainElevonPlanScraper] Error processing card {idx+1}: {e}")
                        continue
            
            return listings
        except Exception as e:
            print(f"[UnionMainElevonPlanScraper] Error: {e}")
            return [] 