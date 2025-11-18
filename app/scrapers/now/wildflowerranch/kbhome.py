import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class KBHomeWildflowerRanchNowScraper(BaseScraper):
    URL = "https://www.kbhome.com/new-homes-dallas-fort-worth/the-preserve"
    
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
        # KB Home listings typically don't show stories, default to 1
        return "1"

    def get_status(self, container):
        """Extract the status of the home."""
        # Check for "Available Now" overlay
        overlay = container.find('div', class_='availablenow-overlay-div')
        if overlay and 'Available Now' in overlay.get_text():
            return "available"
        return "available"  # Default to available

    def get_homesite_number(self, container):
        """Extract homesite number from the container."""
        homesite_elem = container.find('div', class_='fp-action-items')
        if homesite_elem:
            homesite_text = homesite_elem.get_text()
            homesite_match = re.search(r'Homesite\s+(\d+)', homesite_text)
            return homesite_match.group(1) if homesite_match else None
        return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[KBHomeWildflowerRanchNowScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            response = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[KBHomeWildflowerRanchNowScraper] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[KBHomeWildflowerRanchNowScraper] Request failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # The data is loaded via JavaScript, so we need to extract it from the script tags
            # Look for the LocalQMIs JavaScript variable
            script_tags = soup.find_all('script')
            qmi_data = None
            
            for script in script_tags:
                if script.string and 'LocalQMIs' in script.string:
                    script_content = script.string
                    # Extract the LocalQMIs array from JavaScript
                    start_marker = 'var LocalQMIs = ['
                    end_marker = '];'
                    
                    start_idx = script_content.find(start_marker)
                    if start_idx != -1:
                        start_idx += len(start_marker) - 1  # Include the opening bracket
                        end_idx = script_content.find(end_marker, start_idx)
                        if end_idx != -1:
                            json_str = script_content[start_idx:end_idx + 1]
                            try:
                                import json
                                qmi_data = json.loads(json_str)
                                break
                            except:
                                # If JSON parsing fails, try to extract data manually
                                pass
            
            if not qmi_data:
                print(f"[KBHomeWildflowerRanchNowScraper] No QMI data found in JavaScript")
                return []
            
            print(f"[KBHomeWildflowerRanchNowScraper] Found {len(qmi_data)} QMI listings in JavaScript data")
            
            listings = []
            
            for idx, home_data in enumerate(qmi_data):
                try:
                    # Extract data from the JavaScript object
                    address = home_data.get('address', '')
                    price = home_data.get('price', '')
                    beds = home_data.get('bedrooms', '')
                    baths = home_data.get('bathrooms', '')
                    sqft = home_data.get('size', '')
                    homesite_number = home_data.get('homesite', '')
                    stories = home_data.get('stories', '1')
                    cars = home_data.get('garages', '')
                    
                    if not address:
                        print(f"[KBHomeWildflowerRanchNowScraper] Skipping listing {idx+1}: No address found")
                        continue
                    
                    # Parse price
                    try:
                        price = int(price) if price else None
                    except:
                        price = self.parse_price(str(price)) if price else None
                    
                    if not price:
                        print(f"[KBHomeWildflowerRanchNowScraper] Skipping listing {idx+1}: No price found")
                        continue
                    
                    # Parse sqft
                    try:
                        sqft = int(sqft) if sqft else None
                    except:
                        sqft = self.parse_sqft(str(sqft)) if sqft else None
                    
                    # Skip if missing essential details
                    if not all([beds, baths, sqft]):
                        print(f"[KBHomeWildflowerRanchNowScraper] Skipping listing {idx+1}: Missing property details (beds: {beds}, baths: {baths}, sqft: {sqft})")
                        continue
                    
                    # Get additional details
                    status = "available"  # All QMI listings are available
                    page_url = home_data.get('pageUrl', '')
                    property_url = f"https://www.kbhome.com{page_url}" if page_url else None
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    # Create plan name with address and homesite
                    plan_name = address
                    if homesite_number:
                        plan_name += f" (Homesite {homesite_number})"
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": str(stories),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "KB Home",
                        "community": "Wildflower Ranch",
                        "type": "now",
                        "beds": str(beds),
                        "baths": str(baths),
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "status": status,
                        "url": property_url,
                        "homesite_number": homesite_number,
                        "cars": str(cars)
                    }
                    
                    print(f"[KBHomeWildflowerRanchNowScraper] Property {idx+1}: {plan_data['plan_name']} - ${price:,} - {sqft:,} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[KBHomeWildflowerRanchNowScraper] Error processing listing {idx+1}: {e}")
                    continue
            
            print(f"[KBHomeWildflowerRanchNowScraper] Successfully processed {len(listings)} properties")
            return listings
            
        except Exception as e:
            print(f"[KBHomeWildflowerRanchNowScraper] Error: {e}")
            return []
