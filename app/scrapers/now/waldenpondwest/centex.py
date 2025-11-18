import requests
import json
from ...base import BaseScraper
from typing import List, Dict

class CentexWaldenPondWestNowScraper(BaseScraper):
    BASE_URL = "https://www.centex.com/api/plan/qmiplans?communityId=211042"
    
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
        date_available = home_data.get('dateAvailable', '')
        if 'Available Now' in date_available:
            return 'available'
        elif 'Coming Soon' in date_available:
            return 'coming_soon'
        else:
            return 'available'  # Default to available
    
    def get_price_cut(self, home_data):
        """Extract price cut information."""
        price_discount = home_data.get('priceDiscount', 0)
        if price_discount and price_discount > 0:
            return f"${price_discount:,}"
        return None
    
    def get_original_price(self, home_data):
        """Get original price before discount."""
        price = home_data.get('price', 0)
        price_discount = home_data.get('priceDiscount', 0)
        if price_discount and price_discount > 0:
            return int(price)
        return None
    
    def fetch_plans(self) -> List[Dict]:
        """Fetch available homes from Centex API."""
        try:
            print(f"[CentexWaldenPondWestNowScraper] Fetching available homes from API")
            
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
            print(f"[CentexWaldenPondWestNowScraper] Response status: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            print(f"[CentexWaldenPondWestNowScraper] Found {len(data)} available homes")
            
            listings = []
            
            for idx, home in enumerate(data):
                try:
                    # Extract basic information
                    plan_name = home.get('planName', '')
                    beds = self.parse_beds(home.get('bedrooms', ''))
                    baths = self.parse_baths(home.get('totalBaths', ''))
                    sqft = self.parse_sqft(home.get('squareFeet', ''))
                    stories = self.parse_stories(home.get('floors', ''))
                    
                    # Extract price information
                    final_price = self.parse_price(home.get('finalPrice', 0))
                    original_price = self.get_original_price(home)
                    price_cut = self.get_price_cut(home)
                    
                    # Extract address
                    address_data = home.get('address', {})
                    street1 = address_data.get('street1', '').strip()
                    city = address_data.get('city', '').strip()
                    state = address_data.get('state', '').strip()
                    zip_code = address_data.get('zipCode', '').strip()
                    
                    # Build full address
                    address_parts = [street1, city, state, zip_code]
                    address = ', '.join([part for part in address_parts if part])
                    
                    # Get URL
                    inventory_url = home.get('inventoryPageURL', '')
                    url = f"https://www.centex.com{inventory_url}" if inventory_url else ""
                    
                    # Get availability status
                    status = self.get_status(home)
                    
                    # Validate required fields
                    if not all([plan_name, final_price, sqft, beds, baths, address]):
                        print(f"[CentexWaldenPondWestNowScraper] Skipping home {idx+1}: Missing required data")
                        print(f"  Plan: {plan_name}, Price: {final_price}, Sqft: {sqft}, Beds: {beds}, Baths: {baths}, Address: {address}")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(final_price / sqft, 2) if sqft else None
                    
                    home_data = {
                        "price": final_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Centex",
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
                    
                    print(f"[CentexWaldenPondWestNowScraper] Home {idx+1}: {plan_name} - ${final_price:,} - {sqft:,} sqft - {beds} beds - {baths} baths - {address}")
                    listings.append(home_data)
                    
                except Exception as e:
                    print(f"[CentexWaldenPondWestNowScraper] Error processing home {idx+1}: {e}")
                    continue
            
            print(f"[CentexWaldenPondWestNowScraper] Successfully processed {len(listings)} homes")
            return listings
            
        except requests.exceptions.RequestException as e:
            print(f"[CentexWaldenPondWestNowScraper] Request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"[CentexWaldenPondWestNowScraper] Error decoding JSON: {e}")
            return []
        except Exception as e:
            print(f"[CentexWaldenPondWestNowScraper] An unexpected error occurred: {e}")
            return []
