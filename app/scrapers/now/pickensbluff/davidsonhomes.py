import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict
import json

class DavidsonHomesPickensBluffNowScraper(BaseScraper):
    URL = "https://www.davidsonhomes.com/states/georgia/atlanta-market-area/dallas/riverwood/"

    def parse_sqft(self, text):
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DavidsonHomesPickensBluffNowScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }

            response = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DavidsonHomesPickensBluffNowScraper] Response status: {response.status_code}")

            if response.status_code != 200:
                print(f"[DavidsonHomesPickensBluffNowScraper] Request failed with status {response.status_code}")
                return []

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all home cards using the structure from the provided HTML
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

            print(f"[DavidsonHomesPickensBluffNowScraper] Found {len(home_cards)} home cards")

            listings = []

            for idx, card in enumerate(home_cards):
                try:
                    # First try to extract data from JSON-LD script tag
                    script_tag = card.find('script', type='application/ld+json')
                    plan_name = None
                    price = None
                    beds = None
                    baths = None
                    sqft = None
                    stories = "1"
                    address = None
                    plan_url = None
                    homesite_number = None
                    status = "available"
                    
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
                            
                            # Extract URL
                            plan_url = json_data.get('url', '')
                            if plan_url and not plan_url.startswith('http'):
                                plan_url = f"https://www.davidsonhomes.com{plan_url}"
                                
                        except Exception as e:
                            print(f"[DavidsonHomesPickensBluffNowScraper] Error parsing JSON for card {idx+1}: {e}")
                    
                    # If JSON parsing failed or missing data, try HTML extraction
                    if not all([plan_name, price, beds, baths, sqft]):
                        card_text = card.get_text()
                        
                        # Extract plan name from HTML
                        if not plan_name:
                            name_elem = card.find('h4')
                            if name_elem:
                                plan_name = name_elem.get_text(strip=True)
                        
                        # Extract address from HTML
                        if not address:
                            address_elem = card.find('span', class_='text-grey-500')
                            if address_elem:
                                address = address_elem.get_text(strip=True)
                        
                        # Extract price from HTML - look for the actual home price, not monthly payment
                        if not price:
                            # Look for the main price (not monthly payment) - use more flexible selector
                            price_elem = card.find('div', class_=re.compile(r'.*text-xl.*font-semibold.*text-green.*'))
                            if price_elem:
                                price_text = price_elem.get_text(strip=True)
                                print(f"[DavidsonHomesPickensBluffNowScraper] Found price element: '{price_text}'")
                                # Extract just the price number (remove "or" text)
                                price_match = re.search(r'\$([\d,]+)', price_text)
                                if price_match:
                                    price_str = price_match.group(1)
                                    print(f"[DavidsonHomesPickensBluffNowScraper] Price string to parse: '{price_str}'")
                                    # Parse the price directly since we already extracted the number
                                    price = int(price_str.replace(",", ""))
                                    print(f"[DavidsonHomesPickensBluffNowScraper] Parsed price: {price}")
                                    print(f"[DavidsonHomesPickensBluffNowScraper] Extracted price: ${price:,}")
                            else:
                                print(f"[DavidsonHomesPickensBluffNowScraper] No price element found for card {idx+1}")
                        
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
                        
                        # Extract homesite number
                        homesite_match = re.search(r'Homesite\s*#\s*(\d+)', card_text)
                        if homesite_match:
                            homesite_number = homesite_match.group(1)
                        
                        # Check status (Move-In Ready, Sold, etc.)
                        status_elem = card.find('span', class_=re.compile(r'.*bg-green.*|.*bg-red.*'))
                        if status_elem:
                            status_text = status_elem.get_text(strip=True).lower()
                            if 'sold' in status_text:
                                status = "sold"
                            elif 'move-in ready' in status_text:
                                status = "available"
                        
                        # Also check for the specific status classes from the HTML
                        if not status_elem:
                            # Look for green status badge (Move-In Ready)
                            green_status = card.find('span', class_=re.compile(r'.*bg-green.*'))
                            if green_status:
                                status = "available"
                            # Look for red status badge (Sold)
                            red_status = card.find('span', class_=re.compile(r'.*bg-red.*'))
                            if red_status:
                                status = "sold"
                        
                        # Include all properties (both Move-In Ready and Sold)
                        # No need to skip sold properties
                        
                        # Extract URL from HTML
                        if not plan_url:
                            link_elem = card.find('a', href=True)
                            if link_elem:
                                plan_url = link_elem.get('href')
                                if plan_url and not plan_url.startswith('http'):
                                    plan_url = f"https://www.davidsonhomes.com{plan_url}"
                    
                    # Skip if missing essential details
                    if not all([plan_name, price, beds, baths, sqft, address]):
                        print(f"[DavidsonHomesPickensBluffNowScraper] Skipping card {idx+1}: Missing essential details (name: {plan_name}, price: {price}, beds: {beds}, baths: {baths}, sqft: {sqft}, address: {address})")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Davidson Homes",
                        "community": "Pickens Bluff",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "status": status,
                        "url": plan_url,
                        "homesite_number": homesite_number
                    }
                    
                    price_str = f"${price:,}" if price else "No price"
                    sqft_str = f"{sqft:,}" if sqft else "No sqft"
                    print(f"[DavidsonHomesPickensBluffNowScraper] Property {idx+1}: {plan_data['plan_name']} - {price_str} - {sqft_str} sqft - {address}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[DavidsonHomesPickensBluffNowScraper] Error processing property {idx+1}: {e}")
                    continue

            print(f"[DavidsonHomesPickensBluffNowScraper] Successfully processed {len(listings)} properties")
            return listings

        except Exception as e:
            print(f"[DavidsonHomesPickensBluffNowScraper] Error: {e}")
            return []
