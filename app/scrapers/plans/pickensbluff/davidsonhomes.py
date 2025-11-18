import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict
import json

class DavidsonHomesPickensBluffPlanScraper(BaseScraper):
    URL = "https://www.davidsonhomes.com/states/georgia/atlanta-market-area/dallas/riverwood/"

    def parse_sqft(self, text):
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DavidsonHomesPickensBluffPlanScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }

            response = requests.get(self.URL, headers=headers, timeout=30)
            print(f"[DavidsonHomesPickensBluffPlanScraper] Response status: {response.status_code}")

            if response.status_code != 200:
                print(f"[DavidsonHomesPickensBluffPlanScraper] Request failed with status {response.status_code}")
                return []

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for home cards that contain plan information
            # Based on the debug output, this appears to be a "now" listings page
            # but we can extract plan information from the home listings
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

            print(f"[DavidsonHomesPickensBluffPlanScraper] Found {len(home_cards)} home cards")

            # Extract unique plan information from home cards
            plan_cards = []
            seen_plans = set()
            
            for card in home_cards:
                try:
                    # Extract plan name from the card
                    plan_name_elem = card.find('h4')
                    if plan_name_elem:
                        plan_name = plan_name_elem.get_text(strip=True)
                        # Clean up plan name (remove address info and get just the plan type)
                        # Handle both " - " and "- " patterns
                        if ' - ' in plan_name:
                            plan_name = plan_name.split(' - ')[0]
                        elif '- ' in plan_name:
                            plan_name = plan_name.split('- ')[0]
                        
                        # Remove trailing dashes and clean up
                        plan_name = plan_name.rstrip('-').strip()
                        
                        # Extract just the plan type (e.g., "The Ash B", "The Willow B")
                        if 'The ' in plan_name:
                            # Extract the plan type (e.g., "The Ash B", "The Willow B")
                            # Split by "The " and take the part after it
                            after_the = plan_name.split('The ')[1]
                            # Split by spaces and take first two words
                            parts = after_the.split(' ')
                            if len(parts) >= 2:
                                plan_name = f"The {parts[0]} {parts[1]}"
                            else:
                                plan_name = f"The {parts[0]}"
                        
                        if plan_name and plan_name not in seen_plans:
                            seen_plans.add(plan_name)
                            plan_cards.append(card)
                except:
                    continue

            print(f"[DavidsonHomesPickensBluffPlanScraper] Found {len(plan_cards)} potential plan cards")

            listings = []

            for idx, card in enumerate(plan_cards):
                try:
                    # First try to extract data from JSON-LD script tag
                    script_tag = card.find('script', type='application/ld+json')
                    plan_name = None
                    price = None
                    beds = None
                    baths = None
                    sqft = None
                    stories = "1"
                    plan_url = None
                    
                    if script_tag and script_tag.string:
                        try:
                            json_data = json.loads(script_tag.string)
                            
                            # Extract data from JSON
                            plan_name = json_data.get('name', '')
                            # Clean up plan name (remove address info)
                            if ' - ' in plan_name:
                                plan_name = plan_name.split(' - ')[0]
                            
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
                            print(f"[DavidsonHomesPickensBluffPlanScraper] Error parsing JSON for card {idx+1}: {e}")
                    
                    # If JSON parsing failed or missing data, try HTML extraction
                    if not all([plan_name, beds, baths, sqft]):
                        card_text = card.get_text()
                        
                        # Extract plan name from HTML
                        if not plan_name:
                            name_elem = card.find('h4')
                            if name_elem:
                                plan_name = name_elem.get_text(strip=True)
                                # Clean up plan name (remove address info)
                                if ' - ' in plan_name:
                                    plan_name = plan_name.split(' - ')[0]
                        
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
                    if not all([plan_name, beds, baths, sqft]):
                        print(f"[DavidsonHomesPickensBluffPlanScraper] Skipping card {idx+1}: Missing essential details (name: {plan_name}, beds: {beds}, baths: {baths}, sqft: {sqft})")
                        continue
                    
                    # For plans, we don't have a specific price, so we'll use a placeholder
                    # or extract from the "Starting at" information if available
                    if not price:
                        # Look for "Starting at" price in the community description
                        community_desc = soup.find(string=re.compile(r'from the \$[\d,]+s', re.IGNORECASE))
                        if community_desc:
                            price_match = re.search(r'from the \$([\d,]+)s', community_desc, re.IGNORECASE)
                            if price_match:
                                price = self.parse_price(price_match.group(1) + "000")  # Convert $500s to $500000
                    
                    # If still no price, use a default
                    if not price:
                        price = 500000  # Default starting price
                    
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
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",  # Plans don't have addresses
                        "design_number": plan_name,  # Use plan name as design number
                        "url": plan_url
                    }
                    
                    print(f"[DavidsonHomesPickensBluffPlanScraper] Plan {idx+1}: {plan_data['plan_name']} - ${price:,} - {sqft:,} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[DavidsonHomesPickensBluffPlanScraper] Error processing plan {idx+1}: {e}")
                    continue

            print(f"[DavidsonHomesPickensBluffPlanScraper] Successfully processed {len(listings)} plans")
            return listings

        except Exception as e:
            print(f"[DavidsonHomesPickensBluffPlanScraper] Error: {e}")
            return []
