import requests
import re
import json
from ...base import BaseScraper
from typing import List, Dict

class KHovnanianElevonNowScraper(BaseScraper):
    URL = "https://www.khov.com/new-construction-homes/texas/lavon/elevon/#quick-move-ins"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def fetch_plans(self) -> List[Dict]:

        try:
            print(f"[KHovnanianElevonNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[KHovnanianElevonNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[KHovnanianElevonNowScraper] Request failed with status {resp.status_code}")
                return []
            
            content = resp.text
            listings = []
            
            # Look for JSON patterns in the HTML content
            # The data is embedded as malformed JSON strings in the HTML
            # Pattern: listing-price:615000,listing-size:3711,listing-beds:5,listing-baths:4.5,...
            json_patterns = re.findall(r'\{[^{}]*listing-price[^{}]*\}', content)
            print(f"[KHovnanianElevonNowScraper] Found {len(json_patterns)} JSON patterns with listing data")
            
            for idx, pattern in enumerate(json_patterns):
                try:
                    print(f"[KHovnanianElevonNowScraper] Processing JSON pattern {idx+1}")
                    
                    # Convert the malformed JSON to proper JSON format
                    # The pattern has escaped quotes, so we need to handle them properly
                    clean_pattern = pattern.replace('\\"', '"')
                    
                    # Parse the JSON data
                    home_data = json.loads(clean_pattern)
                    
                    # Extract data from JSON
                    price = home_data.get('listing-price')
                    sqft = home_data.get('listing-size')
                    address = home_data.get('listing-address', '')
                    beds = home_data.get('listing-beds', '')
                    baths = home_data.get('listing-baths', '')
                    
                    if not price or not sqft:
                        print(f"[KHovnanianElevonNowScraper] Skipping home {idx+1}: Missing price or sqft")
                        print(f"  Price: {price}, Sqft: {sqft}")
                        continue
                    
                    if not address:
                        print(f"[KHovnanianElevonNowScraper] Skipping home {idx+1}: Missing address")
                        continue
                    
                    # Convert to integers
                    price_int = int(price) if isinstance(price, (int, str)) else price
                    sqft_int = int(sqft) if isinstance(sqft, (int, str)) else sqft
                    price_per_sqft = round(price_int / sqft_int, 2) if sqft_int > 0 else None
                    
                    plan_data = {
                        "price": price_int,
                        "sqft": sqft_int,
                        "stories": "1",  # Default to 1 story
                        "price_per_sqft": price_per_sqft,
                        "plan_name": address,  # Use address as plan_name as requested
                        "company": "K. Hovnanian Homes",
                        "community": "Elevon",
                        "type": "now",
                        "beds": str(beds) if beds else "",
                        "baths": str(baths) if baths else "",
                        "address": address
                    }
                    
                    print(f"[KHovnanianElevonNowScraper] Home {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except json.JSONDecodeError as e:
                    print(f"[KHovnanianElevonNowScraper] Error parsing JSON pattern {idx+1}: {e}")
                    continue
                except Exception as e:
                    print(f"[KHovnanianElevonNowScraper] Error processing home {idx+1}: {e}")
                    continue
            
            print(f"[KHovnanianElevonNowScraper] Successfully processed {len(listings)} homes")
            return listings
            
        except Exception as e:
            print(f"[KHovnanianElevonNowScraper] Error: {e}")
            return [] 