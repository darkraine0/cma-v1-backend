import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict
import json

class DavidHomesMaddoxNowScraper(BaseScraper):
    URL = "https://www.davidsonhomes.com/states/georgia/atlanta-market-area/hoschton/wehunt-meadows"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None
    
    def parse_price(self, price_text):
        """Extract price from price text."""
        if not price_text:
            return None
        # Look for patterns like "$488,990" or "$488,990 BASE PRICE"
        match = re.search(r'\$([\d,]+)', str(price_text))
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except (ValueError, TypeError):
                return None
        return None
    
    def parse_beds(self, beds_text):
        """Extract number of bedrooms from text."""
        if not beds_text:
            return ""
        # Look for patterns like "4 - 5" or "5"
        match = re.search(r'(\d+(?:\.\d+)?)', str(beds_text))
        if match:
            return match.group(1).strip()
        return ""
    
    def parse_baths(self, baths_text):
        """Extract number of bathrooms from text."""
        if not baths_text:
            return ""
        # Look for patterns like "3 - 4" or "2.5 - 3"
        match = re.search(r'(\d+(?:\.\d+)?)', str(baths_text))
        if match:
            return match.group(1).strip()
        return ""
    
    def parse_stories(self, stories_text):
        """Extract number of stories from text."""
        if not stories_text:
            return "2"  # Default to 2 stories
        # Look for patterns like "2" or "1"
        match = re.search(r'(\d+)', str(stories_text))
        if match:
            return match.group(1).strip()
        return "2"
    
    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DavidHomesMaddoxNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DavidHomesMaddoxNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[DavidHomesMaddoxNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Find all home cards using the structure similar to PickensBluff scraper
            # Look for divs with the specific structure that contains home listings
            home_cards = soup.find_all('div', class_=re.compile(r'.*relative.*flex.*h-full.*flex-col.*overflow-hidden.*rounded.*bg-white.*text-center.*shadow.*'))
            
            # If that doesn't work, try a more general approach
            if not home_cards:
                # Look for any divs that contain the home listing structure
                all_divs = soup.find_all('div')
                home_cards = []
                for div in all_divs:
                    # Check if this div contains the structure we're looking for
                    if div.find('script', type='application/ld+json') and div.find('article'):
                        home_cards.append(div)
            
            print(f"[DavidHomesMaddoxNowScraper] Found {len(home_cards)} home cards")
            
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            for idx, card in enumerate(home_cards):
                try:
                    # First try to extract data from JSON-LD script tag
                    script_tag = card.find('script', type='application/ld+json')
                    plan_name = None
                    price = None
                    beds = None
                    baths = None
                    sqft = None
                    stories = "2"
                    address = None
                    plan_url = None
                    
                    if script_tag and script_tag.string:
                        try:
                            json_data = json.loads(script_tag.string)
                            
                            # Extract data from JSON
                            plan_name = json_data.get('name', '')
                            address = json_data.get('address', {}).get('streetAddress', '')
                            
                            # Extract from description or other fields
                            description = json_data.get('description', '')
                            if description:
                                # Look for beds in description
                                beds_match = re.search(r'(\d+(?:\.\d+)?)\s*bedrooms?', description, re.IGNORECASE)
                                if beds_match:
                                    beds = beds_match.group(1)
                                
                                # Look for baths in description
                                baths_match = re.search(r'(\d+(?:\.\d+)?)\s*bathrooms?', description, re.IGNORECASE)
                                if baths_match:
                                    baths = baths_match.group(1)
                                
                                # Look for sqft in description
                                sqft_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*square\s*feet', description, re.IGNORECASE)
                                if sqft_match:
                                    sqft = self.parse_sqft(sqft_match.group(1))
                            
                            # Extract price from offers
                            offers = json_data.get('offers', {})
                            if offers:
                                price_value = offers.get('price')
                                if price_value:
                                    try:
                                        price = int(price_value)
                                    except (ValueError, TypeError):
                                        pass
                            
                            # Extract URL
                            plan_url = json_data.get('url', '')
                            if plan_url and not plan_url.startswith('http'):
                                plan_url = f"https://www.davidsonhomes.com{plan_url}"
                                
                        except Exception as e:
                            print(f"[DavidHomesMaddoxNowScraper] Error parsing JSON for card {idx+1}: {e}")
                    
                    # If JSON parsing failed or missing data, try HTML extraction
                    if not all([plan_name, price, beds, baths, sqft]):
                        card_text = card.get_text()
                        
                        # Extract plan name from HTML - look for h4 or h2 elements
                        if not plan_name:
                            # Try h4 first (common in Quick Move-In cards)
                            name_elem = card.find('h4')
                            if not name_elem:
                                name_elem = card.find('h2')
                            if name_elem:
                                plan_name = name_elem.get_text(strip=True)
                                # Clean up plan name - ensure it includes "at Wehunt Meadows" if present
                                # The plan name should be like "The Glenwood C at Wehunt Meadows"
                                # or "The Harrison G" or "The Hickory B - Unfinished Basement at Wehunt Meadows"
                                if plan_name and 'at Wehunt Meadows' not in plan_name:
                                    # Check if there's a community name elsewhere
                                    community_elem = card.find('span', class_=re.compile(r'.*text-grey.*|.*text-gray.*'))
                                    if community_elem:
                                        community_text = community_elem.get_text(strip=True)
                                        if 'Wehunt Meadows' in community_text and 'Wehunt Meadows' not in plan_name:
                                            plan_name = f"{plan_name} at Wehunt Meadows"
                        
                        # Extract address from HTML
                        if not address:
                            address_elem = card.find('span', class_='text-grey-500')
                            if not address_elem:
                                address_elem = card.find('span', class_=re.compile(r'.*text-grey.*|.*text-gray.*'))
                            if address_elem:
                                address = address_elem.get_text(strip=True)
                        
                        # Extract price from HTML - look for the actual home price
                        if not price:
                            # Look for the main price (not monthly payment) - use more flexible selector
                            price_elem = card.find('div', class_=re.compile(r'.*text-xl.*font-semibold.*text-green.*'))
                            if not price_elem:
                                # Try finding price in any div with green text
                                price_elem = card.find('div', class_=re.compile(r'.*text-green.*'))
                            if price_elem:
                                price_text = price_elem.get_text(strip=True)
                                price = self.parse_price(price_text)
                        
                        # Extract other details from HTML
                        if not beds:
                            beds_match = re.search(r'(\d+(?:\.\d+)?)\s*Bd', card_text)
                            beds = beds_match.group(1) if beds_match else None
                        
                        if not baths:
                            baths_match = re.search(r'(\d+(?:\.\d+)?)\s*Ba', card_text)
                            baths = baths_match.group(1) if baths_match else None
                        
                        if not sqft:
                            sqft_match = re.search(r'([\d,]+)\s*Sf', card_text)
                            if sqft_match:
                                sqft = self.parse_sqft(sqft_match.group(1))
                        
                        # Extract URL from HTML
                        if not plan_url:
                            link_elem = card.find('a', href=True)
                            if link_elem:
                                plan_url = link_elem.get('href')
                                if plan_url and not plan_url.startswith('http'):
                                    plan_url = f"https://www.davidsonhomes.com{plan_url}"
                    
                    # Skip if missing essential details
                    if not all([plan_name, price, beds, baths, sqft]):
                        print(f"[DavidHomesMaddoxNowScraper] Skipping card {idx+1}: Missing essential details (name: {plan_name}, price: {price}, beds: {beds}, baths: {baths}, sqft: {sqft})")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[DavidHomesMaddoxNowScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    # Use plan name as address if no address found
                    if not address:
                        address = plan_name
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "David Homes",
                        "community": "Maddox",
                        "type": "now",
                        "beds": str(beds),
                        "baths": str(baths),
                        "address": address,
                        "url": plan_url
                    }
                    
                    price_str = f"${price:,}" if price else "No price"
                    sqft_str = f"{sqft:,}" if sqft else "No sqft"
                    print(f"[DavidHomesMaddoxNowScraper] Property {idx+1}: {plan_data['plan_name']} - {price_str} - {sqft_str} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[DavidHomesMaddoxNowScraper] Error processing property {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[DavidHomesMaddoxNowScraper] Successfully processed {len(listings)} properties")
            return listings
            
        except Exception as e:
            print(f"[DavidHomesMaddoxNowScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []