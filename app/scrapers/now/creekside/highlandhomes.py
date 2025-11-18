import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class HighlandHomesCreeksideNowScraper(BaseScraper):
    URLS = [
        "https://www.highlandhomes.com/dfw/royse-city/creekshaw"
    ]

    def parse_sqft(self, text):
        """Extract square footage from text."""
        if not text:
            return None
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text."""
        if not text:
            return None
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        if not text:
            return None
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else None

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        if not text:
            return None
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else None

    def parse_stories(self, text):
        """Extract number of stories from text."""
        if not text:
            return None
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else None

    def extract_property_data(self, property_card):
        """Extract data from a property card div."""
        try:
            # Extract address from the home identifier
            address = None
            address_elem = property_card.find('span', class_='homeIdentifier')
            if address_elem:
                address = address_elem.get_text(strip=True)

            # Extract price
            price = None
            price_elem = property_card.find('span', class_='price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self.parse_price(price_text)

            # Extract plan name from home upgrades
            plan_name = None
            upgrades_elem = property_card.find('p', class_='homeUpgrades')
            if upgrades_elem:
                upgrades_text = upgrades_elem.get_text(strip=True)
                # Extract plan name (e.g., "Easton Plan with 5 upgrades" -> "Easton")
                plan_match = re.search(r'^([A-Za-z]+)\s+Plan', upgrades_text)
                if plan_match:
                    plan_name = plan_match.group(1)

            # Extract features from the home details
            beds = None
            baths = None
            stories = None
            sqft = None

            home_details = property_card.find('div', class_='homeDetails')
            if home_details:
                detail_items = home_details.find_all('div', class_='homeDetailItem')
                for item in detail_items:
                    label_elem = item.find('span', class_='label')
                    numeral_elem = item.find('span', class_='numeral')
                    if label_elem and numeral_elem:
                        label = label_elem.get_text(strip=True).lower()
                        numeral = numeral_elem.get_text(strip=True)
                        
                        if 'bed' in label:
                            beds = numeral
                        elif 'bath' in label:
                            baths = numeral
                        elif 'stor' in label:
                            stories = numeral

            # Extract square footage
            sqft_elem = property_card.find('div', class_='homeSqFootage')
            if sqft_elem:
                numeral_elem = sqft_elem.find('span', class_='numeral')
                if numeral_elem:
                    sqft_text = numeral_elem.get_text(strip=True)
                    sqft = self.parse_sqft(sqft_text)

            # Extract status from home tag
            status = "Now"
            status_elem = property_card.find('span', class_='home-tag')
            if status_elem:
                status_text = status_elem.get_text(strip=True)
                if status_text:
                    status = status_text

            return {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "plan_name": address,  # Use address as plan_name for inventory
                "floor_plan_name": plan_name,  # Store actual floor plan name
                "beds": beds,
                "baths": baths,
                "status": status,
                "address": address
            }

        except Exception as e:
            print(f"[HighlandHomesCreeksideNowScraper] Error extracting property data: {e}")
            return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[HighlandHomesCreeksideNowScraper] Fetching URLs: {self.URLS}")

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "identity",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            all_listings = []
            seen_properties = set()  # Track properties to prevent duplicates

            for url_idx, url in enumerate(self.URLS):
                try:
                    print(f"[HighlandHomesCreeksideNowScraper] Processing URL {url_idx + 1}: {url}")

                    resp = requests.get(url, headers=headers, timeout=15)
                    print(f"[HighlandHomesCreeksideNowScraper] URL {url_idx + 1} response status: {resp.status_code}")

                    if resp.status_code != 200:
                        print(f"[HighlandHomesCreeksideNowScraper] URL {url_idx + 1} request failed with status {resp.status_code}")
                        continue

                    soup = BeautifulSoup(resp.content, 'html.parser')

                    # Look for property cards with class "home-container-column-block"
                    property_cards = soup.find_all('div', class_='home-container-column-block')
                    print(f"[HighlandHomesCreeksideNowScraper] URL {url_idx + 1}: Found {len(property_cards)} property cards")

                    for card_idx, property_card in enumerate(property_cards):
                        try:
                            print(f"[HighlandHomesCreeksideNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Processing property card")

                            # Extract data from the property card
                            property_data = self.extract_property_data(property_card)
                            if not property_data:
                                print(f"[HighlandHomesCreeksideNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Failed to extract property data")
                                continue

                            # Check for required fields - only require address
                            if not property_data.get('address'):
                                print(f"[HighlandHomesCreeksideNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Missing address")
                                continue

                            # Check for duplicate properties - use address as unique identifier
                            address = property_data.get('address')
                            if address in seen_properties:
                                print(f"[HighlandHomesCreeksideNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Duplicate property {address}")
                                continue
                            seen_properties.add(address)

                            # Calculate price per square foot if both price and sqft are available
                            price_per_sqft = None
                            if property_data.get('price') and property_data.get('sqft'):
                                price_per_sqft = round(property_data['price'] / property_data['sqft'], 2) if property_data['sqft'] > 0 else None

                            # Create the final listing data
                            listing_data = {
                                "price": property_data['price'],
                                "sqft": property_data['sqft'],
                                "stories": property_data['stories'],
                                "price_per_sqft": price_per_sqft,
                                "plan_name": address,  # Use address as plan_name for inventory
                                "floor_plan_name": property_data.get('floor_plan_name'),  # Store actual floor plan name
                                "company": "Highland Homes",
                                "community": "Creekside",
                                "type": "now",
                                "beds": property_data['beds'],
                                "baths": property_data['baths'],
                                "status": property_data['status'],
                                "address": address
                            }

                            print(f"[HighlandHomesCreeksideNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: {listing_data}")
                            all_listings.append(listing_data)

                        except Exception as e:
                            print(f"[HighlandHomesCreeksideNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Error processing card: {e}")
                            continue

                except Exception as e:
                    print(f"[HighlandHomesCreeksideNowScraper] Error processing URL {url_idx + 1}: {e}")
                    continue

            print(f"[HighlandHomesCreeksideNowScraper] Successfully processed {len(all_listings)} total listings across all URLs")
            return all_listings

        except Exception as e:
            print(f"[HighlandHomesCreeksideNowScraper] Error: {e}")
            return []
