import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class BrightlandHomesCambridgePlanScraper(BaseScraper):
    URL = "https://www.brightlandhomes.com/new-homes/texas/dallas/green-meadows"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract starting price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def extract_floor_plan(self, card):
        """Extract floor plan name from the card."""
        floor_plan_div = card.find('div', class_='Inventory-card_cardTitle__sfWte')
        if floor_plan_div:
            # The format is "Series - Plan Name" or "Plan Name - Series"
            text = floor_plan_div.get_text(strip=True)
            return text
        return ""

    def extract_floor_plan_series(self, card):
        """Extract floor plan series from the card."""
        floor_plan_div = card.find('div', class_='Inventory-card_cardTitle__sfWte')
        if floor_plan_div:
            text = floor_plan_div.get_text(strip=True)
            # Split by " - " and take the first part as the series
            if " - " in text:
                return text.split(" - ")[0].strip()
            return ""
        return ""

    def extract_floor_plan_name(self, card):
        """Extract floor plan name from the card."""
        floor_plan_div = card.find('div', class_='Inventory-card_cardTitle__sfWte')
        if floor_plan_div:
            text = floor_plan_div.get_text(strip=True)
            # Split by " - " and take the second part as the plan name
            if " - " in text:
                parts = text.split(" - ")
                if len(parts) >= 2:
                    return parts[1].strip()
            return ""
        return ""

    def extract_status(self, card):
        """Extract availability status from the card."""
        status_div = card.find('div', class_='Inventory-card_availableDate__L1U8m')
        if status_div:
            return status_div.get_text(strip=True)
        return ""

    def extract_address(self, card):
        """Extract address from the card."""
        # Find the address section which contains two divs: street address and city/zip
        address_section = card.find('div', class_='Inventory-card_cardInfo__2nnEn')
        if address_section:
            # Find the divs that contain address information
            address_divs = address_section.find_all('div')
            if len(address_divs) >= 4:  # We expect at least 4 divs in the card info
                # The structure is: title, status, street address, city/zip
                street_address = ""
                city_zip = ""
                
                # Look for the address divs (they come after the title and status)
                for i, div in enumerate(address_divs):
                    div_text = div.get_text(strip=True)
                    # Skip the title and status divs
                    if div_text.startswith('Premier') or div_text.startswith('Classic') or div_text == "Available Now":
                        continue
                    
                    # The first non-title/non-status div should be the street address
                    if not street_address:
                        street_address = div_text
                    # The second non-title/non-status div should be the city/zip
                    elif not city_zip:
                        city_zip = div_text
                        break
                
                if street_address:
                    return street_address
        return ""

    def extract_image_url(self, card):
        """Extract image URL from the card."""
        img_tag = card.find('img')
        if img_tag and img_tag.get('src'):
            return img_tag['src']
        return ""

    def extract_detail_link(self, card):
        """Extract detail link from the card."""
        link_tag = card.find('a')
        if link_tag and link_tag.get('href'):
            href = link_tag['href']
            # Make it absolute URL if it's relative
            if href.startswith('/'):
                return f"https://www.brightlandhomes.com{href}"
            return href
        return ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[BrightlandHomesCambridgePlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[BrightlandHomesCambridgePlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[BrightlandHomesCambridgePlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all home cards - these are inventory cards showing available homes
            home_cards = soup.find_all('div', class_='Inventory-card_card__zCZYC')
            print(f"[BrightlandHomesCambridgePlanScraper] Found {len(home_cards)} home cards")
            
            for idx, card in enumerate(home_cards):
                try:
                    print(f"[BrightlandHomesCambridgePlanScraper] Processing card {idx+1}")
                    
                    # Extract address
                    address = self.extract_address(card)
                    if not address:
                        print(f"[BrightlandHomesCambridgePlanScraper] Skipping card {idx+1}: No address found")
                        continue
                    
                    # Clean up the address - remove city/zip information
                    if 'Celina' in address:
                        address = address.split('Celina')[0].strip()
                    if '75009' in address:
                        address = address.split('75009')[0].strip()
                    # Remove any trailing commas or spaces
                    address = address.rstrip(', ').strip()
                    
                    if not address:
                        print(f"[BrightlandHomesCambridgePlanScraper] Skipping card {idx+1}: Empty address after cleaning")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[BrightlandHomesCambridgePlanScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price
                    price_div = card.find('div', class_='Inventory-card_priceBox__9qHxs')
                    if not price_div:
                        print(f"[BrightlandHomesCambridgePlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_div.get_text())
                    if not current_price:
                        print(f"[BrightlandHomesCambridgePlanScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract status
                    status = self.extract_status(card)
                    
                    # Extract floor plan and type
                    floor_plan = self.extract_floor_plan(card)
                    floor_plan_series = self.extract_floor_plan_series(card)
                    floor_plan_name = self.extract_floor_plan_name(card)
                    
                    # Extract home details (beds, baths, garage, sqft)
                    detail_list = card.find('div', class_='Inventory-card_roomDetails__0id2t')
                    beds = ""
                    baths = ""
                    garage = ""
                    sqft = None
                    
                    if detail_list:
                        detail_items = detail_list.find_all('div', class_='Inventory-card_roomDetail__dVHSI')
                        for item in detail_items:
                            # The structure has icons followed by text, so we need to get the text content
                            text_content = item.find('p')
                            if text_content:
                                text_value = text_content.get_text(strip=True)
                                # Determine the type based on position since the structure is consistent
                                if len(detail_items) >= 4:
                                    if detail_items.index(item) == 0:  # First item is beds
                                        beds = self.parse_beds(text_value)
                                    elif detail_items.index(item) == 1:  # Second item is baths
                                        baths = self.parse_baths(text_value)
                                    elif detail_items.index(item) == 2:  # Third item is garage
                                        garage = self.parse_garage(text_value)
                                    elif detail_items.index(item) == 3:  # Fourth item is sqft
                                        sqft = self.parse_sqft(text_value)
                    
                    if not sqft:
                        print(f"[BrightlandHomesCambridgePlanScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Determine stories based on floor plan series
                    stories = "2"  # Most Brightland homes in Cambridge are 2-story
                    if floor_plan_series in ["Premier", "Classic"]:
                        stories = "2"
                    else:
                        stories = "1"
                    
                    # Extract image URL and detail link
                    image_url = self.extract_image_url(card)
                    detail_link = self.extract_detail_link(card)
                    
                    # Determine if this is a quick move-in or under construction
                    home_type = "now"
                    if "Under Construction" in status or "Coming Soon" in status:
                        home_type = "construction"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": floor_plan or address,
                        "company": "Brightland Homes",
                        "community": "Cambridge",
                        "type": home_type,
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "status": status,
                        "mls": "",
                        "sub_community": floor_plan_series or "Green Meadows",
                        "image_url": image_url,
                        "detail_link": detail_link
                    }
                    
                    print(f"[BrightlandHomesCambridgePlanScraper] Home {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[BrightlandHomesCambridgePlanScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[BrightlandHomesCambridgePlanScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[BrightlandHomesCambridgePlanScraper] Error: {e}")
            return []
