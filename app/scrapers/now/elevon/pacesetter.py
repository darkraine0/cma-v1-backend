import requests
import re
import json
from ...base import BaseScraper
from typing import List, Dict

class PacesetterElevonNowScraper(BaseScraper):
    URL = "https://www.pacesetterhomestexas.com/new-homes-for-sale-dallas/lavon-tx/elevon?community=62"
    
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
            print(f"[PacesetterElevonNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[PacesetterElevonNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[PacesetterElevonNowScraper] Request failed with status {resp.status_code}")
                return []
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            
            listings = []
            
            # Look for the qmi-carousel component that contains the home data
            qmi_carousel = soup.find('qmi-carousel')
            if qmi_carousel:
                print("[PacesetterElevonNowScraper] Found qmi-carousel component")
                print(f"[PacesetterElevonNowScraper] qmi-carousel attributes: {dict(qmi_carousel.attrs)}")
                
                # Extract the qmi-list attribute which contains JSON data (Vue.js syntax with colon prefix)
                qmi_list_attr = qmi_carousel.get(':qmi-list')
                if qmi_list_attr:
                    print(f"[PacesetterElevonNowScraper] Found :qmi-list data: {qmi_list_attr[:200]}...")
                    
                    try:
                        # Parse the JSON data
                        import json
                        homes_data = json.loads(qmi_list_attr)
                        print(f"[PacesetterElevonNowScraper] Successfully parsed {len(homes_data)} homes from JSON")
                        
                        # Process each home in the JSON data
                        for idx, home in enumerate(homes_data):
                            try:
                                print(f"[PacesetterElevonNowScraper] Processing home {idx+1}: {home.get('address', 'Unknown')}")
                                
                                # Extract data from JSON
                                price_text = home.get('formattedPrice', '')
                                price = self.parse_price(price_text)
                                
                                sqft_text = home.get('sqft', '')
                                sqft = self.parse_sqft(sqft_text)
                                
                                beds = home.get('beds', '')
                                baths = home.get('baths', '')
                                address = home.get('address', '')
                                
                                # Get plan name from hero title or address
                                plan_name = ""
                                hero = home.get('hero', {})
                                if hero and hero.get('title'):
                                    plan_name = hero['title']
                                else:
                                    # Use address as plan name if no title
                                    plan_name = address
                                
                                if not price or not sqft:
                                    print(f"[PacesetterElevonNowScraper] Skipping home {idx+1}: Missing price or sqft")
                                    print(f"  Price: {price}, Sqft: {sqft}")
                                    continue
                                
                                if not plan_name:
                                    print(f"[PacesetterElevonNowScraper] Skipping home {idx+1}: Missing plan name")
                                    continue
                                
                                # Convert to integers
                                price_int = int(price) if isinstance(price, str) else price
                                sqft_int = int(sqft) if isinstance(sqft, str) else sqft
                                price_per_sqft = round(price_int / sqft_int, 2) if sqft_int > 0 else None
                                
                                plan_data = {
                                    "price": price_int,
                                    "sqft": sqft_int,
                                    "stories": "1",  # Default to 1 story
                                    "price_per_sqft": price_per_sqft,
                                    "plan_name": plan_name,
                                    "company": "Pacesetter Homes",
                                    "builder": "Pacesetter Homes",
                                    "community": "Elevon",
                                    "type": "now",
                                    "beds": beds,
                                    "baths": baths,
                                    "address": address
                                }
                                
                                print(f"[PacesetterElevonNowScraper] Home {idx+1}: {plan_data}")
                                listings.append(plan_data)
                                
                            except Exception as e:
                                print(f"[PacesetterElevonNowScraper] Error processing home {idx+1}: {e}")
                                continue
                        
                        print(f"[PacesetterElevonNowScraper] Successfully processed {len(listings)} homes from JSON")
                        return listings
                        
                    except json.JSONDecodeError as e:
                        print(f"[PacesetterElevonNowScraper] Error parsing JSON: {e}")
                else:
                    print("[PacesetterElevonNowScraper] No qmi-list attribute found")
            else:
                print("[PacesetterElevonNowScraper] No qmi-carousel component found")
            
            # If JSON parsing failed, return empty list
            print("[PacesetterElevonNowScraper] No data found")
            return []
            
        except Exception as e:
            print(f"[PacesetterElevonNowScraper] Error: {e}")
            return [] 