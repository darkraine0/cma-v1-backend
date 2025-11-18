import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class CoventryCambridgeNowScraper(BaseScraper):
    URL = "https://www.coventryhomes.com/new-homes/tx/celina/cambridge-crossing/"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        # Look for the current price (not the strikethrough price)
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_original_price(self, text):
        """Extract original price from strikethrough text."""
        # Look for the strikethrough price (was price)
        match = re.search(r'Was \$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "2" and "2/1" formats
        match = re.search(r'(\d+(?:/\d+)?)', text)
        return str(match.group(1)) if match else ""

    def is_quick_move_in(self, card):
        """Check if this model card represents a quick move-in home (not a floor plan)."""
        # Quick move-in homes have addresses in the price bar, not model names
        # Floor plans have model names like "Aurora", "Bishop", etc.
        price_bar = card.find('a', class_='price-bar')
        if not price_bar:
            return False
        
        # Check if the first div contains an address pattern (street number + street name)
        address_div = price_bar.find('div')
        if not address_div:
            return False
        
        address_text = address_div.get_text(strip=True)
        
        # Look for address pattern: number + street name + any street type
        # This is more inclusive to catch addresses like "2720 Holland Court"
        address_pattern = r'^\d+\s+[A-Za-z\s]+(?:Ln|Ct|St|Dr|Ave|Blvd|Way|Pl|Cir|Court|Drive|Lane|Street|Road|Boulevard|Avenue|Place|Circle)\.?$'
        
        # Also check if it contains a number and looks like an address (not a model name)
        has_number = bool(re.search(r'^\d+', address_text))
        has_street_like_text = bool(re.search(r'[A-Za-z\s]+(?:Ln|Ct|St|Dr|Ave|Blvd|Way|Pl|Cir|Court|Drive|Lane|Street|Road|Boulevard|Avenue|Place|Circle)', address_text))
        
        # If it has a number and street-like text, it's likely an address
        return has_number and has_street_like_text

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[CoventryCambridgeNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[CoventryCambridgeNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[CoventryCambridgeNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all model cards - these are the quick move-in homes
            model_cards = soup.find_all('div', class_='model-card')
            print(f"[CoventryCambridgeNowScraper] Found {len(model_cards)} total model cards")
            
            for idx, card in enumerate(model_cards):
                try:
                    print(f"[CoventryCambridgeNowScraper] Processing model card {idx+1}")
                    
                    # Check if this is actually a quick move-in home (not a floor plan)
                    if not self.is_quick_move_in(card):
                        print(f"[CoventryCambridgeNowScraper] Skipping card {idx+1}: Not a quick move-in home (likely floor plan)")
                        continue
                    
                    # Extract address from the price bar
                    price_bar = card.find('a', class_='price-bar')
                    if not price_bar:
                        print(f"[CoventryCambridgeNowScraper] Skipping card {idx+1}: No price bar found")
                        continue
                    
                    # Get the address (first div in price bar)
                    address_div = price_bar.find('div')
                    if not address_div:
                        print(f"[CoventryCambridgeNowScraper] Skipping card {idx+1}: No address found")
                        continue
                    
                    address = address_div.get_text(strip=True)
                    if not address:
                        print(f"[CoventryCambridgeNowScraper] Skipping card {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[CoventryCambridgeNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price information from the price bar
                    price_spans = price_bar.find_all('span')
                    current_price = None
                    original_price = None
                    
                    for span in price_spans:
                        span_text = span.get_text(strip=True)
                        if '$' in span_text and 'Was' not in span_text:
                            current_price = self.parse_price(span_text)
                        elif 'Was' in span_text:
                            original_price = self.parse_original_price(span_text)
                    
                    if not current_price:
                        print(f"[CoventryCambridgeNowScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract square footage, beds, and baths from the model info bar
                    info_bar = card.find('ul', class_='model-info-bar')
                    if not info_bar:
                        print(f"[CoventryCambridgeNowScraper] Skipping card {idx+1}: No info bar found")
                        continue
                    
                    info_items = info_bar.find_all('li')
                    sqft = None
                    beds = ""
                    baths = ""
                    
                    for item in info_items:
                        item_text = item.get_text(strip=True)
                        if 'AREA (SQ FT)' in item_text:
                            sqft = self.parse_sqft(item_text)
                        elif 'Beds' in item_text:
                            beds = self.parse_beds(item_text)
                        elif 'Bathrooms' in item_text:
                            baths = self.parse_baths(item_text)
                    
                    if not sqft:
                        print(f"[CoventryCambridgeNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Calculate price reduction if original price exists
                    price_reduction = None
                    if original_price and original_price > current_price:
                        price_reduction = original_price - current_price
                    
                    # Determine if it's a price cut
                    price_cut_text = ""
                    if price_reduction:
                        price_cut_text = f"Price cut: ${price_reduction:,}"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": "1",  # Default to 1 story for single-family homes
                        "price_per_sqft": price_per_sqft,
                        "plan_name": address,
                        "company": "Coventry Homes",
                        "community": "Cambridge",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": original_price,
                        "price_cut": price_cut_text
                    }
                    
                    print(f"[CoventryCambridgeNowScraper] Model Card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[CoventryCambridgeNowScraper] Error processing model card {idx+1}: {e}")
                    continue
            
            print(f"[CoventryCambridgeNowScraper] Successfully processed {len(listings)} unique quick move-in homes")
            return listings
            
        except Exception as e:
            print(f"[CoventryCambridgeNowScraper] Error: {e}")
            return []
