import requests
import json
import re
from ...base import BaseScraper
from typing import List, Dict

class HistoryMakerWaldenPondWestNowScraper(BaseScraper):
    BASE_URL = "https://www.historymaker.com/api/homes?subregions[]=15&communities[]=57&region=3&subregion=15&community=57&perPage=50&page="
    
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
    
    def get_status(self, home_data):
        """Determine availability status."""
        is_ready_now = home_data.get('is_ready_now', False)
        is_coming_soon = home_data.get('is_coming_soon', False)
        banner = home_data.get('banner', '')
        
        if is_ready_now or 'Ready Now' in banner:
            return 'available'
        elif is_coming_soon or 'Coming Soon' in banner:
            return 'coming_soon'
        else:
            return 'available'  # Default to available
    
    def get_price_cut(self, home_data):
        """Extract price cut information."""
        original_price = home_data.get('original_price', 0)
        current_price = home_data.get('price', 0)
        
        if original_price and current_price and original_price > current_price:
            price_cut = original_price - current_price
            return f"${price_cut:,}"
        return None
    
    def get_original_price(self, home_data):
        """Get original price before discount."""
        original_price = home_data.get('original_price', 0)
        if original_price and original_price > 0:
            return int(original_price)
        return None
    
    def fetch_plans(self) -> List[Dict]:
        """Fetch available homes from History Maker API."""
        try:
            print(f"[HistoryMakerWaldenPondWestNowScraper] Fetching available homes from API")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            all_homes = []
            page = 1
            last_page = 1
            
            # Fetch the first page to get pagination info
            response = requests.get(f"{self.BASE_URL}{page}", headers=headers, timeout=15)
            print(f"[HistoryMakerWaldenPondWestNowScraper] Response status: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            last_page = data.get('last_page', 1)
            total = data.get('total', 0)
            print(f"[HistoryMakerWaldenPondWestNowScraper] Found {total} homes across {last_page} pages")
            
            while page <= last_page:
                print(f"[HistoryMakerWaldenPondWestNowScraper] Fetching page {page}/{last_page}")
                
                if page > 1:  # Only fetch again if not the first page already fetched
                    response = requests.get(f"{self.BASE_URL}{page}", headers=headers, timeout=15)
                    response.raise_for_status()
                    data = response.json()
                
                current_page_homes = data.get('data', [])
                print(f"[HistoryMakerWaldenPondWestNowScraper] Page {page}: {len(current_page_homes)} homes")
                all_homes.extend(current_page_homes)
                page += 1
            
            print(f"[HistoryMakerWaldenPondWestNowScraper] Total homes collected: {len(all_homes)}")
            
            listings = []
            
            for idx, home in enumerate(all_homes):
                try:
                    # Extract basic information
                    residence_name = home.get('residence_name', '')
                    beds = self.parse_beds(home.get('beds', ''))
                    baths = self.parse_baths(home.get('baths', ''))
                    sqft = self.parse_sqft(home.get('sqft', ''))
                    stories = self.parse_stories(home.get('floors', ''))
                    
                    # Extract price information
                    current_price = self.parse_price(home.get('price', 0))
                    original_price = self.get_original_price(home)
                    price_cut = self.get_price_cut(home)
                    
                    # Extract address
                    formatted_address = home.get('formatted_address', '')
                    address = formatted_address if formatted_address else home.get('address', '')
                    
                    # Get URL
                    url = home.get('url', '')
                    if url and not url.startswith('http'):
                        url = f"https://www.historymaker.com{url}"
                    
                    # Get availability status
                    status = self.get_status(home)
                    
                    # Use residence name as plan name
                    plan_name = residence_name if residence_name else f"Home {idx+1}"
                    
                    # Validate required fields
                    if not all([plan_name, current_price, sqft, beds, baths, address]):
                        print(f"[HistoryMakerWaldenPondWestNowScraper] Skipping home {idx+1}: Missing required data")
                        print(f"  Plan: {plan_name}, Price: {current_price}, Sqft: {sqft}, Beds: {beds}, Baths: {baths}, Address: {address}")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft else None
                    
                    home_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "History Maker",
                        "community": "Walden Pond West",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": original_price,
                        "price_cut": price_cut,
                        "status": status,
                        "url": url
                    }
                    
                    print(f"[HistoryMakerWaldenPondWestNowScraper] Home {idx+1}: {plan_name} - ${current_price:,} - {sqft:,} sqft - {beds} beds - {baths} baths - {address}")
                    listings.append(home_data)
                    
                except Exception as e:
                    print(f"[HistoryMakerWaldenPondWestNowScraper] Error processing home {idx+1}: {e}")
                    continue
            
            print(f"[HistoryMakerWaldenPondWestNowScraper] Successfully processed {len(listings)} homes")
            return listings
            
        except requests.exceptions.RequestException as e:
            print(f"[HistoryMakerWaldenPondWestNowScraper] Request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"[HistoryMakerWaldenPondWestNowScraper] Error decoding JSON: {e}")
            return []
        except Exception as e:
            print(f"[HistoryMakerWaldenPondWestNowScraper] An unexpected error occurred: {e}")
            return []
