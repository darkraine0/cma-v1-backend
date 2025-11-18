import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class EastwoodHomesMaddoxNowScraper(BaseScraper):
    URL = "https://www.eastwoodhomes.com/atlanta/hoschton/twin-lakes"
    
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
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        if "Finished Basement" in text or "Walk-out Basement" in text:
            return "2 + Finished Basement"
        elif "Walk-out Basement" in text:
            return "2 + Walk-out Basement"
        else:
            match = re.search(r'(\d+)', text)
            return str(match.group(1)) if match else "2"

    def get_status(self, container):
        """Extract the status of the home."""
        status_elements = container.find_all('div', class_='e-status')
        for status_elem in status_elements:
            status_text = status_elem.get_text(strip=True).lower()
            if 'ready now' in status_text:
                return "ready now"
            elif 'under construction' in status_text:
                return "under construction"
            elif 'coming soon' in status_text:
                return "coming soon"
        return "unknown"

    def get_site_number(self, container):
        """Extract site number from status elements."""
        status_elements = container.find_all('div', class_='e-status')
        for status_elem in status_elements:
            status_text = status_elem.get_text(strip=True)
            if 'Site' in status_text:
                match = re.search(r'Site (\d+)', status_text)
                return match.group(1) if match else ""
        return ""

    def is_twin_lakes_home(self, card):
        """Check if this is a Twin Lakes home (not other communities)."""
        # Look for links that contain 'twin-lakes' in the href
        links = card.find_all('a')
        for link in links:
            href = link.get('href', '')
            if 'twin-lakes' in href:
                return True
        return False

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[EastwoodHomesMaddoxNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[EastwoodHomesMaddoxNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[EastwoodHomesMaddoxNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all home cards - both featured and regular housing cards
            featured_cards = soup.find_all('div', class_='s-card-featured')
            housing_cards = soup.find_all('div', class_='s-card-housing')
            
            all_cards = featured_cards + housing_cards
            print(f"[EastwoodHomesMaddoxNowScraper] Found {len(all_cards)} home cards")
            
            for idx, card in enumerate(all_cards):
                try:
                    print(f"[EastwoodHomesMaddoxNowScraper] Processing card {idx+1}")
                    
                    # Skip sold homes
                    if card.find('div', class_='s-card-housing__sold'):
                        print(f"[EastwoodHomesMaddoxNowScraper] Skipping card {idx+1}: Sold home")
                        continue
                    
                    # Only process Twin Lakes homes
                    if not self.is_twin_lakes_home(card):
                        print(f"[EastwoodHomesMaddoxNowScraper] Skipping card {idx+1}: Not a Twin Lakes home")
                        continue
                    
                    # Extract plan name
                    plan_name_elem = card.find('p', class_='e-card-caption__heading')
                    if not plan_name_elem:
                        print(f"[EastwoodHomesMaddoxNowScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    plan_name = plan_name_elem.get_text(strip=True)
                    if not plan_name:
                        print(f"[EastwoodHomesMaddoxNowScraper] Skipping card {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[EastwoodHomesMaddoxNowScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract price - try different selectors
                    price = None
                    price_elem = card.find('p', class_='e-card-caption__subheading')
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self.parse_price(price_text)
                    
                    # If not found in subheading, try price tag
                    if not price:
                        price_tag = card.find('span', class_='s-card-housing__price-tag')
                        if price_tag:
                            price_text = price_tag.get_text(strip=True)
                            price = self.parse_price(price_text)
                    
                    if not price:
                        print(f"[EastwoodHomesMaddoxNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract square footage - look for the specific square footage element
                    sqft = None
                    
                    # First try to find square footage in the prominent features area
                    prominent_features = card.find('div', class_='e-card-caption__features__item--prominent')
                    if prominent_features:
                        sqft_elem = prominent_features.find('span', class_='e-spec__content')
                        if sqft_elem:
                            sqft_text = sqft_elem.get_text(strip=True)
                            sqft = self.parse_sqft(sqft_text)
                    
                    # If not found, look in all spec content elements
                    if not sqft:
                        sqft_elements = card.find_all('span', class_='e-spec__content')
                        for sqft_elem in sqft_elements:
                            sqft_text = sqft_elem.get_text(strip=True)
                            # Check if this element contains square footage (has "sq ft" or just numbers)
                            if 'sq ft' in sqft_text.lower() or (sqft_text.isdigit() and len(sqft_text) >= 3):
                                sqft = self.parse_sqft(sqft_text)
                                if sqft:
                                    break
                    
                    # If still not found, search in the entire card text for "sq ft" pattern
                    if not sqft:
                        card_text = card.get_text()
                        import re
                        sqft_match = re.search(r'(\d{3,4})\s*sq\s*ft', card_text, re.IGNORECASE)
                        if sqft_match:
                            sqft = int(sqft_match.group(1))
                    
                    if not sqft:
                        print(f"[EastwoodHomesMaddoxNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Extract beds, baths, stories, and garage from specs
                    beds = ""
                    baths = ""
                    stories = "2"  # Default
                    garage = ""
                    
                    spec_items = card.find_all('li', class_='e-desc-list-specs__list__item')
                    for spec_item in spec_items:
                        spec_text = spec_item.get_text(strip=True)
                        if 'Bedrooms' in spec_text:
                            beds = self.parse_beds(spec_text)
                        elif 'Full-Baths' in spec_text:
                            baths = self.parse_baths(spec_text)
                        elif 'Half-Baths' in spec_text:
                            # Add half bath to full baths
                            half_bath = self.parse_baths(spec_text)
                            if half_bath and baths:
                                try:
                                    full_baths = float(baths)
                                    half_baths = float(half_bath)
                                    baths = str(full_baths + half_baths)
                                except:
                                    pass
                        elif 'Stories' in spec_text:
                            stories = self.parse_stories(spec_text)
                        elif 'Garage' in spec_text:
                            garage = self.parse_beds(spec_text)  # Same parsing logic
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                    
                    # Get status and site number
                    status = self.get_status(card)
                    site_number = self.get_site_number(card)
                    
                    # Create address from plan name and site number
                    address = f"{plan_name} - Site {site_number}" if site_number else plan_name
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Eastwood Homes",
                        "community": "Maddox",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "garage": garage,
                        "site_number": site_number
                    }
                    
                    # Add additional metadata
                    if status:
                        plan_data["status"] = status
                    
                    print(f"[EastwoodHomesMaddoxNowScraper] Card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[EastwoodHomesMaddoxNowScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[EastwoodHomesMaddoxNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[EastwoodHomesMaddoxNowScraper] Error: {e}")
            return []
