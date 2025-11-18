import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class BlueHavenHomesLakeBreezePlanScraper(BaseScraper):
    BASE_URL = "https://bluehavenhomes.com/areas-we-serve/dfw-tx/lakepointe/"
    
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
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        return "2"  # Default to 2 stories for most homes

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
        
        # Add pagination URLs for plans
        urls.append(f"{self.BASE_URL}?e-page-8128520=2")
        
        return urls

    def fetch_plans(self) -> List[Dict]:
        try:
            all_listings = []
            urls = self.get_page_urls()
            
            for url_idx, url in enumerate(urls):
                print(f"[BlueHavenHomesLakeBreezePlanScraper] Fetching URL {url_idx + 1}/{len(urls)}: {url}")
                
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                }
                
                response = requests.get(url, headers=headers, timeout=15)
                print(f"[BlueHavenHomesLakeBreezePlanScraper] Response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"[BlueHavenHomesLakeBreezePlanScraper] Request failed with status {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find all plan cards (elementor loop items with floor-plans type)
                plan_cards = soup.find_all('div', class_=re.compile(r'elementor-7727.*e-loop-item'))
                print(f"[BlueHavenHomesLakeBreezePlanScraper] Found {len(plan_cards)} plan cards on page {url_idx + 1}")
                
                for idx, card in enumerate(plan_cards):
                    try:
                        # Extract plan name from heading elements
                        plan_name_elem = card.find('span', class_='elementor-heading-title')
                        plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else None
                        
                        if not plan_name:
                            print(f"[BlueHavenHomesLakeBreezePlanScraper] Skipping card {idx+1}: No plan name found")
                            continue
                        
                        # Extract starting price from heading elements
                        price_elements = card.find_all('span', class_='elementor-heading-title')
                        starting_price = None
                        
                        for elem in price_elements:
                            text = elem.get_text(strip=True)
                            if 'STARTING AT' in text:
                                starting_price = self.parse_price(text)
                                break
                        
                        if not starting_price:
                            print(f"[BlueHavenHomesLakeBreezePlanScraper] Skipping card {idx+1}: No starting price found")
                            continue
                        
                        # Extract community from text editor
                        community_elem = card.find('div', class_='elementor-widget-text-editor')
                        community = community_elem.get_text(strip=True) if community_elem else "LakePointe"
                        
                        # Extract property details
                        details = self.extract_property_details(card)
                        
                        if not all([details['beds'], details['baths'], details['sqft']]):
                            print(f"[BlueHavenHomesLakeBreezePlanScraper] Skipping card {idx+1}: Missing property details")
                            continue
                        
                        # Extract plan link
                        link_elem = card.find('a', href=True)
                        plan_url = link_elem.get('href') if link_elem else None
                        
                        # Calculate price per sqft
                        price_per_sqft = round(starting_price / details['sqft'], 2) if details['sqft'] else None
                        
                        plan_data = {
                            "price": starting_price,
                            "sqft": details['sqft'],
                            "stories": self.parse_stories(""),
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name,
                            "company": "BlueHaven Homes",
                            "community": "Lake Breeze",
                            "type": "plan",
                            "beds": details['beds'],
                            "baths": details['baths'],
                            "address": f"{plan_name} Plan",
                            "original_price": None,
                            "price_cut": "",
                            "status": "available",
                            "url": plan_url,
                            "cars": details['cars']
                        }
                        
                        print(f"[BlueHavenHomesLakeBreezePlanScraper] Plan {idx+1}: {plan_data['plan_name']} - Starting at ${starting_price:,} - {details['sqft']:,} sqft")
                        all_listings.append(plan_data)
                        
                    except Exception as e:
                        print(f"[BlueHavenHomesLakeBreezePlanScraper] Error processing plan {idx+1}: {e}")
                        continue
            
            print(f"[BlueHavenHomesLakeBreezePlanScraper] Successfully processed {len(all_listings)} plans across all pages")
            return all_listings
            
        except Exception as e:
            print(f"[BlueHavenHomesLakeBreezePlanScraper] Error: {e}")
            return []
