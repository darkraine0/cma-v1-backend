import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class PulteWildflowerRanchPlanScraper(BaseScraper):
    URL = "https://www.pulte.com/homes/texas/dallas/justin/treeline-211384#"
    
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
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[PulteWildflowerRanchPlanScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            response = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[PulteWildflowerRanchPlanScraper] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[PulteWildflowerRanchPlanScraper] Request failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all plan cards using the correct CSS classes
            plan_cards = soup.find_all('div', class_=re.compile(r'.*PlanGridCard.*'))
            
            print(f"[PulteWildflowerRanchPlanScraper] Found {len(plan_cards)} plan cards")
            
            listings = []
            
            for idx, card in enumerate(plan_cards):
                try:
                    # Extract plan name from PlanGridCard__plan-name
                    plan_name_elem = card.find('div', class_='PlanGridCard__plan-name')
                    plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else None
                    
                    if not plan_name:
                        print(f"[PulteWildflowerRanchPlanScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    # Extract price from PlanGridCard__price
                    price_elem = card.find('div', class_='PlanGridCard__price')
                    price_text = price_elem.get_text(strip=True) if price_elem else ""
                    price = self.parse_price(price_text)
                    
                    if not price:
                        print(f"[PulteWildflowerRanchPlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract property details from the card text
                    card_text = card.get_text()
                    
                    # Look for beds
                    beds_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bed|bedroom)', card_text, re.IGNORECASE)
                    beds = beds_match.group(1) if beds_match else None
                    
                    # Look for baths
                    baths_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|bathroom)', card_text, re.IGNORECASE)
                    baths = baths_match.group(1) if baths_match else None
                    
                    # Look for sqft
                    sqft_match = re.search(r'([\d,]+)\s*(?:sq\.?\s*ft|square\s*feet)', card_text, re.IGNORECASE)
                    sqft = self.parse_sqft(sqft_match.group(1)) if sqft_match else None
                    
                    # Look for stories
                    stories_match = re.search(r'(\d+)\s*(?:story|stories)', card_text, re.IGNORECASE)
                    stories = stories_match.group(1) if stories_match else "1"  # Default to 1 story
                    
                    # Skip if missing essential details
                    if not all([beds, baths, sqft]):
                        print(f"[PulteWildflowerRanchPlanScraper] Skipping card {idx+1}: Missing property details (beds: {beds}, baths: {baths}, sqft: {sqft})")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    # Extract plan link if available
                    link_elem = card.find('a', href=True)
                    plan_url = link_elem.get('href') if link_elem else None
                    if plan_url and not plan_url.startswith('http'):
                        plan_url = f"https://www.pulte.com{plan_url}"
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Pulte",
                        "community": "Wildflower Ranch",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",  # Plans don't have addresses
                        "design_number": plan_name,  # Use plan name as design number
                        "url": plan_url
                    }
                    
                    print(f"[PulteWildflowerRanchPlanScraper] Plan {idx+1}: {plan_data['plan_name']} - ${price:,} - {sqft:,} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[PulteWildflowerRanchPlanScraper] Error processing plan {idx+1}: {e}")
                    continue
            
            print(f"[PulteWildflowerRanchPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[PulteWildflowerRanchPlanScraper] Error: {e}")
            return []
