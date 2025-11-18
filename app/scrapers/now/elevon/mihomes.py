import requests
import re
import json
from ...base import BaseScraper
from typing import List, Dict

class MIHomesElevonNowScraper(BaseScraper):
    API_URL = "https://www.mihomes.com/sitecore/api/ssc/MIHomes-Project-Website-Api/Search"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[MIHomesElevonNowScraper] Fetching API URL: {self.API_URL}")
            
            # API parameters based on the provided fetch request
            params = {
                "community": "Elevon",
                "search": "Dallas / Fort Worth Metroplex",
                "searchtype": "inventory",
                "typeahead_type": "markets",
                "x1": "33.74810296876089",
                "x2": "31.803835487578123",
                "y1": "-96.3135887890625",
                "y2": "-97.5330712109375",
                "zoom": "9"
            }
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.mihomes.com/new-homes/texas/dallas-fort-worth-metroplex/quick-move-in-homes?community=Elevon"
            }
            
            resp = requests.get(self.API_URL, params=params, headers=headers, timeout=15)
            print(f"[MIHomesElevonNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[MIHomesElevonNowScraper] API request failed with status {resp.status_code}")
                return []
            
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                print(f"[MIHomesElevonNowScraper] Failed to parse JSON response: {e}")
                return []
            
            print(f"[MIHomesElevonNowScraper] Successfully parsed JSON response")
            
            listings = []
            
            # Extract results from the API response
            results = data.get('results', [])
            print(f"[MIHomesElevonNowScraper] Found {len(results)} results in API response")
            
            for idx, result in enumerate(results):
                try:
                    # Extract basic information
                    plan_name = result.get('plan', '')
                    street_address = result.get('streetaddress', '')
                    price_str = result.get('price', '0')
                    square_str = result.get('square', '0')
                    stories_str = result.get('stories', '1')
                    bedrooms = result.get('bedrooms', '')
                    bathrooms = result.get('bathrooms', 0)
                    
                    # Parse price and square footage
                    price = None
                    if price_str and price_str != '0':
                        try:
                            price = int(price_str.replace(',', ''))
                        except (ValueError, TypeError):
                            print(f"[MIHomesElevonNowScraper] Could not parse price: {price_str}")
                    
                    sqft = None
                    if square_str and square_str != '0':
                        sqft = self.parse_sqft(square_str)
                    
                    # Use street address as plan name if available, otherwise use plan name
                    final_plan_name = street_address if street_address else plan_name
                    
                    if not final_plan_name:
                        print(f"[MIHomesElevonNowScraper] Skipping result {idx+1}: Missing plan name and street address")
                        continue
                    
                    if not price or not sqft:
                        print(f"[MIHomesElevonNowScraper] Skipping result {idx+1}: Missing price or sqft")
                        print(f"  Plan name: {final_plan_name}")
                        print(f"  Price: {price}")
                        print(f"  Sqft: {sqft}")
                        continue
                    
                    # Calculate price per square foot
                    price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": self.parse_stories(stories_str),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": final_plan_name,
                        "company": "M/I Homes",
                        "community": "Elevon",
                        "type": "now",
                        "beds": int(bedrooms) if bedrooms else None,
                        "baths": bathrooms if bathrooms else None,
                        "address": street_address
                    }
                    
                    print(f"[MIHomesElevonNowScraper] Result {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[MIHomesElevonNowScraper] Error processing result {idx+1}: {e}")
                    continue
            
            print(f"[MIHomesElevonNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[MIHomesElevonNowScraper] Error: {e}")
            return [] 