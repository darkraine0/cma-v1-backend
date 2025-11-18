import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class BloomfieldMilranyNowScraper(BaseScraper):
    URL = "https://www.bloomfieldhomes.com/new-homes/tx/melissa/legacy-ranch/"
    
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

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        # Default to 2 stories for these homes based on the data
        return "2"

    def get_status(self, container):
        """Extract status from the spec banners."""
        status_banners = container.find_all('div', class_='card-banner')
        for banner in status_banners:
            banner_text = banner.get_text(strip=True)
            if 'Model Home For Sale' in banner_text:
                return "Model Home For Sale"
            elif 'Move-In Ready' in banner_text:
                return "Move-In Ready"
            elif 'Under Contract' in banner_text:
                return "Under Contract"
        return "Available"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[BloomfieldMilranyNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[BloomfieldMilranyNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[BloomfieldMilranyNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all spec card containers
            spec_cards = soup.find_all('div', class_='spec-card-vertical')
            print(f"[BloomfieldMilranyNowScraper] Found {len(spec_cards)} spec cards")
            
            for idx, card in enumerate(spec_cards):
                try:
                    print(f"[BloomfieldMilranyNowScraper] Processing card {idx+1}")
                    
                    # Extract address from the card heading
                    heading_link = card.find('p', class_='card-heading').find('a')
                    if not heading_link:
                        print(f"[BloomfieldMilranyNowScraper] Skipping card {idx+1}: No heading link found")
                        continue
                    
                    address = heading_link.get_text(strip=True)
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[BloomfieldMilranyNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract location information
                    subheading = card.find('p', class_='card-subheading')
                    city_state_zip = ""
                    community = ""
                    
                    if subheading:
                        # Extract city, state, zip
                        location_text = subheading.get_text(strip=True)
                        city_state_zip = location_text.split('\n')[0] if '\n' in location_text else location_text
                        
                        # Extract community from child location link
                        community_link = subheading.find('a', class_='child-location-link')
                        if community_link:
                            community = community_link.get_text(strip=True)
                    
                    full_address = f"{address}, {city_state_zip}" if city_state_zip else address
                    
                    # Extract floor plan name
                    plan_link = card.find('a', class_='plan-link')
                    plan_name = plan_link.get_text(strip=True) if plan_link else "Unknown Plan"
                    
                    # Extract price information
                    price_section = card.find('div', class_='d-flex justify-content-between align-items-center')
                    current_price = None
                    original_price = None
                    price_cut = ""
                    
                    if price_section:
                        # Look for current price
                        current_price_elem = price_section.find('p', class_='card-price')
                        if current_price_elem and not current_price_elem.find('s'):  # Not a strikethrough price
                            current_price = self.parse_price(current_price_elem.get_text())
                        
                        # Look for original price (strikethrough)
                        old_price_elem = price_section.find('p', class_='old-price')
                        if old_price_elem:
                            original_price = self.parse_price(old_price_elem.get_text())
                        
                        # If no current price found in main section, look for it in the flex container
                        if not current_price:
                            price_labels = price_section.find_all('p', class_='card-price-label')
                            for label in price_labels:
                                if 'Now' in label.get_text():
                                    # Find the next price element
                                    next_price = label.find_next_sibling('p', class_='card-price')
                                    if next_price:
                                        current_price = self.parse_price(next_price.get_text())
                                        break
                    
                    # If still no current price, look for "UNDER CONTRACT" or similar
                    if not current_price:
                        contract_text = price_section.find('p', class_='card-price')
                        if contract_text and 'UNDER CONTRACT' in contract_text.get_text():
                            current_price = 0  # Mark as under contract
                    
                    if not current_price and current_price != 0:
                        print(f"[BloomfieldMilranyNowScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract stats (sqft, beds, baths, garage)
                    stats_list = card.find('ul', class_='spec-card-stats')
                    sqft = None
                    beds = ""
                    baths = ""
                    garage = ""
                    
                    if stats_list:
                        stat_items = stats_list.find_all('li')
                        for item in stat_items:
                            stat_value = item.find('p', class_='stat-value')
                            stat_label = item.find('p', class_='h6')
                            
                            if stat_value and stat_label:
                                value_text = stat_value.get_text(strip=True)
                                label_text = stat_label.get_text(strip=True)
                                
                                if 'Square Feet' in label_text:
                                    sqft = self.parse_sqft(value_text)
                                elif 'Bedrooms' in label_text:
                                    beds = self.parse_beds(value_text)
                                elif 'Bathrooms' in label_text:
                                    baths = self.parse_baths(value_text)
                                elif 'Car Garage' in label_text:
                                    garage = self.parse_garage(value_text)
                    
                    if not sqft:
                        print(f"[BloomfieldMilranyNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if current_price and sqft > 0 else None
                    
                    # Get status
                    status = self.get_status(card)
                    
                    # Calculate price cut if original price exists
                    if original_price and current_price and current_price > 0:
                        price_cut_amount = original_price - current_price
                        price_cut = f"${price_cut_amount:,}"
                    
                    # Create plan name from address (extract street number and name)
                    plan_name_match = re.search(r'(\d+)\s+([A-Za-z]+)', address)
                    display_plan_name = f"{plan_name_match.group(1)} {plan_name_match.group(2)}" if plan_name_match else address
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": self.parse_stories(""),
                        "price_per_sqft": price_per_sqft,
                        "plan_name": display_plan_name,
                        "company": "Bloomfield Homes",
                        "builder": "Bloomfield Homes",
                        "community": "Milrany",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": full_address,
                        "original_price": original_price,
                        "price_cut": price_cut,
                        "floor_plan": plan_name,
                        "status": status,
                        "garage": garage
                    }
                    
                    # Add community if available
                    if community:
                        plan_data["sub_community"] = community
                    
                    print(f"[BloomfieldMilranyNowScraper] Card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[BloomfieldMilranyNowScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[BloomfieldMilranyNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[BloomfieldMilranyNowScraper] Error: {e}")
            return []
