import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class BloomFieldHomesMyrtleCreekNowScraper(BaseScraper):
    BASE_URL = "https://www.bloomfieldhomes.com/new-homes/tx/waxahachie/sunrise-at-garden-valley/#available-homes"
    
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
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_cars(self, text):
        """Extract number of car garage from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_status(self, text):
        """Extract status from text."""
        if "move-in ready" in text.lower():
            return "Ready Now"
        elif "available" in text.lower() and "2025" in text:
            return "Under Construction"
        elif "under contract" in text.lower():
            return "Under Contract"
        return "Available"

    def fetch_plans(self) -> List[Dict]:
        """Fetch all available homes from BloomField Homes."""
        listings = []
        
        try:
            response = requests.get(self.BASE_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find property cards with the same structure as Lake Breeze
            property_cards = soup.find_all('div', class_='card spec-card-vertical spec-card oi-map-item')
            
            for card in property_cards:
                try:
                    listing = self.parse_property_card(card)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    print(f"Error parsing property card: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error fetching BloomField Homes data: {e}")
            
        return listings

    def parse_property_card(self, card) -> Dict:
        """Parse individual property card."""
        listing = {
            'company': 'Bloomfield Homes',
            'community': 'Myrtle Creek',
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
        
        # Extract property address
        heading_element = card.find('p', class_='card-heading')
        if heading_element:
            address_link = heading_element.find('a')
            if address_link:
                listing['address'] = address_link.get_text(strip=True)
                listing['plan_name'] = address_link.get_text(strip=True)
                listing['listing_link'] = address_link.get('href', self.BASE_URL)
        
        # Extract community name
        community_element = card.find('a', class_='child-location-link')
        if community_element:
            community_name = community_element.get_text(strip=True)
            # Map the community name to Myrtle Creek
            if 'Sunrise at Garden Valley' in community_name:
                listing['community'] = 'Myrtle Creek'
        
        # Extract floor plan name
        floor_plan_element = card.find('a', class_='plan-link')
        if floor_plan_element:
            floor_plan_name = floor_plan_element.get_text(strip=True)
            listing['plan_name'] = floor_plan_name
            listing['floor_plan_link'] = floor_plan_element.get('href', '')
        
        # Extract current price (look for "Now" price specifically)
        price_container = card.find('div', class_='d-flex justify-content-between align-items-center')
        if price_container:
            # Look for the "Now" price (second card-price element)
            all_price_elements = price_container.find_all('p', class_='card-price')
            if len(all_price_elements) >= 2:
                # Take the second price element (the "Now" price)
                now_price_elem = all_price_elements[1]
                price_text = now_price_elem.get_text(strip=True)
                listing['price'] = self.parse_price(price_text)
        
        # Extract previous price and calculate savings
        prev_price_element = card.find('p', class_='old-price')
        if prev_price_element:
            prev_price_text = prev_price_element.get_text(strip=True)
            original_price = self.parse_price(prev_price_text)
            if original_price and listing['price']:
                listing['original_price'] = original_price
                savings = original_price - listing['price']
                listing['price_cut'] = f"Save: ${savings:,}"
        
        # Extract property details (sqft, beds, baths, garage)
        stats_list = card.find('ul', class_='spec-card-stats')
        if stats_list:
            stat_items = stats_list.find_all('li')
            for item in stat_items:
                stat_value = item.find('p', class_='stat-value')
                stat_label = item.find('p', class_='h6')
                
                if stat_value and stat_label:
                    value_text = stat_value.get_text(strip=True)
                    label_text = stat_label.get_text(strip=True)
                    
                    if 'Square Feet' in label_text:
                        listing['sqft'] = self.parse_sqft(value_text)
                    elif 'Bedrooms' in label_text:
                        listing['beds'] = self.parse_beds(value_text)
                    elif 'Bathrooms' in label_text:
                        listing['baths'] = self.parse_baths(value_text)
                    elif 'Car Garage' in label_text:
                        listing['cars'] = self.parse_cars(value_text)
        
        # Extract status from banners
        banner_element = card.find('div', class_='spec-banners')
        if banner_element:
            banner_text = banner_element.get_text(strip=True)
            listing['status'] = self.parse_status(banner_text)
        
        # Calculate price per sqft
        if listing['price'] and listing['sqft']:
            listing['price_per_sqft'] = round(listing['price'] / listing['sqft'], 2)
        
        # Set community
        listing['community'] = 'Myrtle Creek'
        
        return listing

    def get_company_name(self) -> str:
        """Return company name."""
        return "Bloomfield Homes"

    def get_community_name(self) -> str:
        """Return community name."""
        return "Myrtle Creek"
