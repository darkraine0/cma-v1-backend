import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class BlueHavenHomesLakeBreezeNowScraper(BaseScraper):
    BASE_URL = "https://bluehavenhomes.com/areas-we-serve/dfw-tx/lakepointe/"
    
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
        return "2"  # Default to 2 stories for most homes

    def get_status(self, container):
        """Extract the status of the home."""
        status_button = container.find('div', class_='btnstatus')
        if status_button:
            button_text = status_button.find('span', class_='elementor-button-text')
            if button_text:
                return button_text.get_text(strip=True)
        return "available"

    def get_price_cut(self, container):
        """Extract price cut information if available."""
        # Look for seller concessions
        concessions_elem = container.find('div', class_='elementor-widget-text-editor')
        if concessions_elem:
            text = concessions_elem.get_text(strip=True)
            if "SELLER CONCESSIONS" in text:
                return text
        return ""

    def extract_property_details(self, container):
        """Extract beds, baths, sqft, and cars from icon lists."""
        details = {
            'beds': None,
            'baths': None,
            'sqft': None,
            'cars': None
        }
        
        # Find all icon list items
        icon_lists = container.find_all('ul', class_='elementor-icon-list-items')
        
        for icon_list in icon_lists:
            items = icon_list.find_all('li', class_='elementor-icon-list-item')
            for item in items:
                text_elem = item.find('span', class_='elementor-icon-list-text')
                if text_elem:
                    text = text_elem.get_text(strip=True)
                    
                    if 'BEDS' in text:
                        details['beds'] = self.parse_beds(text)
                    elif 'BATHS' in text:
                        details['baths'] = self.parse_baths(text)
                    elif 'SQ FT' in text:
                        details['sqft'] = self.parse_sqft(text)
                    elif 'CARS' in text:
                        details['cars'] = self.parse_beds(text)  # Same parsing logic
        
        return details

    def get_page_urls(self):
        """Generate URLs for all pages."""
        urls = [self.BASE_URL]
        
        # Add pagination URLs
        for page in range(2, 5):  # Pages 2-4 based on your provided URLs
            urls.append(f"{self.BASE_URL}?e-page-4ee2c48={page}")
        
        return urls

    def fetch_plans(self) -> List[Dict]:
        try:
            all_listings = []
            urls = self.get_page_urls()
            
            for url_idx, url in enumerate(urls):
                print(f"[BlueHavenHomesLakeBreezeNowScraper] Fetching URL {url_idx + 1}/{len(urls)}: {url}")
                
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                }
                
                response = requests.get(url, headers=headers, timeout=15)
                print(f"[BlueHavenHomesLakeBreezeNowScraper] Response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"[BlueHavenHomesLakeBreezeNowScraper] Request failed with status {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find all property cards (elementor loop items)
                property_cards = soup.find_all('div', class_=re.compile(r'elementor-9387.*e-loop-item'))
                print(f"[BlueHavenHomesLakeBreezeNowScraper] Found {len(property_cards)} property cards on page {url_idx + 1}")
                
                for idx, card in enumerate(property_cards):
                    try:
                        # Extract address from heading elements
                        address_elements = card.find_all('span', class_='elementor-heading-title')
                        address_parts = []
                        
                        for elem in address_elements:
                            text = elem.get_text(strip=True)
                            # Skip price and community elements
                            if not text.startswith('$') and 'Community' not in text:
                                address_parts.append(text)
                        
                        if len(address_parts) < 2:
                            print(f"[BlueHavenHomesLakeBreezeNowScraper] Skipping card {idx+1}: Insufficient address parts")
                            continue
                        
                        street_address = address_parts[0]
                        city_state_zip = address_parts[1] if len(address_parts) > 1 else ""
                        full_address = f"{street_address}, {city_state_zip}"
                        
                        # Extract price from heading elements
                        price = None
                        monthly_payment = None
                        
                        for elem in address_elements:
                            text = elem.get_text(strip=True)
                            if text.startswith('$') and ',' in text:
                                price = self.parse_price(text)
                            elif '/mo' in text:
                                monthly_payment = text
                        
                        if not price:
                            print(f"[BlueHavenHomesLakeBreezeNowScraper] Skipping card {idx+1}: No price found")
                            continue
                        
                        # Extract property details
                        details = self.extract_property_details(card)
                        
                        if not all([details['beds'], details['baths'], details['sqft']]):
                            print(f"[BlueHavenHomesLakeBreezeNowScraper] Skipping card {idx+1}: Missing property details")
                            continue
                        
                        # Extract property link
                        link_elem = card.find('a', href=True)
                        property_url = link_elem.get('href') if link_elem else None
                        
                        # Calculate price per sqft
                        price_per_sqft = round(price / details['sqft'], 2) if details['sqft'] else None
                        
                        # Generate plan name from address
                        plan_name_match = re.search(r'(\d+)\s+([A-Za-z\s]+)', street_address)
                        plan_name = f"{plan_name_match.group(1)} {plan_name_match.group(2).strip()}" if plan_name_match else street_address
                        
                        # Get status and price cut
                        status = self.get_status(card)
                        price_cut = self.get_price_cut(card)
                        
                        plan_data = {
                            "price": price,
                            "sqft": details['sqft'],
                            "stories": self.parse_stories(""),
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name,
                            "company": "BlueHaven Homes",
                            "community": "Lake Breeze",
                            "type": "now",
                            "beds": details['beds'],
                            "baths": details['baths'],
                            "address": full_address,
                            "original_price": None,
                            "price_cut": price_cut,
                            "status": status,
                            "url": property_url,
                            "monthly_payment": monthly_payment,
                            "cars": details['cars']
                        }
                        
                        print(f"[BlueHavenHomesLakeBreezeNowScraper] Property {idx+1}: {plan_data['plan_name']} - ${price:,} - {details['sqft']:,} sqft")
                        all_listings.append(plan_data)
                        
                    except Exception as e:
                        print(f"[BlueHavenHomesLakeBreezeNowScraper] Error processing property {idx+1}: {e}")
                        continue
            
            print(f"[BlueHavenHomesLakeBreezeNowScraper] Successfully processed {len(all_listings)} properties across all pages")
            return all_listings
            
        except Exception as e:
            print(f"[BlueHavenHomesLakeBreezeNowScraper] Error: {e}")
            return []
