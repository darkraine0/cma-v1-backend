import requests
import re
import json
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

    def parse_savings(self, text):
        """Extract savings amount from text like '$65K'."""
        # Handle formats like "$65K", "$65,000", etc.
        match = re.search(r'\$([\d,]+)K?', text)
        if match:
            value = match.group(1).replace(",", "")
            # If it ends with K (implicit), multiply by 1000
            if 'K' in text.upper():
                return int(value) * 1000
            return int(value)
        return None

    def is_quick_move_in(self, article):
        """Check if this article represents a quick move-in home (has address)."""
        # Quick move-in homes have addresses, floor plans have model names
        address_elem = article.find('address')
        return address_elem is not None

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
            
            # Find all article cards - these contain both quick move-in homes and floor plans
            articles = soup.find_all('article', class_='card-spec')
            print(f"[CoventryCambridgeNowScraper] Found {len(articles)} total article cards")
            
            for idx, article in enumerate(articles):
                try:
                    print(f"[CoventryCambridgeNowScraper] Processing article {idx+1}")
                    
                    # Check if this is actually a quick move-in home (has address)
                    if not self.is_quick_move_in(article):
                        print(f"[CoventryCambridgeNowScraper] Skipping article {idx+1}: Not a quick move-in home (likely floor plan)")
                        continue
                    
                    # Extract address
                    address_elem = article.find('address')
                    if not address_elem:
                        print(f"[CoventryCambridgeNowScraper] Skipping article {idx+1}: No address found")
                        continue
                    
                    address = address_elem.get_text(strip=True)
                    if not address:
                        print(f"[CoventryCambridgeNowScraper] Skipping article {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[CoventryCambridgeNowScraper] Skipping article {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price - try data attribute first, then fall back to text
                    current_price = None
                    if article.get('data-price'):
                        current_price = int(article.get('data-price'))
                    else:
                        price_elem = article.find('p', class_='display-6')
                        if price_elem:
                            current_price = self.parse_price(price_elem.get_text(strip=True))
                    
                    if not current_price:
                        print(f"[CoventryCambridgeNowScraper] Skipping article {idx+1}: No current price found")
                        continue
                    
                    # Extract square footage - try data attribute first, then fall back to text
                    sqft = None
                    if article.get('data-square-feet'):
                        sqft = int(article.get('data-square-feet'))
                    else:
                        # Try to extract from the info text
                        info_elem = article.find('p', class_='mb-2')
                        if info_elem:
                            info_text = info_elem.get_text(strip=True)
                            # Look for pattern like "2,994 sqft"
                            sqft_match = re.search(r'([\d,]+)\s*sqft', info_text, re.IGNORECASE)
                            if sqft_match:
                                sqft = int(sqft_match.group(1).replace(",", ""))
                    
                    if not sqft:
                        print(f"[CoventryCambridgeNowScraper] Skipping article {idx+1}: No square footage found")
                        continue
                    
                    # Extract beds and baths from the info text
                    beds = ""
                    baths = ""
                    info_elem = article.find('p', class_='mb-2')
                    if info_elem:
                        info_text = info_elem.get_text(strip=True)
                        # Parse format like "4 bed · 3 bath · 2,994 sqft"
                        bed_match = re.search(r'(\d+)\s*bed', info_text, re.IGNORECASE)
                        if bed_match:
                            beds = bed_match.group(1)
                        
                        bath_match = re.search(r'(\d+(?:/\d+)?)\s*bath', info_text, re.IGNORECASE)
                        if bath_match:
                            baths = bath_match.group(1)
                    
                    # Extract savings/price reduction if present
                    savings_badge = article.find('span', class_='badge')
                    price_reduction = None
                    original_price = None
                    if savings_badge and 'bg-red' in savings_badge.get('class', []):
                        savings_text = savings_badge.get_text(strip=True)
                        price_reduction = self.parse_savings(savings_text)
                        if price_reduction:
                            original_price = current_price + price_reduction
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
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
                    
                    print(f"[CoventryCambridgeNowScraper] Article {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[CoventryCambridgeNowScraper] Error processing article {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[CoventryCambridgeNowScraper] Successfully processed {len(listings)} unique quick move-in homes")
            return listings
            
        except Exception as e:
            print(f"[CoventryCambridgeNowScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
