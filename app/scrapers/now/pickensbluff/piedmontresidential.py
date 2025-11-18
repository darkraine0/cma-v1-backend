import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class PiedmontResidentialPickensBluffNowScraper(BaseScraper):
    URL = "https://piedmontresidential.com/new-home-communities/homes-dallas-ga-creekside-landing/"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        # Handle both regular prices and strikethrough prices
        if '<strike>' in text:
            # Extract the non-strikethrough price
            match = re.search(r'<span[^>]*>\$([\d,]+)', text)
        else:
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

    def get_status(self, container):
        """Extract the status of the home."""
        status_elem = container.find('div', class_='uk-display-inline-block uk-background-primary')
        if status_elem:
            status_text = status_elem.get_text(strip=True)
            if "Under Construction" in status_text:
                return "under_construction"
            elif "Available" in status_text:
                return "available"
        return "available"

    def get_price_cut(self, container):
        """Extract price cut information if available."""
        price_elem = container.find('p', class_='font15 w700 uk-margin-small uk-text-center')
        if price_elem and '<strike>' in str(price_elem):
            return "price_reduced"
        return ""

    def get_original_price(self, container):
        """Extract original price if there's a price cut."""
        price_elem = container.find('p', class_='font15 w700 uk-margin-small uk-text-center')
        if price_elem and '<strike>' in str(price_elem):
            strike_match = re.search(r'<strike>\$([\d,]+)', str(price_elem))
            return int(strike_match.group(1).replace(",", "")) if strike_match else None
        return None

    def get_lot_number(self, container):
        """Extract lot number from the container."""
        lot_elem = container.find('div', class_='uk-width-expand uk-text-right')
        if lot_elem:
            lot_text = lot_elem.get_text(strip=True)
            lot_match = re.search(r'Lot:\s*(\d+)', lot_text)
            return lot_match.group(1) if lot_match else None
        return None

    def get_ready_date(self, container):
        """Extract ready date from the container."""
        ready_elem = container.find('div', class_='uk-width-expand font8 uk-text-left')
        if ready_elem:
            return ready_elem.get_text(strip=True)
        return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[PiedmontResidentialPickensBluffNowScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            response = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[PiedmontResidentialPickensBluffNowScraper] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[PiedmontResidentialPickensBluffNowScraper] Request failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all home cards
            home_cards = soup.find_all('div', class_='home')
            print(f"[PiedmontResidentialPickensBluffNowScraper] Found {len(home_cards)} home cards")
            
            listings = []
            
            for idx, card in enumerate(home_cards):
                try:
                    # Extract data attributes
                    sqft = card.get('data-sqft')
                    beds = card.get('data-beds')
                    baths = card.get('data-baths')
                    plan_number = card.get('data-plan')
                    home_type = card.get('data-type', '')
                    
                    # Convert sqft to int if it exists
                    if sqft:
                        sqft = int(sqft)
                    
                    # Extract plan name from h2 element
                    plan_name_elem = card.find('h2', class_='uk-text-primary w700 uk-margin-remove')
                    plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else None
                    
                    if not plan_name:
                        print(f"[PiedmontResidentialPickensBluffNowScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    # Extract address
                    address_elem = card.find('div', class_='font7 uk-margin-small-bottom')
                    address = ""
                    if address_elem:
                        # Remove the map marker icon and get just the address text
                        address_text = address_elem.get_text(strip=True)
                        # Remove the map marker icon text
                        address = re.sub(r'^.*?&nbsp;', '', address_text)
                    
                    # Extract price
                    price_elem = card.find('p', class_='font15 w700 uk-margin-small uk-text-center')
                    price_text = str(price_elem) if price_elem else ""
                    price = self.parse_price(price_text)
                    original_price = self.get_original_price(card)
                    
                    if not price:
                        print(f"[PiedmontResidentialPickensBluffNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Get additional details
                    status = self.get_status(card)
                    price_cut = self.get_price_cut(card)
                    lot_number = self.get_lot_number(card)
                    ready_date = self.get_ready_date(card)
                    
                    # Extract property link
                    link_elem = card.find('a', class_='uk-position-cover')
                    property_url = link_elem.get('href') if link_elem else None
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    # Create plan name with lot number if available
                    full_plan_name = f"{plan_name}"
                    if lot_number:
                        full_plan_name += f" - Lot {lot_number}"
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": self.parse_stories(home_type),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": full_plan_name,
                        "company": "Piedmont Residential",
                        "community": "Pickens Bluff",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": original_price,
                        "price_cut": price_cut,
                        "status": status,
                        "url": property_url,
                        "lot_number": lot_number,
                        "ready_date": ready_date,
                        "plan_number": plan_number
                    }
                    
                    print(f"[PiedmontResidentialPickensBluffNowScraper] Property {idx+1}: {plan_data['plan_name']} - ${price:,} - {sqft:,} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[PiedmontResidentialPickensBluffNowScraper] Error processing property {idx+1}: {e}")
                    continue
            
            print(f"[PiedmontResidentialPickensBluffNowScraper] Successfully processed {len(listings)} properties")
            return listings
            
        except Exception as e:
            print(f"[PiedmontResidentialPickensBluffNowScraper] Error: {e}")
            return []
