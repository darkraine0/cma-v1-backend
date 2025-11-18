import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class HighlandHomesMyrtleCreekPlanScraper(BaseScraper):
    URLS = [
        "https://www.highlandhomes.com/dfw/waxahachie/ridge-crossing",
        "https://www.highlandhomes.com/dfw/waxahachie/dove-hollow"
    ]
    
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
        match = re.search(r'(\d+(?:-\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "3" and "3-4" formats
        match = re.search(r'(\d+(?:-\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            listings = []
            
            # Loop through both URLs
            for url_idx, url in enumerate(self.URLS, 1):
                print(f"[HighlandHomesMyrtleCreekPlanScraper] Fetching URL {url_idx}: {url}")
                
                resp = requests.get(url, headers=headers, timeout=15)
                print(f"[HighlandHomesMyrtleCreekPlanScraper] Response status: {resp.status_code}")
                
                if resp.status_code != 200:
                    print(f"[HighlandHomesMyrtleCreekPlanScraper] Request failed with status {resp.status_code}")
                    continue
                
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Extract plan data from JavaScript
                print(f"[HighlandHomesMyrtleCreekPlanScraper] Extracting JavaScript plan data from URL {url_idx}...")
                
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'availableIfps' in script.string:
                        script_content = script.string
                        
                        # Extract the availableIfps array
                        import re
                        import json
                        array_match = re.search(r'const availableIfps = (\[.*?\]);', script_content, re.DOTALL)
                        if array_match:
                            array_str = array_match.group(1)
                            
                            try:
                                # Parse the JSON array
                                plans_data = json.loads(array_str)
                                print(f"[HighlandHomesMyrtleCreekPlanScraper] Found {len(plans_data)} plans in JavaScript from URL {url_idx}")
                                
                                for idx, plan in enumerate(plans_data, 1):
                                    try:
                                        # Extract data from JavaScript object
                                        plan_name = plan.get('display', '')
                                        price = plan.get('calcPrice', 0)
                                        sqft = int(plan.get('squareFootage', 0)) if plan.get('squareFootage') else None
                                        beds = plan.get('bedroomsRange', '')
                                        baths = plan.get('bathsRange', '')
                                        stories = plan.get('storiesRange', '1')
                                        url = plan.get('url', '')
                                        
                                        if not plan_name or not price or not sqft:
                                            print(f"[HighlandHomesMyrtleCreekPlanScraper] Skipping plan {idx}: Missing required data")
                                            continue
                                        
                                        # Calculate price per sqft
                                        price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                                        
                                        plan_data = {
                                            "price": price,
                                            "sqft": sqft,
                                            "stories": stories,
                                            "price_per_sqft": price_per_sqft,
                                            "plan_name": plan_name,
                                            "company": "Highland Homes",
                                            "community": "Myrtle Creek",
                                            "type": "plan",
                                            "beds": beds,
                                            "baths": baths,
                                            "address": "",
                                            "original_price": None,
                                            "price_cut": "",
                                            "floor_plan_link": url
                                        }
                                        
                                        print(f"[HighlandHomesMyrtleCreekPlanScraper] Plan {idx}: {plan_name} - ${price:,} - {sqft:,} sqft")
                                        listings.append(plan_data)
                                        
                                    except Exception as e:
                                        print(f"[HighlandHomesMyrtleCreekPlanScraper] Error processing plan {idx}: {e}")
                                        continue
                                
                                break
                                
                            except json.JSONDecodeError as e:
                                print(f"[HighlandHomesMyrtleCreekPlanScraper] JSON decode error: {e}")
                                continue
            
            print(f"[HighlandHomesMyrtleCreekPlanScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[HighlandHomesMyrtleCreekPlanScraper] Error: {e}")
            return []


    def get_company_name(self) -> str:
        """Return company name."""
        return "Highland Homes"

    def get_community_name(self) -> str:
        """Return community name."""
        return "Myrtle Creek"
