import requests
import re
import json
from ...base import BaseScraper
from typing import List, Dict

class HistoryMakerBrookvillePlanScraper(BaseScraper):
    API_URL = "https://www.historymaker.com/api/residences"
    
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
            print(f"[HistoryMakerBrookvillePlanScraper] Fetching API URL: {self.API_URL}")
            
            # API parameters for Brookville community
            base_params = {
                "subregions[]": "15",
                "communities[]": "57",
                "region": "3",
                "subregion": "15",
                "community": "57",
                "perPage": "11"
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
                print(f"[HistoryMakerBrookvillePlanScraper] Fetching page {page}...")
                
                # Add page parameter
                params = base_params.copy()
                params["page"] = str(page)
                
                resp = requests.get(self.API_URL, params=params, headers=headers, timeout=15)
                print(f"[HistoryMakerBrookvillePlanScraper] Page {page} response status: {resp.status_code}")
                
                if resp.status_code != 200:
                    print(f"[HistoryMakerBrookvillePlanScraper] API request failed with status {resp.status_code}")
                    break
                
                try:
                    data = resp.json()
                except json.JSONDecodeError as e:
                    print(f"[HistoryMakerBrookvillePlanScraper] Failed to parse JSON response for page {page}: {e}")
                    break
                
                print(f"[HistoryMakerBrookvillePlanScraper] Successfully parsed JSON response for page {page}")
                
                # Extract data from the API response
                residences_data = data.get('data', [])
                print(f"[HistoryMakerBrookvillePlanScraper] Page {page}: Found {len(residences_data)} residences")
                
                if not residences_data:
                    print(f"[HistoryMakerBrookvillePlanScraper] No more residences found on page {page}")
                    break
                
                for idx, residence in enumerate(residences_data):
                    try:
                        # Extract basic information
                        name = residence.get('name', '')
                        price = residence.get('price', 0)
                        sqft_str = residence.get('sqft', '0')
                        floors = residence.get('floors', 1)
                        beds = residence.get('beds', 0)
                        baths = residence.get('baths', 0)
                        
                        # Parse square footage
                        sqft = None
                        if sqft_str and sqft_str != '0':
                            sqft = self.parse_sqft(sqft_str)
                        
                        if not name:
                            print(f"[HistoryMakerBrookvillePlanScraper] Skipping residence {idx+1} on page {page}: Missing name")
                            continue
                        
                        if not price or not sqft:
                            print(f"[HistoryMakerBrookvillePlanScraper] Skipping residence {idx+1} on page {page}: Missing price or sqft")
                            print(f"  Name: {name}")
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
                            "plan_name": name,
                            "company": "HistoryMaker Homes",
                            "community": "Brookville",
                            "type": "plan",
                            "beds": beds if beds else None,
                            "baths": baths if baths else None
                        }
                        
                        print(f"[HistoryMakerBrookvillePlanScraper] Page {page}, Residence {idx+1}: {plan_data}")
                        listings.append(plan_data)
                        
                    except Exception as e:
                        print(f"[HistoryMakerBrookvillePlanScraper] Error processing residence {idx+1} on page {page}: {e}")
                        continue
                
                # Check if there's a next page
                current_page = data.get('current_page', page)
                last_page = data.get('last_page', 1)
                next_page_url = data.get('next_page_url')
                
                print(f"[HistoryMakerBrookvillePlanScraper] Page {page}: current_page={current_page}, last_page={last_page}, next_page_url={next_page_url}")
                
                if not next_page_url or page >= last_page:
                    print(f"[HistoryMakerBrookvillePlanScraper] Reached last page ({page}) or no next page available")
                    break
                
                page += 1
            
            print(f"[HistoryMakerBrookvillePlanScraper] Successfully processed {len(listings)} total listings across all pages")
            return listings
            
        except Exception as e:
            print(f"[HistoryMakerBrookvillePlanScraper] Error: {e}")
            return []
