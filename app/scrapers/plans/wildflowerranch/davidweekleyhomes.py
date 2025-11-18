import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class DavidWeekleyHomesWildflowerRanchPlanScraper(BaseScraper):
    URL = "https://www.davidweekleyhomes.com/new-homes/tx/dallas-ft-worth/justin/treeline"
    
    def parse_price(self, text):
        """Extract price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_sqft(self, text):
        """Extract square footage from text."""
        # Handle ranges like "2484 - 2495" by taking the first number
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
        return str(match.group(1)) if match else "1"

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        # Handle ranges like "2 - 3" by taking the first number
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plans = set()  # Track plan names to prevent duplicates
            
            # Find the floor-plans section
            floor_plans = soup.find('div', class_='floor-plans')
            if not floor_plans:
                print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Floor plans section not found")
                return []
            
            # Find all plan cards in the floor plans section
            plan_cards = floor_plans.find_all('div', class_='plan-card')
            print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Found {len(plan_cards)} plan cards")
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Processing card {idx+1}")
                    
                    # Extract plan title
                    plan_title = card.find('h2', class_='plan-title')
                    if not plan_title:
                        print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Skipping card {idx+1}: No plan title found")
                        continue
                    
                    plan_name = plan_title.get_text(strip=True)
                    if not plan_name:
                        print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Skipping card {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plans:
                        print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plans.add(plan_name)
                    
                    # Extract price (look for "From: $XXX" format)
                    price_elements = card.find_all('h4', class_='card-black')
                    current_price = None
                    for element in price_elements:
                        text = element.get_text(strip=True)
                        if text.startswith('From:'):
                            current_price = self.parse_price(text)
                            break
                    
                    if not current_price:
                        print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract square footage
                    sqft = None
                    for element in price_elements:
                        text = element.get_text(strip=True)
                        if 'Sq. Ft:' in text:
                            sqft = self.parse_sqft(text)
                            break
                    
                    if not sqft:
                        print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Extract beds, baths, stories, and garage from second-level properties
                    second_level = card.find('div', class_='second-level-properties')
                    beds = ""
                    baths = ""
                    stories = "1"
                    garage = ""
                    
                    if second_level:
                        features = second_level.find_all('div', class_='feature')
                        for feature in features:
                            title = feature.find('div', class_='title')
                            value = feature.find('div', class_='value')
                            
                            if title and value:
                                title_text = title.get_text(strip=True).lower()
                                value_text = value.get_text(strip=True)
                                
                                if 'bedroom' in title_text:
                                    beds = self.parse_beds(value_text)
                                elif 'full bath' in title_text:
                                    baths = self.parse_baths(value_text)
                                elif 'story' in title_text or 'stories' in title_text:
                                    stories = self.parse_stories(value_text)
                                elif 'garage' in title_text:
                                    garage = self.parse_garage(value_text)
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "David Weekley Homes",
                        "community": "Wildflower Ranch",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",
                        "original_price": None,
                        "price_cut": "",
                        "floor_plan_link": ""
                    }
                    
                    print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[DavidWeekleyHomesWildflowerRanchPlanScraper] Error: {e}")
            return []

    def get_company_name(self) -> str:
        """Return company name."""
        return "David Weekley Homes"

    def get_community_name(self) -> str:
        """Return community name."""
        return "Wildflower Ranch"
