import requests
import json
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class DavidHomesMaddoxPlanScraper(BaseScraper):
    URL = "https://www.davidsonhomes.com/states/georgia/atlanta-market-area/hoschton/wehunt-meadows"
    
    def parse_sqft_from_description(self, description):
        """Extract square footage from description text."""
        # Look for patterns like "2,200 Sq Ft" or "2200 Sq Ft"
        match = re.search(r'([\d,]+)\s*Sq\s*Ft', description, re.IGNORECASE)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds_from_description(self, description):
        """Extract number of bedrooms from description text."""
        # Look for patterns like "3 Beds" or "4 Beds"
        match = re.search(r'(\d+)\s*Beds?', description, re.IGNORECASE)
        return str(match.group(1)) if match else ""

    def parse_baths_from_description(self, description):
        """Extract number of bathrooms from description text."""
        # Look for patterns like "2.5 Baths" or "3.5 Baths"
        match = re.search(r'(\d+(?:\.\d+)?)\s*Baths?', description, re.IGNORECASE)
        return str(match.group(1)) if match else ""

    def parse_price_from_html(self, html_content):
        """Extract price from HTML content."""
        # Look for patterns like "$415,900+" or "$415,900"
        match = re.search(r'\$([\d,]+)', html_content)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_sqft_from_html(self, html_content):
        """Extract square footage from HTML content."""
        # Look for patterns like "2,200" in the square footage section
        match = re.search(r'<span class="font-semibold text-blue">([\d,]+)</span>\s*Sf', html_content)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds_from_html(self, html_content):
        """Extract number of bedrooms from HTML content."""
        # Look for patterns like "3" in the bedroom section
        match = re.search(r'<span class="font-semibold text-blue">(\d+)</span>\s*Bd', html_content)
        return str(match.group(1)) if match else ""

    def parse_baths_from_html(self, html_content):
        """Extract number of bathrooms from HTML content."""
        # Look for patterns like "2.5" in the bathroom section
        match = re.search(r'<span class="font-semibold text-blue">(\d+(?:\.\d+)?)</span>\s*Ba', html_content)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DavidHomesMaddoxPlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DavidHomesMaddoxPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[DavidHomesMaddoxPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all plan cards with JSON-LD structured data
            plan_cards = soup.find_all('div', class_='relative flex h-full flex-col overflow-hidden rounded bg-white text-center shadow transition-transform hover:-translate-y-2')
            print(f"[DavidHomesMaddoxPlanScraper] Found {len(plan_cards)} plan cards")
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[DavidHomesMaddoxPlanScraper] Processing card {idx+1}")
                    
                    # Find the JSON-LD script tag
                    json_script = card.find('script', type='application/ld+json')
                    if not json_script:
                        print(f"[DavidHomesMaddoxPlanScraper] Skipping card {idx+1}: No JSON-LD script found")
                        continue
                    
                    # Parse the JSON-LD data
                    try:
                        json_data = json.loads(json_script.string)
                    except json.JSONDecodeError as e:
                        print(f"[DavidHomesMaddoxPlanScraper] Skipping card {idx+1}: Invalid JSON-LD data: {e}")
                        continue
                    
                    # Extract plan information from JSON-LD
                    plan_name = json_data.get('name', '')
                    if not plan_name:
                        print(f"[DavidHomesMaddoxPlanScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[DavidHomesMaddoxPlanScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract price from offers
                    offers = json_data.get('offers', {})
                    starting_price = offers.get('price')
                    if not starting_price:
                        print(f"[DavidHomesMaddoxPlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract description for beds/baths/sqft
                    description = json_data.get('description', '')
                    
                    # Parse beds, baths, and sqft from description
                    beds = self.parse_beds_from_description(description)
                    baths = self.parse_baths_from_description(description)
                    sqft = self.parse_sqft_from_description(description)
                    
                    # If we couldn't parse from description, try to extract from HTML
                    if not sqft or not beds or not baths:
                        card_html = str(card)
                        if not sqft:
                            sqft = self.parse_sqft_from_html(card_html)
                        if not beds:
                            beds = self.parse_beds_from_html(card_html)
                        if not baths:
                            baths = self.parse_baths_from_html(card_html)
                    
                    # If still no sqft, estimate based on beds
                    if not sqft:
                        if beds:
                            bed_count = int(beds.split('.')[0]) if '.' in beds else int(beds)
                            if bed_count >= 4:
                                sqft = 2500  # Large homes with 4+ beds
                            elif bed_count >= 3:
                                sqft = 2000  # Medium homes with 3 beds
                            else:
                                sqft = 1500  # Smaller homes
                        else:
                            sqft = 2000  # Default estimate
                        
                        print(f"[DavidHomesMaddoxPlanScraper] Estimated square footage for plan '{plan_name}': {sqft}")
                    
                    # Calculate price per sqft
                    price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                    
                    # Extract address (same as plan name for floor plans)
                    address = plan_name
                    
                    plan_data = {
                        "price": starting_price,
                        "sqft": sqft,
                        "stories": "",  # Not available in the data
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "David Homes",
                        "community": "Maddox",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": ""
                    }
                    
                    print(f"[DavidHomesMaddoxPlanScraper] Card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[DavidHomesMaddoxPlanScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[DavidHomesMaddoxPlanScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[DavidHomesMaddoxPlanScraper] Error: {e}")
            return []

