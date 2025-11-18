import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class TrophySignatureCambridgeNowScraper(BaseScraper):
    URL = "https://trophysignaturehomes.com/communities/dallas-ft-worth/celina/cross-creek-meadows"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_original_price(self, text):
        """Extract original price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price_cut(self, text):
        """Extract price cut amount from text."""
        match = re.search(r'Save:\s*\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:-\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "3" and "3.5" formats
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def extract_floor_plan(self, card):
        """Extract floor plan name from the card."""
        floor_plan_links = card.find_all('span', class_='HomeCard_link')
        for link_span in floor_plan_links:
            link_text = link_span.get_text(strip=True)
            if 'Floor Plan' in link_text:
                # Try to find a link first
                floor_plan_link = link_span.find('a')
                if floor_plan_link:
                    return floor_plan_link.get_text(strip=True)
                else:
                    # If no link, extract from the text
                    plan_name = link_text.replace('Floor Plan', '').strip()
                    return plan_name
        return ""

    def extract_community(self, card):
        """Extract community name from the card."""
        community_links = card.find_all('span', class_='HomeCard_link')
        for link_span in community_links:
            link_text = link_span.get_text(strip=True)
            if 'Community' in link_text:
                # Try to find a link first
                community_link = link_span.find('a')
                if community_link:
                    return community_link.get_text(strip=True)
                else:
                    # If no link, extract from the text
                    community_name = link_text.replace('Community', '').strip()
                    return community_name
        return ""

    def extract_status(self, card):
        """Extract availability status from the card."""
        # Look for the Available Date information
        detail_list = card.find('ul', class_='HomeCard_list')
        if detail_list:
            detail_items = detail_list.find_all('li')
            for item in detail_items:
                item_text = item.get_text(strip=True)
                if 'Available Date:' in item_text:
                    # Extract the date part after "Available Date:"
                    date_part = item_text.split('Available Date:')[-1].strip()
                    return date_part
        return "Now"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[TrophySignatureCambridgeNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[TrophySignatureCambridgeNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[TrophySignatureCambridgeNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all home cards
            home_cards = soup.find_all('div', class_='card_wrapper')
            print(f"[TrophySignatureCambridgeNowScraper] Found {len(home_cards)} home cards")
            
            for idx, card in enumerate(home_cards):
                try:
                    print(f"[TrophySignatureCambridgeNowScraper] Processing card {idx+1}")
                    
                    # Extract address
                    title_link = card.find('a', class_='HomeCard_title')
                    if not title_link:
                        print(f"[TrophySignatureCambridgeNowScraper] Skipping card {idx+1}: No title link found")
                        continue
                    
                    # Get the full text and extract just the address part
                    full_title_text = title_link.get_text(strip=True)
                    # The address is typically the first part before any comma
                    address_parts = full_title_text.split(',')
                    if len(address_parts) >= 2:
                        address = address_parts[0].strip()
                        # Remove any trailing "Celina" or other city names that might be attached
                        if address.endswith('Celina'):
                            address = address[:-6].strip()
                        elif address.endswith('TX'):
                            address = address[:-2].strip()
                        elif address.endswith('75009'):
                            address = address[:-5].strip()
                    else:
                        address = full_title_text
                    
                    if not address:
                        print(f"[TrophySignatureCambridgeNowScraper] Skipping card {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[TrophySignatureCambridgeNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract current price
                    current_price_span = card.find('div', class_='Current_price')
                    if not current_price_span:
                        print(f"[TrophySignatureCambridgeNowScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    current_price = self.parse_price(current_price_span.get_text())
                    if not current_price:
                        print(f"[TrophySignatureCambridgeNowScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract original price and price cut
                    original_price = None
                    price_cut = None
                    prev_price_div = card.find('div', class_='Prev_price')
                    if prev_price_div:
                        prev_price_text = prev_price_div.get_text(strip=True)
                        original_price = self.parse_original_price(prev_price_text)
                        price_cut = self.parse_price_cut(prev_price_text)
                    
                    # Extract status
                    status = self.extract_status(card)
                    
                    # Extract floor plan
                    floor_plan = self.extract_floor_plan(card)
                    
                    # Extract community
                    community = self.extract_community(card)
                    
                    # Extract home details (beds, baths, sqft)
                    detail_list = card.find('ul', class_='HomeCard_list')
                    beds = ""
                    baths = ""
                    sqft = None
                    
                    if detail_list:
                        detail_items = detail_list.find_all('li')
                        for item in detail_items:
                            item_text = item.get_text(strip=True)
                            if 'Beds' in item_text:
                                beds = self.parse_beds(item_text)
                            elif 'Baths' in item_text:
                                baths = self.parse_baths(item_text)
                            elif 'SQ FT' in item_text:
                                sqft = self.parse_sqft(item_text)
                    
                    if not sqft:
                        print(f"[TrophySignatureCambridgeNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Determine if this is a quick move-in or under construction
                    home_type = "now"
                    if "Under Construction" in status or "Construction" in status:
                        home_type = "construction"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": "1",  # Default to 1 story for Trophy Signature
                        "price_per_sqft": price_per_sqft,
                        "plan_name": floor_plan or address,
                        "company": "Trophy Signature Homes",
                        "community": "Cambridge",
                        "type": home_type,
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": original_price,
                        "price_cut": f"${price_cut:,}" if price_cut else "",
                        "status": status,
                        "mls": "",  # No MLS information in the provided HTML
                        "sub_community": community
                    }
                    
                    print(f"[TrophySignatureCambridgeNowScraper] Home {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[TrophySignatureCambridgeNowScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[TrophySignatureCambridgeNowScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[TrophySignatureCambridgeNowScraper] Error: {e}")
            return []
