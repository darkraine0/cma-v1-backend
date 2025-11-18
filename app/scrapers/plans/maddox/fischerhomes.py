import requests
import json
from datetime import datetime
from ...base import BaseScraper
from typing import List, Dict

class FischerHomesMaddoxPlanScraper(BaseScraper):
    API_URL = "https://www.fischerhomes.com/api/residence?community_id=872"
    
    def fetch_plans(self) -> List[Dict]:
        """Fetch and parse plan data from Fischer Homes API."""
        print(f"[{self.__class__.__name__}] Fetching API: {self.API_URL}")
        
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json, text/plain, */*",
        }
        
        try:
            resp = requests.get(self.API_URL, headers=headers, timeout=15)
            print(f"[{self.__class__.__name__}] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[{self.__class__.__name__}] Request failed with status {resp.status_code}")
                return []
            
            data = resp.json()
            
            if 'residences' not in data:
                print(f"[{self.__class__.__name__}] No residences found in API response")
                return []
            
            # Parse residences data (it's a JSON string)
            residences_data = data['residences']
            if isinstance(residences_data, str):
                residences = json.loads(residences_data)
            else:
                residences = residences_data
            
            print(f"[{self.__class__.__name__}] Found {len(residences)} residences")
            
            plans = []
            for residence in residences:
                try:
                    # Extract plan data from residence
                    plan = residence.get('plan', {})
                    
                    plan_name = plan.get('name', residence.get('name', ''))
                    if not plan_name:
                        continue
                    
                    price = residence.get('price')
                    if price:
                        price = int(price)
                    
                    # Get square footage (use low value if available)
                    sqft = plan.get('sqft_low') or residence.get('sqft_low')
                    if sqft:
                        sqft = int(sqft)
                    
                    # Get bedroom range
                    bed_low = plan.get('bed_low') or residence.get('bed_low')
                    bed_high = plan.get('bed_high') or residence.get('bed_high')
                    beds = None
                    if bed_low and bed_high:
                        if bed_low == bed_high:
                            beds = str(int(bed_low))
                        else:
                            beds = f"{int(bed_low)}-{int(bed_high)}"
                    elif bed_low:
                        beds = str(int(bed_low))
                    
                    # Get bathroom range
                    bath_low = plan.get('bath_low') or residence.get('bath_low')
                    bath_high = plan.get('bath_high') or residence.get('bath_high')
                    baths = None
                    if bath_low and bath_high:
                        if bath_low == bath_high:
                            baths = str(bath_low)
                        else:
                            baths = f"{bath_low}-{bath_high}"
                    elif bath_low:
                        baths = str(bath_low)
                    
                    # Get stories
                    stories = plan.get('floors') or residence.get('floors')
                    if stories:
                        stories = int(stories)
                    
                    # Calculate price per sqft if we have both
                    price_per_sqft = None
                    if price and sqft:
                        price_per_sqft = round(price / sqft, 2)
                    
                    plan_data = {
                        'plan_name': plan_name,
                        'price': price,
                        'sqft': sqft,
                        'stories': stories,
                        'price_per_sqft': price_per_sqft,
                        'beds': beds,
                        'baths': baths,
                        'company': 'Fischer Homes',
                        'community': 'Maddox',
                        'type': 'plan',
                        'address': 'Crossvine Estates, Braselton, GA',
                        'last_updated': datetime.now()
                    }
                    
                    plans.append(plan_data)
                    print(f"[{self.__class__.__name__}] Added plan: {plan_name} - ${price:,} - {sqft:,} sqft")
                    
                except Exception as e:
                    print(f"[{self.__class__.__name__}] Error processing residence: {e}")
                    continue
            
            print(f"[{self.__class__.__name__}] Successfully parsed {len(plans)} plans")
            return plans
            
        except Exception as e:
            print(f"[{self.__class__.__name__}] Error fetching plans: {e}")
            return []