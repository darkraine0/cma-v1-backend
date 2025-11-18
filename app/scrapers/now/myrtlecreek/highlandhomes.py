import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class HighlandHomesMyrtleCreekNowScraper(BaseScraper):
    URLS = [
        "https://www.highlandhomes.com/dfw/waxahachie/ridge-crossing",
        "https://www.highlandhomes.com/dfw/waxahachie/dove-hollow"
    ]
    
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
        # Handle both "3" and "3-4" formats
        match = re.search(r'(\d+(?:-\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def is_quick_move_in(self, card):
        """Check if this card represents a quick move-in home."""
        # Quick move-in homes have addresses (not plan names) and specific home tags
        home_tag = card.find('span', class_='home-tag')
        home_identifier = card.find('span', class_='homeIdentifier')
        
        if home_identifier:
            identifier_text = home_identifier.get_text(strip=True)
            # If it's an address (contains street number and doesn't end with "Plan"), it's a quick move-in home
            if re.search(r'^\d+\s+[A-Za-z\s]+(?:Court|Street|Avenue|Drive|Lane|Boulevard|Way|Place|Circle)', identifier_text):
                return True
        
        # Also check for specific tags that indicate quick move-in homes
        if home_tag:
            tag_text = home_tag.get_text(strip=True)
            if 'Complete' in tag_text or 'Est. Completion' in tag_text:
                return True
        
        return False

    def is_floor_plan(self, card):
        """Check if this card represents a floor plan."""
        # Floor plans have "Starting at" text and plan names ending with "Plan"
        starting_at = card.find('span', class_='homeStartingAt')
        home_identifier = card.find('span', class_='homeIdentifier')
        
        if starting_at and home_identifier:
            identifier_text = home_identifier.get_text(strip=True)
            # If it ends with "Plan", it's a floor plan
            if identifier_text.endswith('Plan'):
                return True
        
        return False

    def fetch_plans(self) -> List[Dict]:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Loop through both URLs
            for url_idx, url in enumerate(self.URLS, 1):
                print(f"[HighlandHomesMyrtleCreekNowScraper] Fetching URL {url_idx}: {url}")
                
                resp = requests.get(url, headers=headers, timeout=15)
                print(f"[HighlandHomesMyrtleCreekNowScraper] Response status: {resp.status_code}")
                
                if resp.status_code != 200:
                    print(f"[HighlandHomesMyrtleCreekNowScraper] Request failed with status {resp.status_code}")
                    continue
                
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Find all home containers (both quick move-in and floor plans)
                home_containers = soup.find_all('a', class_='home-container')
                print(f"[HighlandHomesMyrtleCreekNowScraper] Found {len(home_containers)} home containers in URL {url_idx}")
                
                for idx, container in enumerate(home_containers):
                    try:
                        print(f"[HighlandHomesMyrtleCreekNowScraper] Processing container {idx+1}")
                        
                        # Check if this is a quick move-in home
                        if self.is_quick_move_in(container):
                            print(f"[HighlandHomesMyrtleCreekNowScraper] Processing quick move-in home {idx+1}")
                            
                            # Extract address
                            home_identifier = container.find('span', class_='homeIdentifier')
                            if not home_identifier:
                                print(f"[HighlandHomesMyrtleCreekNowScraper] Skipping container {idx+1}: No home identifier found")
                                continue
                            
                            address = home_identifier.get_text(strip=True)
                            if not address:
                                print(f"[HighlandHomesMyrtleCreekNowScraper] Skipping container {idx+1}: Empty address")
                                continue
                            
                            # Check for duplicate addresses
                            if address in seen_addresses:
                                print(f"[HighlandHomesMyrtleCreekNowScraper] Skipping container {idx+1}: Duplicate address '{address}'")
                                continue
                            
                            seen_addresses.add(address)
                            
                            # Extract price
                            price_span = container.find('span', class_='price')
                            if not price_span:
                                print(f"[HighlandHomesMyrtleCreekNowScraper] Skipping container {idx+1}: No price found")
                                continue
                            
                            current_price = self.parse_price(price_span.get_text())
                            if not current_price:
                                print(f"[HighlandHomesMyrtleCreekNowScraper] Skipping container {idx+1}: No current price found")
                                continue
                            
                            # Extract plan name from homeUpgrades
                            home_upgrades = container.find('p', class_='homeUpgrades')
                            plan_name = ""
                            if home_upgrades:
                                plan_text = home_upgrades.get_text(strip=True)
                                # Extract plan name (e.g., "London Plan with 6 upgrades" -> "London Plan")
                                plan_match = re.search(r'^([A-Za-z\s]+)\s+Plan', plan_text)
                                if plan_match:
                                    plan_name = plan_match.group(1).strip()
                            
                            # Extract beds, baths, stories, and sqft from homeDetails
                            home_details = container.find('div', class_='homeDetails')
                            beds = ""
                            baths = ""
                            stories = ""
                            sqft = None
                            
                            if home_details:
                                detail_items = home_details.find_all('div', class_='homeDetailItem')
                                for item in detail_items:
                                    numeral = item.find('span', class_='numeral')
                                    label = item.find('span', class_='label')
                                    if numeral and label:
                                        value = numeral.get_text(strip=True)
                                        label_text = label.get_text(strip=True).lower()
                                        
                                        if 'bed' in label_text:
                                            beds = self.parse_beds(value)
                                        elif 'bath' in label_text:
                                            baths = self.parse_baths(value)
                                        elif 'stor' in label_text:
                                            stories = self.parse_stories(value)
                            
                            # Extract square footage from homeSqFootage
                            home_sqft = container.find('div', class_='homeSqFootage')
                            if home_sqft:
                                numeral = home_sqft.find('span', class_='numeral')
                                if numeral:
                                    sqft = self.parse_sqft(numeral.get_text())
                            
                            if not sqft:
                                print(f"[HighlandHomesMyrtleCreekNowScraper] Skipping container {idx+1}: No square footage found")
                                continue
                            
                            # Calculate price per sqft
                            price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                            
                            plan_data = {
                                "price": current_price,
                                "sqft": sqft,
                                "stories": stories or "1",
                                "price_per_sqft": price_per_sqft,
                                "plan_name": plan_name or address,
                                "company": "Highland Homes",
                                "community": "Myrtle Creek",
                                "type": "now",
                                "beds": beds,
                                "baths": baths,
                                "address": address,
                                "original_price": None,
                                "price_cut": ""
                            }
                            
                            print(f"[HighlandHomesMyrtleCreekNowScraper] Quick Move-in Home {idx+1}: {plan_data}")
                            listings.append(plan_data)
                        
                        else:
                            print(f"[HighlandHomesMyrtleCreekNowScraper] Container {idx+1}: Not a quick move-in home, skipping")
                            continue
                        
                    except Exception as e:
                        print(f"[HighlandHomesMyrtleCreekNowScraper] Error processing container {idx+1}: {e}")
                        continue
            
            print(f"[HighlandHomesMyrtleCreekNowScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[HighlandHomesMyrtleCreekNowScraper] Error: {e}")
            return []


    def get_company_name(self) -> str:
        """Return company name."""
        return "Highland Homes"

    def get_community_name(self) -> str:
        """Return community name."""
        return "Myrtle Creek"
