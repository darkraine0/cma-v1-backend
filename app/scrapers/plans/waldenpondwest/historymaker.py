import requests
import json
import re
from ...base import BaseScraper
from typing import List, Dict

class HistoryMakerWaldenPondWestPlanScraper(BaseScraper):
    BASE_URL = "https://www.historymaker.com/api/residences?subregions[]=15&communities[]=57&region=3&subregion=15&community=57&perPage=50&page="
    
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
        # History Maker plans are generally available unless marked otherwise
        return 'available'
    
    def fetch_plans(self) -> List[Dict]:
        """Fetch home plans from History Maker API."""
        try:
            print(f"[HistoryMakerWaldenPondWestPlanScraper] Fetching home plans from API")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            all_plans = []
            page = 1
            last_page = 1
            
            # Fetch the first page to get pagination info
            response = requests.get(f"{self.BASE_URL}{page}", headers=headers, timeout=15)
            print(f"[HistoryMakerWaldenPondWestPlanScraper] Response status: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            last_page = data.get('last_page', 1)
            total = data.get('total', 0)
            print(f"[HistoryMakerWaldenPondWestPlanScraper] Found {total} plans across {last_page} pages")
            
            while page <= last_page:
                print(f"[HistoryMakerWaldenPondWestPlanScraper] Fetching page {page}/{last_page}")
                
                if page > 1:  # Only fetch again if not the first page already fetched
                    response = requests.get(f"{self.BASE_URL}{page}", headers=headers, timeout=15)
                    response.raise_for_status()
                    data = response.json()
                
                current_page_plans = data.get('data', [])
                print(f"[HistoryMakerWaldenPondWestPlanScraper] Page {page}: {len(current_page_plans)} plans")
                all_plans.extend(current_page_plans)
                page += 1
            
            print(f"[HistoryMakerWaldenPondWestPlanScraper] Total plans collected: {len(all_plans)}")
            
            listings = []
            
            for idx, plan in enumerate(all_plans):
                try:
                    # Extract basic information
                    plan_name = plan.get('name', '')
                    beds = self.parse_beds(plan.get('beds', ''))
                    baths = self.parse_baths(plan.get('baths', ''))
                    sqft = self.parse_sqft(plan.get('sqft', ''))
                    
                    # Extract price information
                    price = self.parse_price(plan.get('price', 0))
                    
                    # Get URL
                    url = plan.get('url', '')
                    if url and not url.startswith('http'):
                        url = f"https://www.historymaker.com{url}"
                    
                    # Get plan status
                    status = self.get_status(plan)
                    
                    # Get series information
                    series_name = plan.get('series_name', '')
                    
                    # Validate required fields
                    if not all([plan_name, beds, baths, sqft]):
                        print(f"[HistoryMakerWaldenPondWestPlanScraper] Skipping plan {idx+1}: Missing required data")
                        print(f"  Name: {plan_name}, Beds: {beds}, Baths: {baths}, Sqft: {sqft}")
                        continue
                    
                    # Calculate price per sqft if price is available
                    price_per_sqft = round(price / sqft, 2) if price and sqft else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": None,  # Not available in the API response
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "History Maker",
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
                    print(f"[HistoryMakerWaldenPondWestPlanScraper] Plan {idx+1}: {plan_name} - {price_str} - {sqft:,} sqft - {beds} beds - {baths} baths")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[HistoryMakerWaldenPondWestPlanScraper] Error processing plan {idx+1}: {e}")
                    continue
            
            print(f"[HistoryMakerWaldenPondWestPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except requests.exceptions.RequestException as e:
            print(f"[HistoryMakerWaldenPondWestPlanScraper] Request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"[HistoryMakerWaldenPondWestPlanScraper] Error decoding JSON: {e}")
            return []
        except Exception as e:
            print(f"[HistoryMakerWaldenPondWestPlanScraper] An unexpected error occurred: {e}")
            return []
