import requests
import re
from ...base import BaseScraper
from typing import List, Dict

class ChesmarHomesMyrtleCreekPlanScraper(BaseScraper):
    API_URL = "https://chesmar.com/wp-json/chesmar/search/"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        # Handle both formats: "$410,990" and "410,990"
        if isinstance(text, str):
            # Remove any non-digit characters except commas
            clean_text = re.sub(r'[^\d,]', '', text)
            if clean_text:
                return int(clean_text.replace(",", ""))
        return None

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
        # Chesmar homes are typically single story, but we'll default to 1
        return "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[ChesmarHomesMyrtleCreekPlanScraper] Fetching API: {self.API_URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.API_URL, headers=headers, timeout=15)
            print(f"[ChesmarHomesMyrtleCreekPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[ChesmarHomesMyrtleCreekPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            data = resp.json()
            listings = []
            
            # Find Oaks of North Grove community
            oaks_community = None
            if 'successes' in data:
                for success in data['successes']:
                    if 'communities' in success:
                        for community in success['communities']:
                            if 'oaks of north grove' in community.get('name', '').lower():
                                oaks_community = community
                                break
            
            if not oaks_community:
                print(f"[ChesmarHomesMyrtleCreekPlanScraper] Oaks of North Grove community not found")
                return []
            
            print(f"[ChesmarHomesMyrtleCreekPlanScraper] Found Oaks of North Grove community")
            
            # Extract floor plans from the community data
            floorplans = oaks_community.get('floorplans', [])
            print(f"[ChesmarHomesMyrtleCreekPlanScraper] Found {len(floorplans)} floor plan IDs")
            
            # For now, we'll create placeholder listings based on the community info
            # In a real implementation, you might need to fetch individual floor plan details
            # from a different API endpoint using the floor plan IDs
            
            # Extract community info
            starting_price = self.parse_price(oaks_community.get('starting_from', '0'))
            bedroom_range = oaks_community.get('bedroom_range', '')
            bathroom_range = oaks_community.get('bathroom_range', '')
            sqft_range = oaks_community.get('sq_foot_range', '')
            
            print(f"[ChesmarHomesMyrtleCreekPlanScraper] Community data: starting_from={oaks_community.get('starting_from')}, bedroom_range={bedroom_range}, bathroom_range={bathroom_range}, sq_foot_range={sqft_range}")
            print(f"[ChesmarHomesMyrtleCreekPlanScraper] Parsed data: starting_price={starting_price}, beds={bedroom_range}, baths={bathroom_range}, sqft_range={sqft_range}")
            
            # Parse bedroom and bathroom ranges
            beds = bedroom_range.split('-')[0].strip() if '-' in bedroom_range else bedroom_range
            baths = bathroom_range.split('-')[0].strip() if '-' in bathroom_range else bathroom_range
            
            # Parse square footage range (take the lower bound)
            sqft_match = re.search(r'([\d,]+)', sqft_range)
            sqft = int(sqft_match.group(1).replace(",", "")) if sqft_match else None
            
            if starting_price and sqft:
                # Calculate price per sqft
                price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                
                plan_data = {
                    "price": starting_price,
                    "sqft": sqft,
                    "stories": self.parse_stories(""),
                    "price_per_sqft": price_per_sqft,
                    "plan_name": "Starting from",
                    "company": "Chesmar Homes",
                    "community": "Myrtle Creek",
                    "type": "plan",
                    "beds": beds,
                    "baths": baths,
                    "address": "",
                    "original_price": None,
                    "price_cut": "",
                    "floor_plan_link": ""
                }
                
                print(f"[ChesmarHomesMyrtleCreekPlanScraper] Community plan: {plan_data}")
                listings.append(plan_data)
            else:
                print(f"[ChesmarHomesMyrtleCreekPlanScraper] Missing required data: starting_price={starting_price}, sqft={sqft}")
            
            print(f"[ChesmarHomesMyrtleCreekPlanScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[ChesmarHomesMyrtleCreekPlanScraper] Error: {e}")
            return []

    def get_company_name(self) -> str:
        """Return company name."""
        return "Chesmar Homes"

    def get_community_name(self) -> str:
        """Return community name."""
        return "Myrtle Creek"
