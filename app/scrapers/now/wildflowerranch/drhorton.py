import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class DRHortonWildflowerRanchNowScraper(BaseScraper):
    URL = "https://www.drhorton.com/texas/fort-worth/justin/treeline"
    
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
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def get_status(self, price_text):
        """Determine status based on price text."""
        if "Under Contract" in price_text:
            return "under_contract"
        elif "$" in price_text:
            return "available"
        else:
            return "unknown"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DRHortonWildflowerRanchNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DRHortonWildflowerRanchNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[DRHortonWildflowerRanchNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find the available homes section
            available_homes_section = soup.find('div', id='available-homes')
            if not available_homes_section:
                print("[DRHortonWildflowerRanchNowScraper] Could not find available homes section")
                return []
            
            # Find all home cards
            home_cards = available_homes_section.find_all('div', class_='toggle-item')
            print(f"[DRHortonWildflowerRanchNowScraper] Found {len(home_cards)} home cards")
            
            for idx, card in enumerate(home_cards):
                try:
                    print(f"[DRHortonWildflowerRanchNowScraper] Processing card {idx+1}")
                    
                    # Extract price from h2 element
                    price_elem = card.find('h2')
                    if not price_elem:
                        print(f"[DRHortonWildflowerRanchNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    price_text = price_elem.get_text(strip=True)
                    current_price = self.parse_price(price_text)
                    status = self.get_status(price_text)
                    
                    # Skip if under contract (unless we want to track those too)
                    if status == "under_contract":
                        print(f"[DRHortonWildflowerRanchNowScraper] Skipping card {idx+1}: Under contract")
                        continue
                    
                    if not current_price:
                        print(f"[DRHortonWildflowerRanchNowScraper] Skipping card {idx+1}: No valid price found")
                        continue
                    
                    # Extract address from h3 element
                    address_elem = card.find('h3')
                    if not address_elem:
                        print(f"[DRHortonWildflowerRanchNowScraper] Skipping card {idx+1}: No address found")
                        continue
                    
                    address = address_elem.get_text(strip=True)
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[DRHortonWildflowerRanchNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract property details from p elements
                    p_elements = card.find_all('p')
                    beds = ""
                    baths = ""
                    sqft = None
                    stories = "1"  # Default
                    lot_number = ""
                    
                    for p_elem in p_elements:
                        p_text = p_elem.get_text(strip=True)
                        
                        # Look for beds/baths/garage pattern
                        if "Bed" in p_text and "Bath" in p_text:
                            # Extract beds
                            beds_match = re.search(r'(\d+(?:\.\d+)?)\s*Bed', p_text)
                            if beds_match:
                                beds = beds_match.group(1)
                            
                            # Extract baths
                            baths_match = re.search(r'(\d+(?:\.\d+)?)\s*Bath', p_text)
                            if baths_match:
                                baths = baths_match.group(1)
                        
                        # Look for story/sqft/lot pattern
                        elif "Story" in p_text and "Sq. Ft." in p_text:
                            # Extract stories
                            stories_match = re.search(r'(\d+)\s*Story', p_text)
                            if stories_match:
                                stories = stories_match.group(1)
                            
                            # Extract sqft
                            sqft_match = re.search(r'([\d,]+)\s*Sq\.\s*Ft\.', p_text)
                            if sqft_match:
                                sqft = self.parse_sqft(sqft_match.group(1))
                            
                            # Extract lot number
                            lot_match = re.search(r'Lot\s+(\w+)', p_text)
                            if lot_match:
                                lot_number = lot_match.group(1)
                    
                    if not sqft:
                        print(f"[DRHortonWildflowerRanchNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Extract property URL
                    link_elem = card.find('a', class_='CoveoResultLink')
                    property_url = link_elem.get('href') if link_elem else None
                    if property_url and not property_url.startswith('http'):
                        property_url = f"https://www.drhorton.com{property_url}"
                    
                    # Generate plan name from address (remove numbers and clean up)
                    plan_name = re.sub(r'^\d+\s+', '', address).title()
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "DR Horton",
                        "community": "Wildflower Ranch",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "status": status,
                        "lot_number": lot_number,
                        "url": property_url
                    }
                    
                    print(f"[DRHortonWildflowerRanchNowScraper] Card {idx+1}: {plan_data['plan_name']} - ${current_price:,} - {sqft:,} sqft - {status}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[DRHortonWildflowerRanchNowScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[DRHortonWildflowerRanchNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[DRHortonWildflowerRanchNowScraper] Error: {e}")
            return []
