import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class PacesetterMilranyNowScraper(BaseScraper):
    URL = "https://www.pacesetterhomestexas.com/new-homes-for-sale-dallas/melissa-tx/meadow-run?community=39"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text."""
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
        # Default to 2 stories for these homes based on the data
        return "2"

    def get_availability_date(self, container):
        """Extract availability date from the availability div."""
        availability_div = container.find('div', class_='home-card__availability')
        if availability_div:
            availability_text = availability_div.get_text(strip=True)
            return self.get_availability_date_from_text(availability_text)
        return "Unknown"
    
    def get_availability_date_from_text(self, availability_text):
        """Extract availability date from text."""
        if not availability_text:
            return "Unknown"
        
        # Extract date from text like "Available Now", "Available September 2025"
        if 'Available Now' in availability_text:
            return "Now"
        elif 'Available' in availability_text:
            # Extract month and year
            date_match = re.search(r'Available\s+(\w+)\s+(\d{4})', availability_text)
            if date_match:
                month = date_match.group(1)
                year = date_match.group(2)
                return f"{month} {year}"
        return "Unknown"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[PacesetterMilranyNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[PacesetterMilranyNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[PacesetterMilranyNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Debug: Save HTML content for inspection
            with open('pacesetter_debug.html', 'w', encoding='utf-8') as f:
                f.write(resp.text)
            print(f"[PacesetterMilranyNowScraper] Saved HTML content to pacesetter_debug.html")
            
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Try to find the qmi-carousel component with embedded data
            qmi_carousel = soup.find('qmi-carousel')
            print(f"[PacesetterMilranyNowScraper] Found qmi-carousel: {qmi_carousel is not None}")
            if qmi_carousel:
                print(f"[PacesetterMilranyNowScraper] qmi-carousel attributes: {qmi_carousel.attrs}")
                # Vue.js uses :qmi-list attribute
                qmi_list_attr = qmi_carousel.get(':qmi-list')
                print(f"[PacesetterMilranyNowScraper] :qmi-list attribute: {qmi_list_attr[:200] if qmi_list_attr else 'None'}...")
            
            if qmi_carousel and qmi_carousel.get(':qmi-list'):
                try:
                    import json
                    # Extract the JSON data from the :qmi-list attribute
                    qmi_list_data = qmi_carousel.get(':qmi-list')
                    # The data is HTML-encoded, so we need to decode it
                    import html
                    decoded_data = html.unescape(qmi_list_data)
                    # Replace escaped forward slashes with regular forward slashes
                    decoded_data = decoded_data.replace('\\/', '/')
                    home_data = json.loads(decoded_data)
                    print(f"[PacesetterMilranyNowScraper] Found {len(home_data)} homes in qmi-list data")
                    
                    # Process the JSON data directly
                    for idx, home in enumerate(home_data):
                        try:
                            print(f"[PacesetterMilranyNowScraper] Processing home {idx+1}")
                            
                            address = home.get('address', '')
                            city_state_zip = home.get('cityStateZip', '')
                            full_address = f"{address}, {city_state_zip}" if city_state_zip else address
                            
                            # Check for duplicate addresses
                            if full_address in seen_addresses:
                                print(f"[PacesetterMilranyNowScraper] Skipping home {idx+1}: Duplicate address '{full_address}'")
                                continue
                            
                            seen_addresses.add(full_address)
                            
                            # Extract price from formattedPrice
                            formatted_price = home.get('formattedPrice', '')
                            current_price = self.parse_price(formatted_price)
                            if not current_price:
                                print(f"[PacesetterMilranyNowScraper] Skipping home {idx+1}: No current price found")
                                continue
                            
                            # Extract other data
                            beds = home.get('beds', '')
                            baths = home.get('baths', '')
                            sqft_text = home.get('sqft', '')
                            sqft = self.parse_sqft(sqft_text) if sqft_text else None
                            
                            if not sqft:
                                print(f"[PacesetterMilranyNowScraper] Skipping home {idx+1}: No square footage found")
                                continue
                            
                            # Calculate price per sqft
                            price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                            
                            # Get availability from formattedAvailability
                            availability_text = home.get('formattedAvailability', '')
                            availability_date = self.get_availability_date_from_text(availability_text)
                            
                            # Create plan name from address (extract street number and name)
                            plan_name_match = re.search(r'(\d+)\s+([A-Za-z]+)', address)
                            plan_name = f"{plan_name_match.group(1)} {plan_name_match.group(2)}" if plan_name_match else address
                            
                            plan_data = {
                                "price": current_price,
                                "sqft": sqft,
                                "stories": self.parse_stories(""),
                                "price_per_sqft": price_per_sqft,
                                "plan_name": plan_name,
                                "company": "Pacesetter Homes",
                                "builder": "Pacesetter Homes",
                                "community": "Milrany",
                                "type": "now",
                                "beds": str(beds),
                                "baths": str(baths),
                                "address": full_address,
                                "original_price": None,
                                "price_cut": ""
                            }
                            
                            # Add availability date if available
                            if availability_date and availability_date != "Unknown":
                                plan_data["availability_date"] = availability_date
                            
                            print(f"[PacesetterMilranyNowScraper] Home {idx+1}: {plan_data}")
                            listings.append(plan_data)
                            
                        except Exception as e:
                            print(f"[PacesetterMilranyNowScraper] Error processing home {idx+1}: {e}")
                            continue
                    
                    print(f"[PacesetterMilranyNowScraper] Successfully processed {len(listings)} homes from JSON data")
                    return listings
                    
                except Exception as e:
                    print(f"[PacesetterMilranyNowScraper] Error parsing JSON data: {e}")
            
            # Fallback to HTML parsing if JSON extraction fails
            print(f"[PacesetterMilranyNowScraper] Falling back to HTML parsing")
            
            # Find all home listings in the splide list
            home_listings = soup.find_all('li', class_='splide__slide')
            print(f"[PacesetterMilranyNowScraper] Found {len(home_listings)} home listings")
            
            # If no listings found, try alternative selectors
            if not home_listings:
                home_listings = soup.find_all('li', attrs={'data-v-7a236e11': True, 'class': 'splide__slide'})
                print(f"[PacesetterMilranyNowScraper] Found {len(home_listings)} home listings with alternative selector")
            
            # If still no listings, try finding any elements with home-card class
            if not home_listings:
                home_cards = soup.find_all('a', class_='home-card')
                print(f"[PacesetterMilranyNowScraper] Found {len(home_cards)} home cards directly")
                if home_cards:
                    # Create a list structure to work with existing code
                    home_listings = [type('obj', (object,), {'find': lambda *args, **kwargs: card})() for card in home_cards]
            
            for idx, listing in enumerate(home_listings):
                try:
                    print(f"[PacesetterMilranyNowScraper] Processing listing {idx+1}")
                    
                    # Find the home card within the slide
                    home_card = listing.find('a', class_='home-card')
                    if not home_card:
                        print(f"[PacesetterMilranyNowScraper] Skipping listing {idx+1}: No home card found")
                        continue
                    
                    # Extract address from the location section
                    location_section = home_card.find('div', class_='home-card__location')
                    if not location_section:
                        print(f"[PacesetterMilranyNowScraper] Skipping listing {idx+1}: No location section found")
                        continue
                    
                    address_div = location_section.find('div', class_='home-card__address')
                    city_div = location_section.find('div', class_='home-card__city')
                    
                    if not address_div:
                        print(f"[PacesetterMilranyNowScraper] Skipping listing {idx+1}: No address found")
                        continue
                    
                    address = address_div.get_text(strip=True)
                    city = city_div.get_text(strip=True) if city_div else ""
                    full_address = f"{address}, {city}" if city else address
                    
                    # Check for duplicate addresses
                    if full_address in seen_addresses:
                        print(f"[PacesetterMilranyNowScraper] Skipping listing {idx+1}: Duplicate address '{full_address}'")
                        continue
                    
                    seen_addresses.add(full_address)
                    
                    # Extract price
                    price_section = home_card.find('div', class_='home-card__price')
                    if not price_section:
                        print(f"[PacesetterMilranyNowScraper] Skipping listing {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_section.get_text())
                    if not current_price:
                        print(f"[PacesetterMilranyNowScraper] Skipping listing {idx+1}: No current price found")
                        continue
                    
                    # Extract beds, baths, and sqft from snapshot section
                    snapshot_section = home_card.find('div', class_='home-card__snapshot')
                    beds = ""
                    baths = ""
                    sqft = None
                    
                    if snapshot_section:
                        attribute_items = snapshot_section.find_all('div', class_='home-card__attribute')
                        for item in attribute_items:
                            attribute_text = item.find('div', class_='home-card__attribute-text')
                            if attribute_text:
                                text_content = attribute_text.get_text(strip=True)
                                if 'Beds' in text_content:
                                    # Extract beds from span content
                                    span = attribute_text.find('span')
                                    if span:
                                        beds = self.parse_beds(span.get_text())
                                elif 'Baths' in text_content:
                                    # Extract baths from span content
                                    span = attribute_text.find('span')
                                    if span:
                                        baths = self.parse_baths(span.get_text())
                                elif 'Sq. Ft.' in text_content:
                                    # Extract square footage from span content
                                    span = attribute_text.find('span')
                                    if span:
                                        sqft = self.parse_sqft(span.get_text())
                    
                    if not sqft:
                        print(f"[PacesetterMilranyNowScraper] Skipping listing {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Get availability date
                    availability_date = self.get_availability_date(home_card)
                    
                    # Create plan name from address (extract street number and name)
                    plan_name_match = re.search(r'(\d+)\s+([A-Za-z]+)', address)
                    plan_name = f"{plan_name_match.group(1)} {plan_name_match.group(2)}" if plan_name_match else address
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": self.parse_stories(""),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Pacesetter Homes",
                        "builder": "Pacesetter Homes",
                        "community": "Milrany",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": full_address,
                        "original_price": None,
                        "price_cut": ""
                    }
                    
                    # Add availability date if available
                    if availability_date and availability_date != "Unknown":
                        plan_data["availability_date"] = availability_date
                    
                    print(f"[PacesetterMilranyNowScraper] Listing {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[PacesetterMilranyNowScraper] Error processing listing {idx+1}: {e}")
                    continue
            
            print(f"[PacesetterMilranyNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[PacesetterMilranyNowScraper] Error: {e}")
            return []

