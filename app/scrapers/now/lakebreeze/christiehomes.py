import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class ChristieHomesLakeBreezeNowScraper(BaseScraper):
    BASE_URL = "https://www.christiehomes.net/copy-of-available-homes-1"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'(\d+(?:,\d+)?)\s*sq\.ft', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text."""
        if "pending" in text.lower():
            return None
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)\s*Bed', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)\s*Bath', text)
        return str(match.group(1)) if match else ""

    def parse_status(self, text):
        """Extract status from text."""
        if "ready now" in text.lower():
            return "Ready Now"
        elif "pending" in text.lower():
            return "Pending"
        return "Available"

    def fetch_plans(self) -> List[Dict]:
        """Fetch all available homes from Christie Homes."""
        listings = []
        
        try:
            response = requests.get(self.BASE_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all property cards
            property_cards = soup.find_all('div', class_='comp-m797swba YzqVVZ wixui-repeater__item')
            
            for card in property_cards:
                try:
                    listing = self.parse_property_card(card)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    print(f"Error parsing property card: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error fetching Christie Homes data: {e}")
            
        return listings

    def parse_property_card(self, card) -> Dict:
        """Parse individual property card."""
        listing = {
            'company': 'Christie Homes',
            'community': 'Lake Breeze',
            'plan_name': '',
            'address': '',
            'price': None,
            'sqft': None,
            'stories': '1',  # Default to 1 story for single-family homes
            'price_per_sqft': None,
            'beds': '',
            'baths': '',
            'cars': '',
            'status': '',
            'monthly_payment': '',
            'concessions': '',
            'floor_plan_link': '',
            'listing_link': self.BASE_URL,
            'type': 'now'
        }
        
        # Extract property title/name
        title_element = card.find('div', class_='comp-m797swbm19')
        if title_element:
            title_text = title_element.get_text(strip=True)
            # Extract address from title (e.g., "775 Water View - Ready Now")
            if ' - ' in title_text:
                address_part = title_text.split(' - ')[0]
                listing['address'] = address_part
                listing['plan_name'] = address_part
            else:
                listing['plan_name'] = title_text
                listing['address'] = title_text
        
        # Extract price
        price_element = card.find('div', class_='comp-m797swbn5')
        if price_element:
            price_text = price_element.get_text(strip=True)
            listing['price'] = self.parse_price(price_text)
            if listing['price'] is None and "pending" in price_text.lower():
                listing['status'] = "Pending"
        
        # Extract property details (floor plan, sqft, beds/baths)
        details_element = card.find('div', class_='comp-m797swbo6')
        if details_element:
            details_text = details_element.get_text(strip=True)
            
            # Extract floor plan name
            floor_plan_match = re.search(r'The\s+(\w+)\s+Floor\s+Plan', details_text)
            if floor_plan_match:
                listing['plan_name'] = f"{floor_plan_match.group(1)} Floor Plan"
            
            # Extract square footage
            listing['sqft'] = self.parse_sqft(details_text)
            
            # Extract beds and baths
            listing['beds'] = self.parse_beds(details_text)
            listing['baths'] = self.parse_baths(details_text)
        
        # Extract floor plan link
        floor_plan_link = card.find('a', {'data-testid': 'linkElement'})
        if floor_plan_link and 'href' in floor_plan_link.attrs:
            listing['floor_plan_link'] = floor_plan_link['href']
        
        # Set status if not already set
        if not listing['status']:
            listing['status'] = self.parse_status(listing['plan_name'])
        
        # Calculate price per sqft
        if listing['price'] and listing['sqft']:
            listing['price_per_sqft'] = round(listing['price'] / listing['sqft'], 2)
        
        # Set community
        listing['community'] = 'Lake Breeze'
        
        return listing

    def get_company_name(self) -> str:
        """Return company name."""
        return "Christie Homes"

    def get_community_name(self) -> str:
        """Return community name."""
        return "Lake Breeze"
