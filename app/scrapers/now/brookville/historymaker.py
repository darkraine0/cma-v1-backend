import requests
import re
import json
from ...base import BaseScraper
from typing import List, Dict

class HistoryMakerBrookvilleNowScraper(BaseScraper):
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
            print(f"[HistoryMakerBrookvilleNowScraper] Fetching API URL: {self.API_URL}")
            
            # API parameters for Brookville community
            base_params = {
                "subregions[]": "15",
                "communities[]": "57",
                "region": "3",
                "subregion": "15",
                "community": "57",
                "perPage": "50"
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
                "Referer": "https://www.historymaker.com/new-home-communities/dallas-fort-worth/brookville"
            }
            
            listings = []
            page = 1
            
            while True:
                print(f"[HistoryMakerBrookvilleNowScraper] Fetching page {page}...")
                
                # Add page parameter
                params = base_params.copy()
                params["page"] = str(page)
                
                resp = requests.get(self.API_URL, params=params, headers=headers, timeout=15)
                print(f"[HistoryMakerBrookvilleNowScraper] Page {page} response status: {resp.status_code}")
                
                if resp.status_code != 200:
                    print(f"[HistoryMakerBrookvilleNowScraper] API request failed with status {resp.status_code}")
                    break
                
                try:
                    data = resp.json()
                except json.JSONDecodeError as e:
                    print(f"[HistoryMakerBrookvilleNowScraper] Failed to parse JSON response for page {page}: {e}")
                    break
                
                print(f"[HistoryMakerBrookvilleNowScraper] Successfully parsed JSON response for page {page}")
                
                # Extract data from the API response
                homes_data = data.get('data', [])
                print(f"[HistoryMakerBrookvilleNowScraper] Page {page}: Found {len(homes_data)} homes")
                
                if not homes_data:
                    print(f"[HistoryMakerBrookvilleNowScraper] No more homes found on page {page}")
                    break
                
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
                            print(f"[HistoryMakerBrookvilleNowScraper] Skipping home {idx+1} on page {page}: Missing address and residence name")
                            continue
                        
                        if not price or not sqft:
                            print(f"[HistoryMakerBrookvilleNowScraper] Skipping home {idx+1} on page {page}: Missing price or sqft")
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
                            "community": "Brookville",
                            "type": "now",
                            "beds": beds if beds else None,
                            "baths": baths if baths else None,
                            "address": address
                        }
                        
                        print(f"[HistoryMakerBrookvilleNowScraper] Page {page}, Home {idx+1}: {plan_data}")
                        listings.append(plan_data)
                        
                    except Exception as e:
                        print(f"[HistoryMakerBrookvilleNowScraper] Error processing home {idx+1} on page {page}: {e}")
                        continue
                
                # Check if there's a next page
                current_page = data.get('current_page', page)
                last_page = data.get('last_page', 1)
                next_page_url = data.get('next_page_url')
                
                print(f"[HistoryMakerBrookvilleNowScraper] Page {page}: current_page={current_page}, last_page={last_page}, next_page_url={next_page_url}")
                
                if not next_page_url or page >= last_page:
                    print(f"[HistoryMakerBrookvilleNowScraper] Reached last page ({page}) or no next page available")
                    break
                
                page += 1
            
            print(f"[HistoryMakerBrookvilleNowScraper] Successfully processed {len(listings)} total listings across all pages")
            return listings
            
        except Exception as e:
            print(f"[HistoryMakerBrookvilleNowScraper] Error: {e}")
            return []
