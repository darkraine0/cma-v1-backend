import requests
import re
import json
from ...base import BaseScraper
from typing import List, Dict

class HistoryMakerElevonNowScraper(BaseScraper):
    API_URL = "https://www.historymaker.com/api/homes"
    
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
            print(f"[HistoryMakerElevonNowScraper] Fetching API URL: {self.API_URL}")
            
            # API parameters based on the provided fetch request
            params = {
                "subregions[]": "20",
                "communities[]": "64",
                "region": "3",
                "subregion": "20",
                "community": "64",
                "perPage": "11",
                "page": "1"
            }
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.historymaker.com/new-home-communities/dallas-fort-worth/lavon/elevon"
            }
            
            resp = requests.get(self.API_URL, params=params, headers=headers, timeout=15)
            print(f"[HistoryMakerElevonNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[HistoryMakerElevonNowScraper] API request failed with status {resp.status_code}")
                return []
            
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                print(f"[HistoryMakerElevonNowScraper] Failed to parse JSON response: {e}")
                return []
            
            print(f"[HistoryMakerElevonNowScraper] Successfully parsed JSON response")
            
            listings = []
            
            # Extract data from the API response
            homes_data = data.get('data', [])
            print(f"[HistoryMakerElevonNowScraper] Found {len(homes_data)} homes in API response")
            
            for idx, home in enumerate(homes_data):
                try:
                    # Extract basic information
                    address = home.get('address', '')
                    price = home.get('price', 0)
                    sqft_str = home.get('sqft', '0')
                    floors = home.get('floors', 1)
                    beds = home.get('beds', 0)
                    baths = home.get('baths', 0)
                    residence_name = home.get('residence_name', '')
                    
                    # Parse square footage
                    sqft = None
                    if sqft_str and sqft_str != '0':
                        sqft = self.parse_sqft(sqft_str)
                    
                    # Use address as plan name if available, otherwise use residence name
                    final_plan_name = address if address else residence_name
                    
                    if not final_plan_name:
                        print(f"[HistoryMakerElevonNowScraper] Skipping home {idx+1}: Missing address and residence name")
                        continue
                    
                    if not price or not sqft:
                        print(f"[HistoryMakerElevonNowScraper] Skipping home {idx+1}: Missing price or sqft")
                        print(f"  Plan name: {final_plan_name}")
                        print(f"  Price: {price}")
                        print(f"  Sqft: {sqft}")
                        continue
                    
                    # Calculate price per square foot
                    price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": self.parse_stories(str(floors)),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": final_plan_name,
                        "company": "HistoryMaker Homes",
                        "community": "Elevon",
                        "type": "now",
                        "beds": beds if beds else None,
                        "baths": baths if baths else None,
                        "address": address
                    }
                    
                    print(f"[HistoryMakerElevonNowScraper] Home {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[HistoryMakerElevonNowScraper] Error processing home {idx+1}: {e}")
                    continue
            
            print(f"[HistoryMakerElevonNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[HistoryMakerElevonNowScraper] Error: {e}")
            return [] 