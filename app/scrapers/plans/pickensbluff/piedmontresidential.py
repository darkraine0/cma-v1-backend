import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class PiedmontResidentialPickensBluffPlanScraper(BaseScraper):
    URL = "https://piedmontresidential.com/new-home-communities/homes-dallas-ga-creekside-landing/"
    
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
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        if "2 Story" in text:
            return "2"
        elif "Single Story" in text:
            return "1"
        return "2"  # Default to 2 stories

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[PiedmontResidentialPickensBluffPlanScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            response = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[PiedmontResidentialPickensBluffPlanScraper] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[PiedmontResidentialPickensBluffNowScraper] Request failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all plan cards
            plan_cards = soup.find_all('div', class_='plan')
            print(f"[PiedmontResidentialPickensBluffPlanScraper] Found {len(plan_cards)} plan cards")
            
            listings = []
            
            for idx, card in enumerate(plan_cards):
                try:
                    # Extract data attributes
                    sqft = card.get('data-sqft')
                    beds = card.get('data-beds')
                    baths = card.get('data-baths')
                    plan_type = card.get('data-type', '')
                    
                    # Convert sqft to int if it exists
                    if sqft:
                        sqft = int(sqft)
                    
                    # Extract plan name from h3 element
                    plan_name_elem = card.find('h3', class_='uk-text-primary uk-text-center font15 w700 uk-margin-small')
                    plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else None
                    
                    if not plan_name:
                        print(f"[PiedmontResidentialPickensBluffPlanScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    # Extract price from the "starting from" section
                    price_elem = card.find('span', class_='uk-text-secondary w700 font12')
                    price_text = price_elem.get_text(strip=True) if price_elem else ""
                    price = self.parse_price(price_text)
                    
                    if not price:
                        print(f"[PiedmontResidentialPickensBluffPlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract plan link
                    link_elem = card.find('a', class_='uk-position-cover')
                    plan_url = link_elem.get('href') if link_elem else None
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": self.parse_stories(plan_type),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Piedmont Residential",
                        "community": "Pickens Bluff",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",  # Plans don't have addresses
                        "design_number": plan_name,  # Use plan name as design number
                        "url": plan_url,
                        "plan_type": plan_type
                    }
                    
                    print(f"[PiedmontResidentialPickensBluffPlanScraper] Plan {idx+1}: {plan_data['plan_name']} - ${price:,} - {sqft:,} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[PiedmontResidentialPickensBluffPlanScraper] Error processing plan {idx+1}: {e}")
                    continue
            
            print(f"[PiedmontResidentialPickensBluffPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[PiedmontResidentialPickensBluffPlanScraper] Error: {e}")
            return []
