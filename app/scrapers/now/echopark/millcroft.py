import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class MillcroftEchoParkNowScraper(BaseScraper):
    URL = "https://theprovidencegroup.com/new-homes/ga/buford/millcroft-townhomes/13814/"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        if not text:
            return None
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        if not text:
            return None
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        if not text:
            return ""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        if not text:
            return ""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        # Default to 3 stories for these townhomes based on the data
        return "3"

    def parse_available_homes(self, text):
        """Extract available homes count from text."""
        if not text:
            return ""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_collection_name(self, text):
        """Extract collection name from text."""
        if not text:
            return ""
        # Look for text like "The Glendale" or similar
        match = re.search(r'([A-Za-z\s]+)', text)
        return match.group(1).strip() if match else ""

    def extract_property_data(self, property_card, community_name, city):
        """Extract data from a property card."""
        try:
            # Extract plan name from card title (this is the actual property address)
            plan_name = None
            title_elem = property_card.find('a', class_='card-title')
            if title_elem:
                plan_name = title_elem.get_text(strip=True)

            # Extract city/state from card-address
            address_elem = property_card.find('div', class_='card-address')
            city_state = address_elem.get_text(strip=True) if address_elem else f"{city}, GA"
            
            # Create full address by combining plan_name (property address) with city/state
            address = f"{plan_name}, {city_state}"

            # Extract price
            price = None
            price_elem = property_card.find('div', class_='card-price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self.parse_price(price_text)

            # Extract original price if available
            original_price = None
            old_price_elem = property_card.find('div', class_='spec-old-price')
            if old_price_elem:
                old_price_span = old_price_elem.find('span')
                if old_price_span:
                    original_price = self.parse_price(old_price_span.get_text())

            # Extract sqft, beds, baths from card-stats
            sqft = None
            beds = ""
            baths = ""
            
            stats_section = property_card.find('div', class_='card-stats')
            if stats_section:
                spans = stats_section.find_all('span')
                for span in spans:
                    img = span.find('img')
                    if img and img.get('alt'):
                        alt_text = img.get('alt')
                        span_text = span.get_text(strip=True)
                        
                        if 'Square Feet' in alt_text:
                            sqft = self.parse_sqft(span_text)
                        elif 'Bedrooms' in alt_text:
                            beds = self.parse_beds(span_text)
                        elif 'Baths' in alt_text:
                            baths = self.parse_baths(span_text)

            # Extract stories (default to 3 for townhomes)
            stories = self.parse_stories("")

            # Calculate price per sqft
            price_per_sqft = round(price / sqft, 2) if price and sqft and sqft > 0 else None

            # Extract collection name
            collection_name = ""
            county_elem = property_card.find('div', class_='card-county')
            if county_elem:
                strong_elem = county_elem.find('strong')
                if strong_elem:
                    collection_name = self.parse_collection_name(strong_elem.get_text())

            # Extract price cut information
            price_cut = ""
            flag_elem = property_card.find('div', class_='model-flag')
            if flag_elem and 'bg-blue-cyan' in flag_elem.get('class', []):
                price_cut = flag_elem.get_text(strip=True)

            plan_data = {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "price_per_sqft": price_per_sqft,
                "plan_name": plan_name,
                "company": "Millcroft Townhomes",
                "community": "Echo Park",
                "type": "now",
                "beds": beds,
                "baths": baths,
                "address": address,
                "original_price": original_price,
                "price_cut": price_cut
            }

            # Add collection name if available
            if collection_name:
                plan_data["collection_name"] = collection_name

            return plan_data

        except Exception as e:
            print(f"[MillcroftEchoParkNowScraper] Error extracting property data: {e}")
            return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[MillcroftEchoParkNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[MillcroftEchoParkNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[MillcroftEchoParkNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all swiper slides
            swiper_slides = soup.find_all('div', class_='swiper-slide')
            print(f"[MillcroftEchoParkNowScraper] Found {len(swiper_slides)} swiper slides")
            
            for idx, slide in enumerate(swiper_slides):
                try:
                    print(f"[MillcroftEchoParkNowScraper] Processing slide {idx+1}")
                    
                    # Find property card within the slide
                    property_card = slide.find('div', class_='new-item')
                    if not property_card or 'spec-map-item' not in property_card.get('class', []):
                        print(f"[MillcroftEchoParkNowScraper] Slide {idx+1}: Not a spec-map-item, skipping")
                        continue
                    
                    print(f"[MillcroftEchoParkNowScraper] Slide {idx+1}: Processing property card")
                    
                    # Extract property data
                    plan_data = self.extract_property_data(property_card, "Echo Park", "Buford")
                    
                    if not plan_data:
                        print(f"[MillcroftEchoParkNowScraper] Slide {idx+1}: Failed to extract property data")
                        continue
                    
                    # Check for duplicate addresses
                    if plan_data['address'] in seen_addresses:
                        print(f"[MillcroftEchoParkNowScraper] Slide {idx+1}: Duplicate address '{plan_data['address']}', skipping")
                        continue
                    
                    seen_addresses.add(plan_data['address'])
                    
                    # Validate required fields
                    if not plan_data.get('plan_name') or not plan_data.get('price'):
                        print(f"[MillcroftEchoParkNowScraper] Slide {idx+1}: Missing required fields")
                        continue
                    
                    print(f"[MillcroftEchoParkNowScraper] Slide {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[MillcroftEchoParkNowScraper] Error processing slide {idx+1}: {e}")
                    continue
            
            print(f"[MillcroftEchoParkNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[MillcroftEchoParkNowScraper] Error: {e}")
            return []
