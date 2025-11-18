import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class ChafinCommunitiesMaddoxNowScraper(BaseScraper):
    URL = "https://www.chafincommunities.com/communities/georgia/jackson/hochston-jackson/rosewood-lakes/"
    
    def parse_price(self, text):
        """Extract price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'<strong>(\d+)</strong>BEDS', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'<strong><strong>(\d+)</strong>\s*</strong>BATHS', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        # Default to 1 story for these homes based on the data
        return "1"

    def get_status(self, listing):
        """Extract status from callout divs."""
        callouts = listing.find_all('div', class_=['callout1', 'callout2', 'callout3'])
        statuses = []
        
        for callout in callouts:
            status_text = callout.get_text(strip=True)
            if status_text:
                statuses.append(status_text)
        
        return ", ".join(statuses) if statuses else "Active"

    def get_plan_name(self, listing):
        """Extract plan name from the listing."""
        # Look for plan name in the right side div
        right_div = listing.find('div', class_='grid-40 mobile-grid-40 grid-parent')
        if right_div:
            # Extract plan name from text like "Stanford Plan"
            plan_text = right_div.get_text(strip=True)
            plan_match = re.search(r'([A-Za-z]+)\s+Plan', plan_text)
            if plan_match:
                plan_name = plan_match.group(1)
                # Remove any leading 'A' prefix if it exists
                if plan_name.startswith('A') and len(plan_name) > 1:
                    plan_name = plan_name[1:]
                return plan_name
        
        # Fallback to lot number
        lot_attr = listing.get('data-lot', '')
        if lot_attr:
            return f"Lot {lot_attr}"
        
        return "Unknown Plan"

    def get_address(self, listing):
        """Extract full address from the listing."""
        # Look for address in the left side div
        left_div = listing.find('div', class_='grid-60 mobile-grid-60 grid-parent')
        if left_div:
            address_p = left_div.find('p')
            if address_p:
                address_text = address_p.get_text(strip=True).replace('\n', ' ')
                # Fix spacing issues - add space before city/state if missing
                address_text = re.sub(r'([a-zA-Z])([A-Z][a-z]+ GA)', r'\1, \2', address_text)
                return address_text
        
        return "Address not found"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[ChafinCommunitiesMaddoxNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[ChafinCommunitiesMaddoxNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[ChafinCommunitiesMaddoxNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find the available homes wrapper
            available_homes_wrapper = soup.find('div', class_='single_community_available_homes_wrapper')
            if not available_homes_wrapper:
                print(f"[ChafinCommunitiesMaddoxNowScraper] Available homes wrapper not found")
                return []
            
            # Find all home listings
            home_listings = available_homes_wrapper.find_all('div', class_='single_community_available_homes_listing')
            print(f"[ChafinCommunitiesMaddoxNowScraper] Found {len(home_listings)} home listings")
            
            for idx, listing in enumerate(home_listings):
                try:
                    print(f"[ChafinCommunitiesMaddoxNowScraper] Processing listing {idx+1}")
                    
                    # Extract address
                    address = self.get_address(listing)
                    if not address or address == "Address not found":
                        print(f"[ChafinCommunitiesMaddoxNowScraper] Skipping listing {idx+1}: No address found")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[ChafinCommunitiesMaddoxNowScraper] Skipping listing {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price
                    price_h2 = listing.find('h2')
                    if not price_h2:
                        print(f"[ChafinCommunitiesMaddoxNowScraper] Skipping listing {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_h2.get_text())
                    if not current_price:
                        print(f"[ChafinCommunitiesMaddoxNowScraper] Skipping listing {idx+1}: No current price found")
                        continue
                    
                    # Extract beds and baths from details section
                    details_section = listing.find('div', class_='single_community_available_homes_listing_details')
                    beds = ""
                    baths = ""
                    
                    if details_section:
                        details_html = str(details_section)
                        beds = self.parse_beds(details_html)
                        baths = self.parse_baths(details_html)
                    
                    # For Chafin Communities, we don't have square footage in the provided HTML
                    # We'll set it to None and let the system handle it
                    sqft = None
                    
                    # Calculate price per sqft (will be None if sqft is None)
                    price_per_sqft = round(current_price / sqft, 2) if sqft and sqft > 0 else None
                    
                    # Get status and plan name
                    status = self.get_status(listing)
                    plan_name = self.get_plan_name(listing)
                    
                    # Extract lot number
                    lot_number = listing.get('data-lot', '')
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": self.parse_stories(""),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Chafin Communities",
                        "community": "Maddox",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": ""
                    }
                    
                    # Add additional metadata
                    if status:
                        plan_data["status"] = status
                    if lot_number:
                        plan_data["lot_number"] = lot_number
                    
                    print(f"[ChafinCommunitiesMaddoxNowScraper] Listing {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[ChafinCommunitiesMaddoxNowScraper] Error processing listing {idx+1}: {e}")
                    continue
            
            print(f"[ChafinCommunitiesMaddoxNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[ChafinCommunitiesMaddoxNowScraper] Error: {e}")
            return []
