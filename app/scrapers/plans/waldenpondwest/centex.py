import requests
import json
from ...base import BaseScraper
from typing import List, Dict

class CentexWaldenPondWestPlanScraper(BaseScraper):
    BASE_URL = "https://www.centex.com/api/plan/homeplans?communityId=211042"
    
    def parse_price(self, price_value):
        """Extract price from various formats."""
        if isinstance(price_value, (int, float)):
            return int(price_value)
        elif isinstance(price_value, str):
            # Remove currency symbols and commas
            cleaned = price_value.replace('$', '').replace(',', '').strip()
            try:
                return int(float(cleaned))
            except (ValueError, TypeError):
                return None
        return None
    
    def parse_sqft(self, sqft_value):
        """Extract square footage from various formats."""
        if isinstance(sqft_value, (int, float)):
            return int(sqft_value)
        elif isinstance(sqft_value, str):
            # Remove commas and extract number
            cleaned = sqft_value.replace(',', '').strip()
            try:
                return int(float(cleaned))
            except (ValueError, TypeError):
                return None
        return None
    
    def parse_beds(self, beds_value):
        """Extract number of bedrooms."""
        if isinstance(beds_value, (int, float)):
            return str(int(beds_value))
        elif isinstance(beds_value, str):
            return beds_value.strip()
        return str(beds_value) if beds_value is not None else ""
    
    def parse_baths(self, baths_value):
        """Extract number of bathrooms."""
        if isinstance(baths_value, (int, float)):
            return str(baths_value)
        elif isinstance(baths_value, str):
            return baths_value.strip()
        return str(baths_value) if baths_value is not None else ""
    
    def parse_stories(self, floors_value):
        """Extract number of stories."""
        if isinstance(floors_value, (int, float)):
            return str(int(floors_value))
        elif isinstance(floors_value, str):
            return floors_value.strip()
        return str(floors_value) if floors_value is not None else ""
    
    def get_status(self, plan_data):
        """Determine plan status."""
        is_plan_active = plan_data.get('isPlanActive', True)
        is_sold_out = plan_data.get('isSoldOut', False)
        is_future_release = plan_data.get('isFutureRelease', False)
        
        if is_sold_out:
            return 'sold_out'
        elif is_future_release:
            return 'coming_soon'
        elif is_plan_active:
            return 'available'
        else:
            return 'unavailable'
    
    def fetch_plans(self) -> List[Dict]:
        """Fetch home plans from Centex API."""
        try:
            print(f"[CentexWaldenPondWestPlanScraper] Fetching home plans from API")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            response = requests.get(self.BASE_URL, headers=headers, timeout=15)
            print(f"[CentexWaldenPondWestPlanScraper] Response status: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            print(f"[CentexWaldenPondWestPlanScraper] Found {len(data)} home plans")
            
            listings = []
            
            for idx, plan in enumerate(data):
                try:
                    # Extract basic information
                    plan_name = plan.get('planName', '')
                    beds = self.parse_beds(plan.get('bedrooms', ''))
                    baths = self.parse_baths(plan.get('bathrooms', ''))
                    sqft = self.parse_sqft(plan.get('squareFeet', ''))
                    stories = self.parse_stories(plan.get('floors', ''))
                    
                    # Extract price information
                    price = self.parse_price(plan.get('price', 0))
                    
                    # Get URL
                    page_url = plan.get('pageURL', '')
                    url = f"https://www.centex.com{page_url}" if page_url else ""
                    
                    # Get plan status
                    status = self.get_status(plan)
                    
                    # Get series information
                    series_name = plan.get('seriesName', '')
                    series_description = plan.get('seriesDescription', '')
                    
                    # Validate required fields
                    if not all([plan_name, beds, baths, sqft]):
                        print(f"[CentexWaldenPondWestPlanScraper] Skipping plan {idx+1}: Missing required data")
                        print(f"  Name: {plan_name}, Beds: {beds}, Baths: {baths}, Sqft: {sqft}")
                        continue
                    
                    # Calculate price per sqft if price is available
                    price_per_sqft = round(price / sqft, 2) if price and sqft else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Centex",
                        "community": "Walden Pond West",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": None,  # Plans don't have specific addresses
                        "original_price": None,
                        "price_cut": "",
                        "status": status,
                        "url": url
                    }
                    
                    price_str = f"${price:,}" if price else "No price"
                    print(f"[CentexWaldenPondWestPlanScraper] Plan {idx+1}: {plan_name} - {price_str} - {sqft:,} sqft - {beds} beds - {baths} baths")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[CentexWaldenPondWestPlanScraper] Error processing plan {idx+1}: {e}")
                    continue
            
            print(f"[CentexWaldenPondWestPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except requests.exceptions.RequestException as e:
            print(f"[CentexWaldenPondWestPlanScraper] Request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"[CentexWaldenPondWestPlanScraper] Error decoding JSON: {e}")
            return []
        except Exception as e:
            print(f"[CentexWaldenPondWestPlanScraper] An unexpected error occurred: {e}")
            return []
