import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class DavidWeekleyHomesCreeksidePlanScraper(BaseScraper):
    URL = "https://www.davidweekleyhomes.com/new-homes/tx/dallas-ft-worth/royse-city/creekshaw-gardens"
    
    def parse_price(self, text):
        """Extract starting price from text."""
        match = re.search(r'From:\s*\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'Sq\. Ft:\s*(\d+(?:\s*-\s*\d+)?)', text)
        if match:
            sqft_text = match.group(1)
            # Handle ranges like "1643 - 1861"
            if ' - ' in sqft_text:
                # Take the first number for simplicity
                first_num = re.search(r'(\d+)', sqft_text)
                return int(first_num.group(1)) if first_num else None
            else:
                return int(sqft_text)
        return None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:\s*-\s*\d+)?)', text)
        if match:
            beds_text = match.group(1)
            # Handle ranges like "3 - 5"
            if ' - ' in beds_text:
                # Take the first number for simplicity
                first_num = re.search(r'(\d+)', beds_text)
                return first_num.group(1) if first_num else ""
            else:
                return beds_text
        return ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\s*-\s*\d+)?)', text)
        if match:
            baths_text = match.group(1)
            # Handle ranges like "2 - 3"
            if ' - ' in baths_text:
                # Take the first number for simplicity
                first_num = re.search(r'(\d+)', baths_text)
                return first_num.group(1) if first_num else ""
            else:
                return baths_text
        return ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def parse_garages(self, text):
        """Extract number of garages from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def extract_plan_data(self, plan_card):
        """Extract data from a plan card div."""
        try:
            # Extract plan name from the title
            plan_title_elem = plan_card.find('h2', class_='plan-title')
            plan_name = ""
            if plan_title_elem:
                plan_link = plan_title_elem.find('a')
                if plan_link:
                    plan_name = plan_link.get_text(strip=True)
                    # Remove "The " prefix if present
                    if plan_name.startswith("The "):
                        plan_name = plan_name[4:]

            # Extract plan number
            plan_number_elem = plan_card.find('div', class_='blue plan-number')
            plan_number = ""
            if plan_number_elem:
                plan_link = plan_number_elem.find('a')
                if plan_link:
                    plan_number = plan_link.get_text(strip=True)
                    # Extract just the number from "Plan XXXX"
                    plan_match = re.search(r'Plan\s+(\w+)', plan_number)
                    if plan_match:
                        plan_number = plan_match.group(1)

            # Extract price from first-level-properties
            price_elem = plan_card.find('div', class_='first-level-properties')
            price = None
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self.parse_price(price_text)

            # Extract square footage from first-level-properties
            sqft = None
            if price_elem:
                sqft_text = price_elem.get_text(strip=True)
                sqft = self.parse_sqft(sqft_text)

            # Extract features from second-level-properties
            features_section = plan_card.find('div', class_='second-level-properties')
            beds = ""
            baths = ""
            stories = "1"
            garages = ""

            if features_section:
                # Extract stories
                story_elem = features_section.find('div', class_='feature', string=re.compile(r'Story', re.IGNORECASE))
                if story_elem:
                    story_value = story_elem.find('div', class_='value')
                    if story_value:
                        stories = self.parse_stories(story_value.get_text(strip=True))

                # Extract bedrooms
                bed_elem = features_section.find('div', class_='feature', string=re.compile(r'Bedrooms', re.IGNORECASE))
                if bed_elem:
                    bed_value = bed_elem.find('div', class_='value')
                    if bed_value:
                        beds = self.parse_beds(bed_value.get_text(strip=True))

                # Extract bathrooms
                bath_elem = features_section.find('div', class_='feature', string=re.compile(r'Full Baths', re.IGNORECASE))
                if bath_elem:
                    bath_value = bath_elem.find('div', class_='value')
                    if bath_value:
                        baths = self.parse_baths(bath_value.get_text(strip=True))

                # Extract garages
                garage_elem = features_section.find('div', class_='feature', string=re.compile(r'Car Garage', re.IGNORECASE))
                if garage_elem:
                    garage_value = garage_elem.find('div', class_='value')
                    if garage_value:
                        garages = self.parse_garages(garage_value.get_text(strip=True))

            # If features weren't found in the structured section, try to extract from the raw text
            if not beds or not baths or not garages:
                features_text = features_section.get_text(strip=True) if features_section else ""
                
                # Extract beds if not found
                if not beds:
                    bed_match = re.search(r'Bedrooms\s*(\d+(?:\s*-\s*\d+)?)', features_text)
                    if bed_match:
                        beds = self.parse_beds(bed_match.group(1))
                
                # Extract baths if not found
                if not baths:
                    bath_match = re.search(r'Full Baths\s*(\d+(?:\s*-\s*\d+)?)', features_text)
                    if bath_match:
                        baths = self.parse_baths(bath_match.group(1))
                
                # Extract garages if not found
                if not garages:
                    garage_match = re.search(r'Car Garage\s*(\d+)', features_text)
                    if garage_match:
                        garages = garage_match.group(1)

            return {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "plan_name": plan_name,
                "plan_number": plan_number,
                "beds": beds,
                "baths": baths,
                "garages": garages
            }

        except Exception as e:
            print(f"[DavidWeekleyHomesCreeksidePlanScraper] Error extracting plan data: {e}")
            return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DavidWeekleyHomesCreeksidePlanScraper] Fetching URL: {self.URL}")

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "identity",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DavidWeekleyHomesCreeksidePlanScraper] Response status: {resp.status_code}")

            if resp.status_code != 200:
                print(f"[DavidWeekleyHomesCreeksidePlanScraper] Request failed with status {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.content, 'html.parser')

            # Look for the content div with data-bind="with: compareHomes"
            content_div = soup.find('div', class_='pure-g content', attrs={'data-bind': 'with: compareHomes'})
            if not content_div:
                print("[DavidWeekleyHomesCreeksidePlanScraper] Could not find content div with compareHomes")
                return []

            # Find all plan cards
            plan_cards = content_div.find_all('div', class_='plan-card')
            print(f"[DavidWeekleyHomesCreeksidePlanScraper] Found {len(plan_cards)} plan cards")

            plans = []
            seen_plan_names = set()  # Track plan names to prevent duplicates

            for card_idx, plan_card in enumerate(plan_cards):
                try:
                    print(f"[DavidWeekleyHomesCreeksidePlanScraper] Processing card {card_idx + 1}")

                    # Extract data from the plan card
                    plan_data = self.extract_plan_data(plan_card)
                    if not plan_data:
                        print(f"[DavidWeekleyHomesCreeksidePlanScraper] Card {card_idx + 1}: Failed to extract plan data")
                        continue

                    # Check for required fields - require plan name
                    if not plan_data.get('plan_name'):
                        print(f"[DavidWeekleyHomesCreeksidePlanScraper] Card {card_idx + 1}: Missing plan name")
                        continue

                    # Check for duplicate plan names
                    plan_name = plan_data.get('plan_name')
                    if plan_name in seen_plan_names:
                        print(f"[DavidWeekleyHomesCreeksidePlanScraper] Card {card_idx + 1}: Duplicate plan name {plan_name}")
                        continue
                    seen_plan_names.add(plan_name)

                    # Calculate price per square foot if both price and sqft are available
                    price_per_sqft = None
                    if plan_data.get('price') and plan_data.get('sqft'):
                        price_per_sqft = round(plan_data['price'] / plan_data['sqft'], 2) if plan_data['sqft'] > 0 else None

                    # Create the final plan data
                    final_plan_data = {
                        "price": plan_data['price'],
                        "sqft": plan_data['sqft'],
                        "stories": plan_data['stories'],
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_data['plan_name'],
                        "company": "David Weekley Homes",
                        "community": "Creekside",
                        "type": "plan",
                        "beds": plan_data['beds'],
                        "baths": plan_data['baths'],
                        "garages": plan_data['garages'],
                        "plan_number": plan_data['plan_number']
                    }

                    print(f"[DavidWeekleyHomesCreeksidePlanScraper] Card {card_idx + 1}: {final_plan_data}")
                    plans.append(final_plan_data)

                except Exception as e:
                    print(f"[DavidWeekleyHomesCreeksidePlanScraper] Error processing card {card_idx + 1}: {e}")
                    continue

            print(f"[DavidWeekleyHomesCreeksidePlanScraper] Successfully processed {len(plans)} total plans")
            return plans

        except Exception as e:
            print(f"[DavidWeekleyHomesCreeksidePlanScraper] Error: {e}")
            return []
