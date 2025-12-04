import requests
import re
from ...base import BaseScraper
from typing import List, Dict

class PacesetterMilranyPlanScraper(BaseScraper):
    API_BASE_URL = "https://www.pacesetterhomestexas.com/api/residences"
    COMMUNITY_ID = 39
    
    def parse_sqft(self, sqft_str):
        """Extract square footage from text. Handles ranges like '2,125 - 2,129' or single values like '1,949'."""
        if not sqft_str:
            return None
        # Handle ranges - take the first number
        if ' - ' in sqft_str:
            match = re.search(r'([\d,]+)', sqft_str)
        else:
            match = re.search(r'([\d,]+)', sqft_str)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, formatted_price):
        """Extract starting price from formatted price string (e.g., 'From <em>$438,900</em>')."""
        if not formatted_price:
            return None
        # Remove HTML tags and extract price
        price_match = re.search(r'\$([\d,]+)', formatted_price)
        return int(price_match.group(1).replace(",", "")) if price_match else None

    def parse_stories(self, text):
        """Extract number of stories from text."""
        # Default to 2 stories for these homes based on the data
        return "2"

    def fetch_plans(self) -> List[Dict]:
        try:
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            # Fetch first page to get pagination info
            print(f"[PacesetterMilranyPlanScraper] Fetching page 1 from API")
            resp = requests.get(
                self.API_BASE_URL,
                params={"community": self.COMMUNITY_ID, "page": 1},
                headers=headers,
                timeout=15
            )
            
            if resp.status_code != 200:
                print(f"[PacesetterMilranyPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            data = resp.json()
            last_page = data.get('last_page', 1)
            total = data.get('total', 0)
            print(f"[PacesetterMilranyPlanScraper] Found {total} total plans across {last_page} pages")
            
            # Process first page
            self._process_page_data(data.get('data', []), listings, seen_plan_names)
            
            # Fetch remaining pages
            for page in range(2, last_page + 1):
                print(f"[PacesetterMilranyPlanScraper] Fetching page {page} from API")
                resp = requests.get(
                    self.API_BASE_URL,
                    params={"community": self.COMMUNITY_ID, "page": page},
                    headers=headers,
                    timeout=15
                )
                
                if resp.status_code != 200:
                    print(f"[PacesetterMilranyPlanScraper] Failed to fetch page {page} with status {resp.status_code}")
                    continue
                
                page_data = resp.json()
                self._process_page_data(page_data.get('data', []), listings, seen_plan_names)
            
            print(f"[PacesetterMilranyPlanScraper] Successfully processed {len(listings)} floor plans")
            return listings
            
        except Exception as e:
            print(f"[PacesetterMilranyPlanScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _process_page_data(self, plans_data: List[Dict], listings: List[Dict], seen_plan_names: set):
        """Process plan data from a single API page."""
        for idx, plan in enumerate(plans_data):
            try:
                print(f"[PacesetterMilranyPlanScraper] Processing plan {idx+1}")
                
                # Extract plan name
                plan_name = plan.get('name', '').strip()
                if not plan_name:
                    print(f"[PacesetterMilranyPlanScraper] Skipping plan {idx+1}: No plan name found")
                    continue
                
                # Check for duplicate plan names
                if plan_name in seen_plan_names:
                    print(f"[PacesetterMilranyPlanScraper] Skipping plan {idx+1}: Duplicate plan name '{plan_name}'")
                    continue
                
                seen_plan_names.add(plan_name)
                
                # Extract price
                formatted_price = plan.get('formattedPrice', '')
                starting_price = self.parse_price(formatted_price)
                if not starting_price:
                    print(f"[PacesetterMilranyPlanScraper] Skipping plan {idx+1}: No starting price found in '{formatted_price}'")
                    continue
                
                # Extract beds, baths, and sqft
                beds = str(plan.get('beds', ''))
                baths = str(plan.get('baths', ''))
                sqft_str = plan.get('sqft', '')
                
                if not sqft_str:
                    print(f"[PacesetterMilranyPlanScraper] Skipping plan {idx+1}: No square footage found")
                    continue
                
                # Parse sqft (handles ranges like "2,125 - 2,129")
                sqft = self.parse_sqft(sqft_str)
                if not sqft:
                    print(f"[PacesetterMilranyPlanScraper] Skipping plan {idx+1}: Invalid square footage '{sqft_str}'")
                    continue
                
                # Calculate price per sqft
                price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                
                # Extract image URL if available
                image_url = ""
                hero = plan.get('hero', {})
                if hero and 'image' in hero:
                    image_url = hero['image'].get('medium', '')
                
                # Extract plan detail URL
                plan_detail_url = plan.get('url', '')
                
                plan_data = {
                    "price": starting_price,
                    "sqft": sqft,
                    "stories": self.parse_stories(""),
                    "price_per_sqft": price_per_sqft,
                    "plan_name": plan_name,
                    "company": "Pacesetter Homes",
                    "community": "Milrany",
                    "type": "plan",
                    "beds": beds,
                    "baths": baths,
                    "address": "",
                    "original_price": None,
                    "price_cut": "",
                    "image_url": image_url,
                    "plan_detail_url": plan_detail_url
                }
                
                print(f"[PacesetterMilranyPlanScraper] Plan {idx+1}: {plan_data}")
                listings.append(plan_data)
                
            except Exception as e:
                print(f"[PacesetterMilranyPlanScraper] Error processing plan {idx+1}: {e}")
                import traceback
                traceback.print_exc()
                continue
