import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict
import time

class PerryHomesBrookvilleNowScraper(BaseScraper):
    URL = "https://www.perryhomes.com/new-homes?city=Dallas+-+Fort+Worth&community=Devonshire"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        # Handle both current price and original price
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_original_price(self, text):
        """Extract original price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "3" and "3.5" formats
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract garage capacity from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def get_status(self, container):
        """Extract the status of the home."""
        status_div = container.find('div', class_='grid h-[2.4rem] w-fit place-items-center rounded-full border-[0.1rem] font-body font-medium uppercase subpixel-antialiased px-[1rem] text-[1.2rem] sm:h-[1.632rem] sm:px-[0.68em] sm:text-[0.8rem] md:h-[2.4rem] md:px-[1rem] md:text-[1.2rem] text-chipDefaultTitle bg-chipDefaultBg border-chipDefaultBorder')
        if status_div:
            status_text = status_div.get_text(strip=True).lower()
            if 'move-in ready' in status_text:
                return "move-in ready"
            elif 'under construction' in status_text:
                return "under construction"
            elif 'coming soon' in status_text:
                return "coming soon"
        return "unknown"

    def get_price_cut(self, container):
        """Extract price cut information if available."""
        # Look for original price that's crossed out
        original_price_div = container.find('div', class_='sm:text-[1.0836rem] md:text-[1.6rem] font-body text-[1.6rem] font-extralight line-through')
        if original_price_div:
            original_price = self.parse_original_price(original_price_div.get_text())
            current_price_div = container.find('div', class_='font-headline font-normal text-headlineColor')
            if current_price_div:
                current_price = self.parse_price(current_price_div.get_text())
                if original_price and current_price:
                    price_cut = original_price - current_price
                    return str(price_cut)
        return ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[PerryHomesBrookvilleNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[PerryHomesBrookvilleNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[PerryHomesBrookvilleNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all home listings - Perry Homes uses li elements with specific classes
            home_listings = soup.find_all('li', class_=lambda x: x and 'id' in x)
            print(f"[PerryHomesBrookvilleNowScraper] Found {len(home_listings)} home listings")
            
            for idx, listing in enumerate(home_listings):
                try:
                    print(f"[PerryHomesBrookvilleNowScraper] Processing listing {idx+1}")
                    
                    # Extract address from the address div
                    address_div = listing.find('div', string=re.compile(r'^\d+.*Lane|Drive|Street|Avenue|Road'))
                    if not address_div:
                        # Try alternative approach - look for address in the text
                        address_text = listing.get_text()
                        address_match = re.search(r'(\d+\s+[A-Za-z\s]+(?:Lane|Drive|Street|Avenue|Road))', address_text)
                        if address_match:
                            address = address_match.group(1)
                        else:
                            print(f"[PerryHomesBrookvilleNowScraper] Skipping listing {idx+1}: No address found")
                            continue
                    else:
                        address = address_div.get_text(strip=True)
                    
                    if not address:
                        print(f"[PerryHomesBrookvilleNowScraper] Skipping listing {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[PerryHomesBrookvilleNowScraper] Skipping listing {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract current price
                    price_div = listing.find('div', class_='font-headline font-normal text-headlineColor')
                    if not price_div:
                        print(f"[PerryHomesBrookvilleNowScraper] Skipping listing {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_div.get_text())
                    if not current_price:
                        print(f"[PerryHomesBrookvilleNowScraper] Skipping listing {idx+1}: No current price found")
                        continue
                    
                    # Extract plan name from the community link
                    plan_name = ""
                    community_link = listing.find('a', href=re.compile(r'/devonshire-reserve'))
                    if community_link:
                        plan_name = community_link.get_text(strip=True)
                    else:
                        # Fallback to address-based plan name
                        plan_name_match = re.search(r'(\d+)\s+([A-Za-z]+)', address)
                        plan_name = f"{plan_name_match.group(1)} {plan_name_match.group(2)}" if plan_name_match else address
                    
                    # Extract beds, baths, sqft, stories, and garage from amenities
                    amenities = listing.find_all('div', class_=lambda x: x and 'flex items-center gap-' in x)
                    beds = ""
                    baths = ""
                    sqft = None
                    stories = ""
                    garage = ""
                    
                    for amenity in amenities:
                        amenity_text = amenity.get_text(strip=True)
                        if 'Beds' in amenity_text:
                            beds = self.parse_beds(amenity_text)
                        elif 'Baths' in amenity_text:
                            baths = self.parse_baths(amenity_text)
                        elif 'Sq. Ft.' in amenity_text:
                            sqft = self.parse_sqft(amenity_text)
                        elif 'Stories' in amenity_text:
                            stories = self.parse_stories(amenity_text)
                        elif 'Cars' in amenity_text:
                            garage = self.parse_garage(amenity_text)
                    
                    if not sqft:
                        print(f"[PerryHomesBrookvilleNowScraper] Skipping listing {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Get status and price cut information
                    status = self.get_status(listing)
                    price_cut = self.get_price_cut(listing)
                    
                    # Determine if it's a quick move-in home
                    is_quick_move_in = status == "move-in ready"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories if stories else "1",
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Perry Homes",
                        "community": "Brookville",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,  # Will be calculated if needed
                        "price_cut": price_cut
                    }
                    
                    # Add additional metadata
                    if status:
                        plan_data["status"] = status
                    if garage:
                        plan_data["garage"] = garage
                    
                    print(f"[PerryHomesBrookvilleNowScraper] Listing {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[PerryHomesBrookvilleNowScraper] Error processing listing {idx+1}: {e}")
                    continue
            
            print(f"[PerryHomesBrookvilleNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[PerryHomesBrookvilleNowScraper] Error: {e}")
            return []
