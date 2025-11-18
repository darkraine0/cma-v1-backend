import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class TrophySignatureHomesLakeBreezeNowScraper(BaseScraper):
    BASE_URL = "https://trophysignaturehomes.com/communities/dallas-ft-worth/lavon/lakepointe/homes"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_monthly_payment(self, text):
        """Extract monthly payment from text."""
        match = re.search(r'As low as.*?\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_status(self, text):
        """Extract status from text."""
        if "now" in text.lower():
            return "Ready Now"
        elif "completion" in text.lower() or "est" in text.lower():
            return "Under Construction"
        return "Available"

    def fetch_plans(self) -> List[Dict]:
        """Fetch all available homes from Trophy Signature Homes."""
        listings = []
        
        try:
            response = requests.get(self.BASE_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all property cards
            property_cards = soup.find_all('div', class_='card_wrapper px-0')
            
            for card in property_cards:
                try:
                    listing = self.parse_property_card(card)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    print(f"Error parsing property card: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error fetching Trophy Signature Homes data: {e}")
            
        return listings

    def parse_property_card(self, card) -> Dict:
        """Parse individual property card."""
        listing = {
            'company': 'Trophy Signature Homes',
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
            'type': 'now',
            'original_price': None,
            'price_cut': ''
        }
        
        # Extract property address and location
        title_element = card.find('a', class_='HomeCard_title')
        if title_element:
            address_text = title_element.get_text(strip=True)
            # Split address and location
            lines = address_text.split('\n')
            if len(lines) >= 2:
                listing['address'] = lines[0].strip()
                listing['plan_name'] = lines[0].strip()
            else:
                listing['address'] = address_text
                listing['plan_name'] = address_text
        
        # Extract current price
        current_price_element = card.find('div', class_='Current_price')
        if current_price_element:
            price_text = current_price_element.get_text(strip=True)
            listing['price'] = self.parse_price(price_text)
        
        # Extract previous price and calculate savings
        prev_price_element = card.find('div', class_='Prev_price')
        if prev_price_element:
            prev_price_text = prev_price_element.get_text(strip=True)
            original_price = self.parse_price(prev_price_text)
            if original_price and listing['price']:
                listing['original_price'] = original_price
                savings = original_price - listing['price']
                listing['price_cut'] = f"Save: ${savings:,}"
        
        # Extract monthly payment
        mortgage_element = card.find('div', class_='HomeDetailHeader_mortgageComp')
        if mortgage_element:
            mortgage_text = mortgage_element.get_text(strip=True)
            monthly_payment = self.parse_monthly_payment(mortgage_text)
            if monthly_payment:
                listing['monthly_payment'] = f"${monthly_payment:,}/mo"
        
        # Extract property details (beds, baths, sqft)
        details_list = card.find('ul', class_='HomeCard_list')
        if details_list:
            detail_items = details_list.find_all('li')
            for item in detail_items:
                item_text = item.get_text(strip=True)
                
                if 'Beds' in item_text:
                    listing['beds'] = self.parse_beds(item_text)
                elif 'Baths' in item_text:
                    listing['baths'] = self.parse_baths(item_text)
                elif 'SQ FT' in item_text:
                    listing['sqft'] = self.parse_sqft(item_text)
                elif 'Available Date:' in item_text or 'Est Completion Date:' in item_text:
                    status_text = item_text.replace('Available Date:', '').replace('Est Completion Date:', '').strip()
                    listing['status'] = self.parse_status(status_text)
        
        # Extract floor plan name
        floor_plan_element = card.find('a', href=lambda x: x and '/plan/' in x)
        if floor_plan_element:
            floor_plan_name = floor_plan_element.get_text(strip=True)
            listing['plan_name'] = f"{floor_plan_name} Floor Plan"
            listing['floor_plan_link'] = floor_plan_element.get('href', '')
        
        # Extract detail link
        detail_link = card.find('a', class_='HomeCard_detailsBtn')
        if detail_link:
            listing['listing_link'] = detail_link.get('href', self.BASE_URL)
        
        # Calculate price per sqft
        if listing['price'] and listing['sqft']:
            listing['price_per_sqft'] = round(listing['price'] / listing['sqft'], 2)
        
        # Set community
        listing['community'] = 'Lake Breeze'
        
        return listing

    def get_company_name(self) -> str:
        """Return company name."""
        return "Trophy Signature Homes"

    def get_community_name(self) -> str:
        """Return community name."""
        return "Lake Breeze"
