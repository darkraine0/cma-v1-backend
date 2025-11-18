import requests
import re
import json
from ...base import BaseScraper
from typing import List, Dict

class PacesetterWaldenPondWestPlanScraper(BaseScraper):
    BASE_URL = "https://www.pacesetterhomestexas.com/api/plans?community=56&page="
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        if isinstance(text, str):
            match = re.search(r'([\d,]+)', text)
            return int(match.group(1).replace(",", "")) if match else None
        return int(text) if text else None

    def parse_price(self, text):
        """Extract price from text."""
        if isinstance(text, str):
            match = re.search(r'\$([\d,]+)', text)
            return int(match.group(1).replace(",", "")) if match else None
        return int(text) if text else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        if isinstance(text, (int, float)):
            return str(text)
        match = re.search(r'(\d+(?:\.\d+)?)', str(text))
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        if isinstance(text, (int, float)):
            return str(text)
        match = re.search(r'(\d+(?:\.\d+)?)', str(text))
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        return "2"  # Default to 2 stories for single family homes

    def get_status(self, plan):
        """Extract the status of the plan."""
        return "available" if plan.get('is_active', 0) == 1 else "unavailable"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[PacesetterWaldenPondWestPlanScraper] Fetching plans from API")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            # Get first page to determine total pages
            response = requests.get(self.BASE_URL + "1", headers=headers, timeout=15)
            print(f"[PacesetterWaldenPondWestPlanScraper] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[PacesetterWaldenPondWestPlanScraper] Request failed with status {response.status_code}")
                return []
            
            first_page_data = response.json()
            last_page = first_page_data.get('last_page', 1)
            total = first_page_data.get('total', 0)
            
            print(f"[PacesetterWaldenPondWestPlanScraper] Found {total} plans across {last_page} pages")
            
            all_plans = []
            
            # Fetch all pages
            for page in range(1, last_page + 1):
                print(f"[PacesetterWaldenPondWestPlanScraper] Fetching page {page}/{last_page}")
                response = requests.get(self.BASE_URL + str(page), headers=headers, timeout=15)
                
                if response.status_code == 200:
                    page_data = response.json()
                    plans = page_data.get('data', [])
                    all_plans.extend(plans)
                    print(f"[PacesetterWaldenPondWestPlanScraper] Page {page}: {len(plans)} plans")
                else:
                    print(f"[PacesetterWaldenPondWestPlanScraper] Failed to fetch page {page}: {response.status_code}")
            
            print(f"[PacesetterWaldenPondWestPlanScraper] Total plans collected: {len(all_plans)}")
            
            listings = []
            
            # Filter for Walden Pond specific plan names (based on website analysis)
            walden_plan_names = [
                "Corrigan", "Statler", "Palmetto", "Harlow", "Archer", 
                "Carrollton", "Frisco", "Coppell", "Fannin", "Southlake",
                "Addison II", "Rockwall", "Fairmont", "Grapevine", "Garland", "Richardson"
            ]
            
            seen_plan_names = set()
            
            for idx, plan in enumerate(all_plans):
                try:
                    # Extract basic information
                    name = plan.get('name', '')
                    
                    # Only process plans that match Walden Pond plan names
                    if name not in walden_plan_names:
                        continue
                    
                    # Only take the first occurrence of each plan name (to match website behavior)
                    if name in seen_plan_names:
                        continue
                    seen_plan_names.add(name)
                    
                    beds = self.parse_beds(plan.get('beds', ''))
                    baths = self.parse_baths(plan.get('baths', ''))
                    sqft_text = plan.get('sqft', '')
                    sqft = self.parse_sqft(sqft_text)
                    
                    # Extract price from formattedPrice
                    formatted_price = plan.get('formattedPrice', '')
                    price = self.parse_price(formatted_price)
                    
                    # Get URL
                    url = plan.get('url', '')
                    
                    # Use the plan name directly
                    plan_name = name
                    
                    if not all([plan_name, beds, baths, sqft]):
                        print(f"[PacesetterWaldenPondWestPlanScraper] Skipping plan {idx+1}: Missing required data")
                        print(f"  Name: {name}, Beds: {beds}, Baths: {baths}, Sqft: {sqft}")
                        continue
                    
                    # For plans, price might be "Pricing Coming Soon" or similar
                    if not price:
                        price = None  # Plans might not have pricing yet
                    
                    # Calculate price per sqft if price is available
                    price_per_sqft = round(price / sqft, 2) if price and sqft else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": self.parse_stories(""),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Pacesetter Homes",
                        "community": "Walden Pond West",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": None,  # Plans don't have specific addresses
                        "original_price": None,
                        "price_cut": "",
                        "status": self.get_status(plan),
                        "url": url
                    }
                    
                    price_str = f"${price:,}" if price else "No price"
                    print(f"[PacesetterWaldenPondWestPlanScraper] Plan {len(listings)+1}: {plan_name} - {price_str} - {sqft:,} sqft - {beds} beds - {baths} baths")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[PacesetterWaldenPondWestPlanScraper] Error processing plan {idx+1}: {e}")
                    continue
            
            print(f"[PacesetterWaldenPondWestPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[PacesetterWaldenPondWestPlanScraper] Error: {e}")
            return []
