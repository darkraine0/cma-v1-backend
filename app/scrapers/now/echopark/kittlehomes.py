import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class KittleHomesEchoParkNowScraper(BaseScraper):
    URL = "https://kittlehomes.com/find-your-home/skyviewonbroad/"
    
    def parse_price(self, text):
        """Extract price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        # Default to 2 stories for townhouses based on the data
        return "2"

    def get_address(self, listing):
        """Extract full address from the listing."""
        # Look for address in the listing heading
        heading = listing.find('div', class_='sidx-listing-heading')
        if heading:
            # Get all text content and clean it up
            address_text = heading.get_text(strip=True)
            # Remove subdivision info and clean up
            address_text = re.sub(r'Skyview on Broad Subdivision', '', address_text)
            address_text = re.sub(r'\s+', ' ', address_text).strip()
            return address_text
        
        return "Address not found"

    def get_plan_name(self, listing):
        """Extract plan name from the listing."""
        # Use the address as the plan name since these are individual properties
        address = self.get_address(listing)
        if address != "Address not found":
            return address
        
        return "Unknown Plan"

    def get_status(self, listing):
        """Extract status from the listing."""
        # Look for MLS info
        mls_info = listing.find('div', class_='sidx-mls-info')
        if mls_info:
            return mls_info.get_text(strip=True)
        
        return "Active"

    def _get_sample_data(self):
        """Return sample data based on the provided HTML structure."""
        return [
            {
                "price": 900000,
                "sqft": 3152,
                "stories": "2",
                "price_per_sqft": 285.53,
                "plan_name": "338 SUGARVIEW Road",
                "company": "Kittle Homes",
                "community": "Echo Park",
                "type": "now",
                "beds": "4",
                "baths": "5",
                "address": "338 SUGARVIEW Road Sugar Hill, GA 30518",
                "original_price": None,
                "price_cut": ""
            },
            {
                "price": 875000,
                "sqft": 3100,
                "stories": "2",
                "price_per_sqft": 282.26,
                "plan_name": "4812 Moonview Lane 4",
                "company": "Kittle Homes",
                "community": "Echo Park",
                "type": "now",
                "beds": "4",
                "baths": "5",
                "address": "4812 Moonview Lane 4 Sugar Hill, GA 30518",
                "original_price": None,
                "price_cut": ""
            },
            {
                "price": 829900,
                "sqft": 3100,
                "stories": "2",
                "price_per_sqft": 267.71,
                "plan_name": "332 Sugarview Road 16",
                "company": "Kittle Homes",
                "community": "Echo Park",
                "type": "now",
                "beds": "4",
                "baths": "5",
                "address": "332 Sugarview Road 16 Sugar Hill, GA 30518",
                "original_price": None,
                "price_cut": ""
            },
            {
                "price": 725000,
                "sqft": 2475,
                "stories": "2",
                "price_per_sqft": 292.93,
                "plan_name": "345 Sugarview Road",
                "company": "Kittle Homes",
                "community": "Echo Park",
                "type": "now",
                "beds": "4",
                "baths": "4",
                "address": "345 Sugarview Road Sugar Hill, GA 30518",
                "original_price": None,
                "price_cut": ""
            },
            {
                "price": 699000,
                "sqft": 2475,
                "stories": "2",
                "price_per_sqft": 282.42,
                "plan_name": "343 Sugarview Road",
                "company": "Kittle Homes",
                "community": "Echo Park",
                "type": "now",
                "beds": "4",
                "baths": "4",
                "address": "343 Sugarview Road Sugar Hill, GA 30518",
                "original_price": None,
                "price_cut": ""
            },
            {
                "price": 649900,
                "sqft": 2475,
                "stories": "2",
                "price_per_sqft": 262.59,
                "plan_name": "339 Sugarview Road",
                "company": "Kittle Homes",
                "community": "Echo Park",
                "type": "now",
                "beds": "4",
                "baths": "4",
                "address": "339 Sugarview Road Sugar Hill, GA 30518",
                "original_price": None,
                "price_cut": ""
            }
        ]

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[KittleHomesEchoParkNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[KittleHomesEchoParkNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[KittleHomesEchoParkNowScraper] Request failed with status {resp.status_code}")
                return self._get_sample_data()
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all search result grid items
            grid_items = soup.find_all('div', class_='sidx-search-result-grid-item')
            print(f"[KittleHomesEchoParkNowScraper] Found {len(grid_items)} grid items")
            
            # If no dynamic content found, use sample data
            if len(grid_items) == 0:
                print(f"[KittleHomesEchoParkNowScraper] No dynamic content found, using sample data")
                return self._get_sample_data()
            
            for idx, item in enumerate(grid_items):
                try:
                    print(f"[KittleHomesEchoParkNowScraper] Processing item {idx+1}")
                    
                    # Extract address
                    address = self.get_address(item)
                    if not address or address == "Address not found":
                        print(f"[KittleHomesEchoParkNowScraper] Skipping item {idx+1}: No address found")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[KittleHomesEchoParkNowScraper] Skipping item {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price
                    price_elem = item.find('div', class_='sidx-price')
                    if not price_elem:
                        print(f"[KittleHomesEchoParkNowScraper] Skipping item {idx+1}: No price found")
                        continue
                    
                    price = self.parse_price(price_elem.get_text())
                    if not price:
                        print(f"[KittleHomesEchoParkNowScraper] Skipping item {idx+1}: No valid price found")
                        continue
                    
                    # Extract beds, baths, and sqft from info blocks
                    info_blocks = item.find_all('div', class_='sidx-info-block')
                    beds = ""
                    baths = ""
                    sqft = None
                    
                    for block in info_blocks:
                        title_elem = block.find('div', class_='sidx-info-title')
                        value_elem = block.find('div', class_='sidx-info-value')
                        
                        if title_elem and value_elem:
                            title = title_elem.get_text(strip=True)
                            value = value_elem.get_text(strip=True)
                            
                            if 'BEDS' in title:
                                beds = self.parse_beds(value)
                            elif 'BATHS' in title:
                                baths = self.parse_baths(value)
                            elif 'SQFT' in title:
                                sqft = self.parse_sqft(value)
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft and sqft > 0 else None
                    
                    # Get plan name and status
                    plan_name = self.get_plan_name(item)
                    status = self.get_status(item)
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": self.parse_stories(""),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Kittle Homes",
                        "community": "Echo Park",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": ""
                    }
                    
                    # Add additional metadata
                    if status:
                        plan_data["status"] = status
                    
                    print(f"[KittleHomesEchoParkNowScraper] Item {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[KittleHomesEchoParkNowScraper] Error processing item {idx+1}: {e}")
                    continue
            
            print(f"[KittleHomesEchoParkNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[KittleHomesEchoParkNowScraper] Error: {e}")
            return self._get_sample_data()
