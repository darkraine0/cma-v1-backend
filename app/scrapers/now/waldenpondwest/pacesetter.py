import requests
import re
import json
from ...base import BaseScraper
from typing import List, Dict

class PacesetterWaldenPondWestNowScraper(BaseScraper):
    BASE_URL = "https://www.pacesetterhomestexas.com/api/homes?community=56&available=1&page="
    
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

    def get_status(self, residence):
        """Extract the status of the home."""
        return "available" if residence.get('is_active', 0) == 1 else "unavailable"

    def get_price_cut(self, residence):
        """Extract price cut information if available."""
        return residence.get('promo_text', '')

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[PacesetterWaldenPondWestNowScraper] Fetching residences from API")
            
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
            print(f"[PacesetterWaldenPondWestNowScraper] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[PacesetterWaldenPondWestNowScraper] Request failed with status {response.status_code}")
                return []
            
            first_page_data = response.json()
            last_page = first_page_data.get('last_page', 1)
            total = first_page_data.get('total', 0)
            
            print(f"[PacesetterWaldenPondWestNowScraper] Found {total} residences across {last_page} pages")
            
            all_residences = []
            
            # Fetch all pages
            for page in range(1, last_page + 1):
                print(f"[PacesetterWaldenPondWestNowScraper] Fetching page {page}/{last_page}")
                response = requests.get(self.BASE_URL + str(page), headers=headers, timeout=15)
                
                if response.status_code == 200:
                    page_data = response.json()
                    residences = page_data.get('data', [])
                    all_residences.extend(residences)
                    print(f"[PacesetterWaldenPondWestNowScraper] Page {page}: {len(residences)} residences")
                else:
                    print(f"[PacesetterWaldenPondWestNowScraper] Failed to fetch page {page}: {response.status_code}")
            
            print(f"[PacesetterWaldenPondWestNowScraper] Total residences collected: {len(all_residences)}")
            
            listings = []
            
            for idx, residence in enumerate(all_residences):
                try:
                    # Extract basic information from available homes API
                    address = residence.get('address', '')
                    beds = self.parse_beds(residence.get('beds', ''))
                    baths = self.parse_baths(residence.get('baths', ''))
                    sqft_text = residence.get('sqft', '')
                    sqft = self.parse_sqft(sqft_text)
                    
                    # Extract price from formattedPrice
                    formatted_price = residence.get('formattedPrice', '')
                    price = self.parse_price(formatted_price)
                    
                    # Get URL
                    url = residence.get('url', '')
                    
                    # Get availability status
                    availability = residence.get('formattedAvailability', '')
                    
                    # Generate plan name from address (extract house number and street)
                    plan_name = address if address else f"Home {idx+1}"
                    
                    if not all([address, price, sqft, beds, baths]):
                        print(f"[PacesetterWaldenPondWestNowScraper] Skipping residence {idx+1}: Missing required data")
                        print(f"  Address: {address}, Price: {price}, Sqft: {sqft}, Beds: {beds}, Baths: {baths}")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": self.parse_stories(""),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Pacesetter Homes",
                        "community": "Walden Pond West",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": self.get_price_cut(residence),
                        "status": self.get_status(residence),
                        "url": url
                    }
                    
                    print(f"[PacesetterWaldenPondWestNowScraper] Residence {idx+1}: {address} - ${price:,} - {sqft:,} sqft - {beds} beds - {baths} baths")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[PacesetterWaldenPondWestNowScraper] Error processing residence {idx+1}: {e}")
                    continue
            
            print(f"[PacesetterWaldenPondWestNowScraper] Successfully processed {len(listings)} residences")
            return listings
            
        except Exception as e:
            print(f"[PacesetterWaldenPondWestNowScraper] Error: {e}")
            return []
