import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class DavidWeekleyHomesCreeksideNowScraper(BaseScraper):
    URL = "https://www.davidweekleyhomes.com/new-homes/tx/dallas-ft-worth/royse-city/creekshaw-classic"
    
    def parse_price(self, text):
        """Extract price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'Sq\. Ft:\s*(\d+)', text)
        return int(match.group(1)) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def parse_garages(self, text):
        """Extract number of garages from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def extract_property_data(self, property_card):
        """Extract data from a property card div."""
        try:
            # Extract plan name from the title
            plan_title_elem = property_card.find('h2', class_='plan-title')
            plan_name = ""
            if plan_title_elem:
                plan_link = plan_title_elem.find('a')
                if plan_link:
                    plan_name = plan_link.get_text(strip=True)
                    # Remove "The " prefix if present
                    if plan_name.startswith("The "):
                        plan_name = plan_name[4:]

            # For Quick Move-ins, we should have addresses
            # Look for address in the plan card structure
            address = ""
            
            # First, try to find the address span element
            address_elem = property_card.find('span', class_='plan-address')
            if address_elem:
                address = address_elem.get_text(strip=True)
            else:
                # Fallback: try to find address in the plan card text
                card_text = property_card.get_text()
                
                # Look for address patterns in the text
                address_patterns = [
                    r'(\d+\s+\w+\s+\w+,\s+\w+\s+\w+,\s+TX\s+\d{5})',  # Full address pattern
                    r'(\d+\s+\w+\s+\w+)',  # Street address pattern
                ]
                
                for pattern in address_patterns:
                    address_match = re.search(pattern, card_text)
                    if address_match:
                        address = address_match.group(1)
                        break
            
            # If no address found, use plan name as fallback
            if not address:
                address = f"{plan_name} Plan" if plan_name else "Unknown Address"

            # Extract price from first-level-properties
            price_elem = property_card.find('div', class_='first-level-properties')
            price = None
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # For Quick Move-ins, price might not have "From:" prefix
                if 'From:' in price_text:
                    price = self.parse_price(price_text)
                else:
                    # Direct price format like "$394,990"
                    price_match = re.search(r'\$([\d,]+)', price_text)
                    if price_match:
                        price = int(price_match.group(1).replace(",", ""))

            # Extract square footage from first-level-properties
            sqft = None
            if price_elem:
                sqft_text = price_elem.get_text(strip=True)
                sqft = self.parse_sqft(sqft_text)

            # Extract features from second-level-properties
            features_section = property_card.find('div', class_='second-level-properties')
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
                    bed_match = re.search(r'Bedrooms\s*(\d+)', features_text)
                    if bed_match:
                        beds = bed_match.group(1)
                
                # Extract baths if not found
                if not baths:
                    bath_match = re.search(r'Full Baths\s*(\d+)', features_text)
                    if bath_match:
                        baths = bath_match.group(1)
                
                # Extract garages if not found
                if not garages:
                    garage_match = re.search(r'Car Garage\s*(\d+)', features_text)
                    if garage_match:
                        garages = garage_match.group(1)

            # Extract status from image tag
            status = "Available"
            image_tag = property_card.find('span', class_='label')
            if image_tag:
                status_text = image_tag.get_text(strip=True)
                if "Ready Now" in status_text:
                    status = "Ready Now"
                elif "Ready" in status_text:
                    status = status_text

            # Extract plan number
            plan_number_elem = property_card.find('div', class_='blue plan-number')
            plan_number = ""
            if plan_number_elem:
                plan_link = plan_number_elem.find('a')
                if plan_link:
                    plan_number = plan_link.get_text(strip=True)
                    # Extract just the number from "Plan XXXX"
                    plan_match = re.search(r'Plan\s+(\d+)', plan_number)
                    if plan_match:
                        plan_number = plan_match.group(1)

            return {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "plan_name": address,  # Use address as plan_name for inventory
                "floor_plan_name": plan_name,  # Store actual floor plan name
                "beds": beds,
                "baths": baths,
                "status": status,
                "address": address,
                "plan_number": plan_number,
                "garages": garages
            }

        except Exception as e:
            print(f"[DavidWeekleyHomesCreeksideNowScraper] Error extracting property data: {e}")
            return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DavidWeekleyHomesCreeksideNowScraper] Fetching URL: {self.URL}")

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
            print(f"[DavidWeekleyHomesCreeksideNowScraper] Response status: {resp.status_code}")

            if resp.status_code != 200:
                print(f"[DavidWeekleyHomesCreeksideNowScraper] Request failed with status {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.content, 'html.parser')

            # Look for the content div with data-bind="with: compareHomes"
            content_div = soup.find('div', class_='pure-g content', attrs={'data-bind': 'with: compareHomes'})
            if not content_div:
                print("[DavidWeekleyHomesCreeksideNowScraper] Could not find content div with compareHomes")
                return []

            # Find all plan cards first
            all_plan_cards = content_div.find_all('div', class_='plan-card')
            print(f"[DavidWeekleyHomesCreeksideNowScraper] Found {len(all_plan_cards)} plan cards in main content")
            
            # Also search for any additional plan cards that might be outside the main content div
            # (This is where inventory homes are often located)
            additional_plan_cards = soup.find_all('div', class_='plan-card')
            if len(additional_plan_cards) > len(all_plan_cards):
                print(f"[DavidWeekleyHomesCreeksideNowScraper] Found {len(additional_plan_cards)} total plan cards on the page")
                all_plan_cards = additional_plan_cards
            
            # Filter for Quick Move-ins based on data characteristics
            # Quick Move-ins typically have addresses and different price formats
            plan_cards = []
            for card in all_plan_cards:
                # Look for indicators that this is a Quick Move-in (inventory home)
                is_quick_move_in = False
                
                # Check for address element - this is the most reliable indicator
                address_elem = card.find('span', class_='plan-address')
                if address_elem:
                    is_quick_move_in = True
                
                # Check for "Ready" status labels
                ready_labels = card.find_all('span', class_='label image-tag')
                for label in ready_labels:
                    label_text = label.get_text(strip=True)
                    if any(status in label_text for status in ['Ready Now', 'Ready', 'Est. Completion']):
                        is_quick_move_in = True
                        break
                
                # Check for price format (Quick Move-ins often don't have "From:" prefix)
                price_elem = card.find('div', class_='first-level-properties')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    if '$' in price_text and 'From:' not in price_text:
                        is_quick_move_in = True
                
                if is_quick_move_in:
                    plan_cards.append(card)
            
            print(f"[DavidWeekleyHomesCreeksideNowScraper] Filtered to {len(plan_cards)} Quick Move-in cards")
            
            # If no Quick Move-ins found, return empty list
            if not plan_cards:
                print("[DavidWeekleyHomesCreeksideNowScraper] No Quick Move-in homes found")
                print("[DavidWeekleyHomesCreeksideNowScraper] This could be because:")
                print("[DavidWeekleyHomesCreeksideNowScraper] - All homes are sold")
                print("[DavidWeekleyHomesCreeksideNowScraper] - Inventory homes are loaded dynamically")
                print("[DavidWeekleyHomesCreeksideNowScraper] - Inventory homes are on a different page")
                print("[DavidWeekleyHomesCreeksideNowScraper] - Website structure has changed")
                return []
            
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates

            for card_idx, plan_card in enumerate(plan_cards):
                try:
                    print(f"[DavidWeekleyHomesCreeksideNowScraper] Processing card {card_idx + 1}")

                    # Extract data from the plan card
                    property_data = self.extract_property_data(plan_card)
                    if not property_data:
                        print(f"[DavidWeekleyHomesCreeksideNowScraper] Card {card_idx + 1}: Failed to extract property data")
                        continue

                    # Check for required fields - require plan name
                    if not property_data.get('floor_plan_name'):
                        print(f"[DavidWeekleyHomesCreeksideNowScraper] Card {card_idx + 1}: Missing plan name")
                        continue

                    # Check for duplicate plan names
                    plan_name = property_data.get('floor_plan_name')
                    if plan_name in seen_plan_names:
                        print(f"[DavidWeekleyHomesCreeksideNowScraper] Card {card_idx + 1}: Duplicate plan name {plan_name}")
                        continue
                    seen_plan_names.add(plan_name)

                    # Calculate price per square foot if both price and sqft are available
                    price_per_sqft = None
                    if property_data.get('price') and property_data.get('sqft'):
                        price_per_sqft = round(property_data['price'] / property_data['sqft'], 2) if property_data['sqft'] > 0 else None

                    # Create the final listing data
                    final_listing_data = {
                        "price": property_data['price'],
                        "sqft": property_data['sqft'],
                        "stories": property_data['stories'],
                        "price_per_sqft": price_per_sqft,
                        "plan_name": property_data['address'],  # Use address as plan_name for inventory
                        "floor_plan_name": property_data['floor_plan_name'],  # Store actual floor plan name
                        "company": "David Weekley Homes",
                        "community": "Creekside",
                        "type": "now",
                        "beds": property_data['beds'],
                        "baths": property_data['baths'],
                        "status": property_data['status'],
                        "address": property_data['address'],
                        "plan_number": property_data['plan_number'],
                        "garages": property_data['garages']
                    }

                    print(f"[DavidWeekleyHomesCreeksideNowScraper] Card {card_idx + 1}: {final_listing_data}")
                    listings.append(final_listing_data)

                except Exception as e:
                    print(f"[DavidWeekleyHomesCreeksideNowScraper] Error processing card {card_idx + 1}: {e}")
                    continue

            print(f"[DavidWeekleyHomesCreeksideNowScraper] Successfully processed {len(listings)} total listings")
            return listings

        except Exception as e:
            print(f"[DavidWeekleyHomesCreeksideNowScraper] Error: {e}")
            return []
