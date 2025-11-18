import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class RockwellHomesCreeksideNowScraper(BaseScraper):
    URLS = [
        "https://www.rockwell-homes.com/new-homes/tx/royse-city/creekside/14633/"
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
        match = re.search(r'(\d+\.?\d*)', text)
        return str(match.group(1)) if match else None

    def parse_stories(self, text):
        """Extract number of stories from text."""
        # Default to 1 story for single-family homes
        return "1"

    def extract_property_data(self, property_card):
        """Extract data from a property card div."""
        try:
            # Extract address from the card title
            address = None
            title_elem = property_card.find('span', class_='card-location')
            if title_elem:
                address = title_elem.get_text(strip=True)

            # Extract plan name (elevation)
            plan_name = None
            elevation_elem = property_card.find('div', class_='elevation-count')
            if elevation_elem:
                plan_name = elevation_elem.get_text(strip=True).strip()

            # Extract price
            price = None
            price_elem = property_card.find('div', class_='card-price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self.parse_price(price_text)

            # Extract status
            status = "Now"
            status_elem = property_card.find('div', class_='card-status')
            if status_elem:
                status_text = status_elem.get_text(strip=True)
                if status_text:
                    status = status_text

            # Extract features from the stats section
            beds = None
            baths = None
            sqft = None

            stats_elem = property_card.find('div', class_='card-stats')
            if stats_elem:
                # Look for bed/bath/sqft/garage stats
                stat_elements = stats_elem.find_all('span', class_='card-stat-text')
                for stat in stat_elements:
                    stat_text = stat.get_text(strip=True)
                    
                    if 'sqft-stat' in stat.get('class', []):
                        sqft = self.parse_sqft(stat_text)
                    elif 'bed-stat' in stat.get('class', []):
                        beds = self.parse_beds(stat_text)
                    elif 'bath-stat' in stat.get('class', []):
                        baths = self.parse_baths(stat_text)

            # Extract stories (default to 1)
            stories = "1"

            # Check for move-in date in status
            if status and any(keyword in status.lower() for keyword in ['move in', 'september', 'quick move']):
                status = f"Now - {status}"

            return {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "plan_name": plan_name or address,  # Use elevation name if available, otherwise address
                "beds": beds,
                "baths": baths,
                "status": status,
                "address": address
            }

        except Exception as e:
            print(f"[RockwellHomesCreeksideNowScraper] Error extracting property data: {e}")
            return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[RockwellHomesCreeksideNowScraper] Fetching URLs: {self.URLS}")

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
                    print(f"[RockwellHomesCreeksideNowScraper] Processing URL {url_idx + 1}: {url}")

                    resp = requests.get(url, headers=headers, timeout=15)
                    print(f"[RockwellHomesCreeksideNowScraper] URL {url_idx + 1} response status: {resp.status_code}")

                    if resp.status_code != 200:
                        print(f"[RockwellHomesCreeksideNowScraper] URL {url_idx + 1} request failed with status {resp.status_code}")
                        continue

                    soup = BeautifulSoup(resp.content, 'html.parser')

                    # Look for property cards with class "plan-card"
                    property_cards = soup.find_all('div', class_='plan-card')
                    print(f"[RockwellHomesCreeksideNowScraper] URL {url_idx + 1}: Found {len(property_cards)} property cards")

                    for card_idx, property_card in enumerate(property_cards):
                        try:
                            print(f"[RockwellHomesCreeksideNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Processing property card")

                            # Extract data from the property card
                            property_data = self.extract_property_data(property_card)
                            if not property_data:
                                print(f"[RockwellHomesCreeksideNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Failed to extract property data")
                                continue

                            # Check for required fields - only require address
                            if not property_data.get('address'):
                                print(f"[RockwellHomesCreeksideNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Missing address")
                                continue

                            # Check for duplicate properties - use address as unique identifier
                            address = property_data.get('address')
                            if address in seen_properties:
                                print(f"[RockwellHomesCreeksideNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Duplicate property {address}")
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
                                "plan_name": property_data['plan_name'],
                                "company": "Rockwell Homes",
                                "community": "Creekside",
                                "type": "now",
                                "beds": property_data['beds'],
                                "baths": property_data['baths'],
                                "status": property_data['status'],
                                "address": address
                            }

                            print(f"[RockwellHomesCreeksideNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: {listing_data}")
                            all_listings.append(listing_data)

                        except Exception as e:
                            print(f"[RockwellHomesCreeksideNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Error processing card: {e}")
                            continue

                except Exception as e:
                    print(f"[RockwellHomesCreeksideNowScraper] Error processing URL {url_idx + 1}: {e}")
                    continue

            print(f"[RockwellHomesCreeksideNowScraper] Successfully processed {len(all_listings)} total listings across all URLs")
            return all_listings

        except Exception as e:
            print(f"[RockwellHomesCreeksideNowScraper] Error: {e}")
            return []
