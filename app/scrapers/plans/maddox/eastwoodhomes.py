import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class EastwoodHomesMaddoxPlanScraper(BaseScraper):
    URL = "https://www.eastwoodhomes.com/atlanta/hoschton/twin-lakes"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract starting price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:\+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+(?:\+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[EastwoodHomesMaddoxPlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[EastwoodHomesMaddoxPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[EastwoodHomesMaddoxPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all floor plan cards
            plan_cards = soup.find_all('div', class_='s-card-housing')
            print(f"[EastwoodHomesMaddoxPlanScraper] Found {len(plan_cards)} plan cards")
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[EastwoodHomesMaddoxPlanScraper] Processing card {idx+1}")
                    
                    # Extract plan name
                    plan_name_elem = card.find('p', class_='e-card-caption__heading')
                    if not plan_name_elem:
                        print(f"[EastwoodHomesMaddoxPlanScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    plan_name = plan_name_elem.get_text(strip=True)
                    if not plan_name:
                        print(f"[EastwoodHomesMaddoxPlanScraper] Skipping card {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[EastwoodHomesMaddoxPlanScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract starting price
                    price_elem = card.find('span', class_='s-card-housing__price-tag')
                    if not price_elem:
                        print(f"[EastwoodHomesMaddoxPlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    starting_price = self.parse_price(price_elem.get_text())
                    if not starting_price:
                        print(f"[EastwoodHomesMaddoxPlanScraper] Skipping card {idx+1}: No starting price found")
                        continue
                    
                    # Extract square footage from prominent feature
                    sqft = None
                    prominent_feature = card.find('div', class_='e-card-caption__features__item--prominent')
                    if prominent_feature:
                        sqft_elem = prominent_feature.find('span', class_='e-spec__content')
                        if sqft_elem:
                            sqft = self.parse_sqft(sqft_elem.get_text())
                    
                    if not sqft:
                        print(f"[EastwoodHomesMaddoxPlanScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Extract beds, baths, stories, and garage from specs list
                    beds = ""
                    baths = ""
                    stories = ""
                    garage = ""
                    
                    specs_list = card.find('ul', class_='e-desc-list-specs__list')
                    if specs_list:
                        spec_items = specs_list.find_all('li', class_='e-desc-list-specs__list__item')
                        for item in spec_items:
                            eyebrow_elem = item.find('span', class_='e-spec__eyebrow')
                            content_elem = item.find('span', class_='e-spec__content')
                            
                            if eyebrow_elem and content_elem:
                                eyebrow_text = eyebrow_elem.get_text(strip=True).lower()
                                content_text = content_elem.get_text(strip=True)
                                
                                if 'bedroom' in eyebrow_text:
                                    beds = self.parse_beds(content_text)
                                elif 'full-bath' in eyebrow_text:
                                    baths = self.parse_baths(content_text)
                                elif 'stories' in eyebrow_text:
                                    stories = self.parse_stories(content_text)
                                elif 'garage' in eyebrow_text:
                                    garage = self.parse_garage(content_text)
                    
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
                        "company": "Eastwood Homes",
                        "community": "Maddox",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": ""
                    }
                    
                    print(f"[EastwoodHomesMaddoxPlanScraper] Card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[EastwoodHomesMaddoxPlanScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[EastwoodHomesMaddoxPlanScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[EastwoodHomesMaddoxPlanScraper] Error: {e}")
            return []
