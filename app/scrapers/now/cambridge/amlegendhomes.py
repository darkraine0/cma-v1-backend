import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class AmericanLegendHomesCambridgeNowScraper(BaseScraper):
    URL = "https://www.amlegendhomes.com/communities/texas/celina/ten-mile-creek"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        match = re.search(r'\$([\d,]+)', text)
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

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def extract_mls(self, card):
        """Extract MLS number from the card."""
        mls_li = card.find('li', class_='HomeCard_link', string=re.compile(r'MLS:'))
        if mls_li:
            mls_text = mls_li.get_text(strip=True)
            mls_match = re.search(r'MLS:\s*(\d+)', mls_text)
            return mls_match.group(1) if mls_match else ""
        return ""

    def extract_floor_plan(self, card):
        """Extract floor plan name from the card."""
        # Look for all HomeCard_link elements and find the one with Floor Plan
        floor_plan_links = card.find_all('li', class_='HomeCard_link')
        for link_li in floor_plan_links:
            link_text = link_li.get_text(strip=True)
            if 'Floor Plan:' in link_text:
                # Try to find a link first
                floor_plan_link = link_li.find('a')
                if floor_plan_link:
                    return floor_plan_link.get_text(strip=True)
                else:
                    # If no link, extract from the text
                    plan_name = link_text.replace('Floor Plan:', '').strip()
                    return plan_name
        return ""

    def extract_community(self, card):
        """Extract community name from the card."""
        # Look for all HomeCard_link elements and find the one with Community
        community_links = card.find_all('li', class_='HomeCard_link')
        for link_li in community_links:
            link_text = link_li.get_text(strip=True)
            if 'Community:' in link_text:
                # Try to find a link first
                community_link = link_li.find('a')
                if community_link:
                    return community_link.get_text(strip=True)
                else:
                    # If no link, extract from the text
                    community_name = link_text.replace('Community:', '').strip()
                    return community_name
        return ""

    def extract_status(self, card):
        """Extract availability status from the card."""
        status_span = card.find('span', class_='HomeCard_priceStatus')
        if status_span:
            return status_span.get_text(strip=True)
        return ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[AmericanLegendHomesCambridgeNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[AmericanLegendHomesCambridgeNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[AmericanLegendHomesCambridgeNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all home cards
            home_cards = soup.find_all('div', class_='css-1j4dvj6')
            print(f"[AmericanLegendHomesCambridgeNowScraper] Found {len(home_cards)} home cards")
            
            for idx, card in enumerate(home_cards):
                try:
                    print(f"[AmericanLegendHomesCambridgeNowScraper] Processing card {idx+1}")
                    
                    # Extract address
                    title_link = card.find('a', class_='HomeCard_title')
                    if not title_link:
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Skipping card {idx+1}: No title link found")
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
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Skipping card {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price
                    price_span = card.find('span', class_='HomeCard_price')
                    if not price_span:
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_span.get_text())
                    if not current_price:
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract status
                    status = self.extract_status(card)
                    
                    # Extract floor plan
                    floor_plan = self.extract_floor_plan(card)
                    
                    # Extract community
                    community = self.extract_community(card)
                    
                    # Extract MLS
                    mls = self.extract_mls(card)
                    
                    # Extract home details (stories, beds, baths, sqft)
                    detail_list = card.find('ul', class_='HomeCard_list')
                    beds = ""
                    baths = ""
                    stories = ""
                    sqft = None
                    
                    if detail_list:
                        detail_items = detail_list.find_all('li', class_='HomeCard_listItem')
                        for item in detail_items:
                            item_text = item.get_text(strip=True)
                            if 'Stories' in item_text:
                                stories = self.parse_stories(item_text)
                            elif 'Beds' in item_text:
                                beds = self.parse_beds(item_text)
                            elif 'Baths' in item_text:
                                baths = self.parse_baths(item_text)
                            elif 'Sqft' in item_text:
                                sqft = self.parse_sqft(item_text)
                    
                    if not sqft:
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Determine if this is a quick move-in or under construction
                    home_type = "now"
                    if "Under Construction" in status:
                        home_type = "construction"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories or "1",
                        "price_per_sqft": price_per_sqft,
                        "plan_name": floor_plan or address,
                        "company": "American Legend Homes",
                        "community": "Cambridge",
                        "type": home_type,
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "status": status,
                        "mls": mls,
                        "sub_community": community
                    }
                    
                    print(f"[AmericanLegendHomesCambridgeNowScraper] Home {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[AmericanLegendHomesCambridgeNowScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[AmericanLegendHomesCambridgeNowScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[AmericanLegendHomesCambridgeNowScraper] Error: {e}")
            return []
