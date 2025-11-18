import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class PulteWildflowerRanchNowScraper(BaseScraper):
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

    def get_status(self, container):
        """Extract the status of the home."""
        container_text = container.get_text().lower()
        if "sold" in container_text:
            return "sold"
        elif "available" in container_text or "move-in" in container_text:
            return "available"
        return "available"

    def get_plan_number(self, container):
        """Extract plan number from the container."""
        container_text = container.get_text()
        plan_match = re.search(r'plan\s*(\d+)', container_text, re.IGNORECASE)
        return plan_match.group(1) if plan_match else None

    def get_mls_number(self, container):
        """Extract MLS number if available."""
        container_text = container.get_text()
        mls_match = re.search(r'mls[:\s]*(\d+)', container_text, re.IGNORECASE)
        return mls_match.group(1) if mls_match else None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[PulteWildflowerRanchNowScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            response = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[PulteWildflowerRanchNowScraper] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[PulteWildflowerRanchNowScraper] Request failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all QMI (Quick Move-In) cards using the correct CSS classes
            home_cards = soup.find_all('div', class_=re.compile(r'.*QMIGridCard.*'))
            
            print(f"[PulteWildflowerRanchNowScraper] Found {len(home_cards)} QMI home cards")
            
            listings = []
            
            for idx, card in enumerate(home_cards):
                try:
                    # Extract plan name from QMIGridCard__plan-name
                    plan_name_elem = card.find('div', class_='QMIGridCard__plan-name')
                    plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else None
                    
                    if not plan_name:
                        print(f"[PulteWildflowerRanchNowScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    # Extract address from the card text (look for street address pattern)
                    card_text = card.get_text()
                    address_match = re.search(r'(\d+\s+[A-Za-z\s]+(?:Lane|Street|Avenue|Drive|Road|Way|Court|Place|Circle|Trail))', card_text)
                    address = address_match.group(1) if address_match else f"{plan_name} - Wildflower Ranch"
                    
                    # Extract price from QMIGridCard__price
                    price_elem = card.find('div', class_='QMIGridCard__price')
                    price_text = price_elem.get_text(strip=True) if price_elem else ""
                    price = self.parse_price(price_text)
                    
                    if not price:
                        print(f"[PulteWildflowerRanchNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract property details from the card text
                    
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
                        print(f"[PulteWildflowerRanchNowScraper] Skipping card {idx+1}: Missing property details (beds: {beds}, baths: {baths}, sqft: {sqft})")
                        continue
                    
                    # Get additional details
                    status = self.get_status(card)
                    plan_number = self.get_plan_number(card)
                    mls_number = self.get_mls_number(card)
                    
                    # Extract property link if available
                    link_elem = card.find('a', href=True)
                    property_url = link_elem.get('href') if link_elem else None
                    if property_url and not property_url.startswith('http'):
                        property_url = f"https://www.pulte.com{property_url}"
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    # Create plan name with address
                    full_plan_name = f"{plan_name} - {address}"
                    if plan_number:
                        full_plan_name += f" (Plan {plan_number})"
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": full_plan_name,
                        "company": "Pulte",
                        "community": "Wildflower Ranch",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "status": status,
                        "url": property_url,
                        "plan_number": plan_number,
                        "mls_number": mls_number
                    }
                    
                    print(f"[PulteWildflowerRanchNowScraper] Property {idx+1}: {plan_data['plan_name']} - ${price:,} - {sqft:,} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[PulteWildflowerRanchNowScraper] Error processing property {idx+1}: {e}")
                    continue
            
            print(f"[PulteWildflowerRanchNowScraper] Successfully processed {len(listings)} properties")
            return listings
            
        except Exception as e:
            print(f"[PulteWildflowerRanchNowScraper] Error: {e}")
            return []
