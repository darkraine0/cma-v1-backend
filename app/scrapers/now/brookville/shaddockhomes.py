import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class ShaddockHomesBrookvilleNowScraper(BaseScraper):
    URLS = [
        "https://www.shaddockhomes.com/communities/forney/devonshire"
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
        
        # Handle individual prices like "$499,900"
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
        # Handle fractional baths like "2.5" or "2 .5"
        text = text.replace(' ', '')
        match = re.search(r'(\d+\.?\d*)', text)
        return str(match.group(1)) if match else None

    def parse_stories(self, text):
        """Extract number of stories from text."""
        if not text:
            return "1"
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def extract_property_data(self, property_card):
        """Extract data from a property card div."""
        try:
            # Extract address from span.HomeCard_city
            address = None
            city_elem = property_card.find('span', class_='HomeCard_city')
            if city_elem:
                address = city_elem.get_text(strip=True)
                # Clean up any extra whitespace
                address = re.sub(r'\s+', ' ', address).strip()
            
            # Extract price from div.HomeCard_priceValue
            price = None
            price_elem = property_card.find('div', class_='HomeCard_priceValue')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self.parse_price(price_text)
            
            # Extract status from div.HomeCard_statusBanner > span.active
            status = "Now"
            status_banner = property_card.find('div', class_='HomeCard_statusBanner')
            if status_banner:
                status_span = status_banner.find('span', class_='active')
                if status_span:
                    status_text = status_span.get_text(strip=True)
                    if status_text:
                        status = status_text
            
            # Extract features from ul.HomeCard_contentRow > li.HomeCard_specItem
            beds = None
            baths = None
            sqft = None
            
            feature_list = property_card.find('ul', class_='HomeCard_contentRow')
            if feature_list:
                features = feature_list.find_all('li', class_='HomeCard_specItem')
                for feature in features:
                    # Get the label to identify what this feature is
                    label_elem = feature.find('span', class_='HomeCard_iconListLabel')
                    value_elem = feature.find('span', class_='HomeCard_iconListValue')
                    
                    if label_elem and value_elem:
                        label_text = label_elem.get_text(strip=True)
                        value_text = value_elem.get_text(strip=True)
                        
                        if 'Beds' in label_text:
                            beds = self.parse_beds(value_text)
                        elif 'Baths' in label_text:
                            # Handle fractional baths - get all text and clean it up
                            bath_text = value_elem.get_text(strip=True)
                            # Replace spaces to handle "2 .5" -> "2.5"
                            bath_text = bath_text.replace(' ', '')
                            baths = self.parse_baths(bath_text) if bath_text else None
                        elif 'SQ FT' in label_text:
                            sqft = self.parse_sqft(value_text)
            
            # Extract plan name from ul.HomeCard_contentRowAlt > li.HomeCard_specItemAlt > a[href*="/plan/"]
            plan_name = None
            alt_list = property_card.find('ul', class_='HomeCard_contentRowAlt')
            if alt_list:
                alt_items = alt_list.find_all('li', class_='HomeCard_specItemAlt')
                for item in alt_items:
                    plan_link = item.find('a', href=re.compile(r'/plan/'))
                    if plan_link:
                        plan_name = plan_link.get_text(strip=True)
                        break
            
            # Extract stories (default to 1 if not found)
            stories = "1"
            
            return {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "plan_name": plan_name,
                "beds": beds,
                "baths": baths,
                "status": status,
                "address": address
            }
            
        except Exception as e:
            print(f"[ShaddockHomesBrookvilleNowScraper] Error extracting property data: {e}")
            return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[ShaddockHomesBrookvilleNowScraper] Fetching URLs: {self.URLS}")
            
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
                    print(f"[ShaddockHomesBrookvilleNowScraper] Processing URL {url_idx + 1}: {url}")
                    
                    resp = requests.get(url, headers=headers, timeout=15)
                    print(f"[ShaddockHomesBrookvilleNowScraper] URL {url_idx + 1} response status: {resp.status_code}")
                    
                    if resp.status_code != 200:
                        print(f"[ShaddockHomesBrookvilleNowScraper] URL {url_idx + 1} request failed with status {resp.status_code}")
                        continue
                    
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    
                    # Look for property cards with class "HomeCard_wrapper" (these are the home cards)
                    property_cards = soup.find_all('div', class_='HomeCard_wrapper')
                    print(f"[ShaddockHomesBrookvilleNowScraper] URL {url_idx + 1}: Found {len(property_cards)} property cards")
                    
                    for card_idx, property_card in enumerate(property_cards):
                        try:
                            print(f"[ShaddockHomesBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Processing property card")
                            
                            # Extract data from the property card
                            property_data = self.extract_property_data(property_card)
                            if not property_data:
                                print(f"[ShaddockHomesBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Failed to extract property data")
                                continue
                            
                            # Check for required fields - only require address, plan_name is optional
                            if not property_data.get('address'):
                                print(f"[ShaddockHomesBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Missing address")
                                continue
                            
                            # Check for duplicate properties - use address as unique identifier
                            address = property_data.get('address')
                            if address in seen_properties:
                                print(f"[ShaddockHomesBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Duplicate property {address}")
                                continue
                            seen_properties.add(address)
                            
                            # Calculate price per square foot if both price and sqft are available
                            price_per_sqft = None
                            if property_data.get('price') and property_data.get('sqft'):
                                price_per_sqft = round(property_data['price'] / property_data['sqft'], 2) if property_data['sqft'] > 0 else None
                            
                            # Create the final listing data
                            # For inventory data, use the address as plan_name and store the floor plan name separately
                            listing_data = {
                                "price": property_data['price'],
                                "sqft": property_data['sqft'],
                                "stories": property_data['stories'],
                                "price_per_sqft": price_per_sqft,
                                "plan_name": address,  # Use address as plan_name for inventory
                                "company": "Shaddock Homes",
                                "community": "Brookville",
                                "type": "now",
                                "beds": property_data['beds'],
                                "baths": property_data['baths'],
                                "status": property_data['status'],
                                "address": address
                            }
                            
                            print(f"[ShaddockHomesBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: {listing_data}")
                            all_listings.append(listing_data)
                            
                        except Exception as e:
                            print(f"[ShaddockHomesBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Error processing card: {e}")
                            continue
                    
                except Exception as e:
                    print(f"[ShaddockHomesBrookvilleNowScraper] Error processing URL {url_idx + 1}: {e}")
                    continue
            
            print(f"[ShaddockHomesBrookvilleNowScraper] Successfully processed {len(all_listings)} total listings across all URLs")
            return all_listings
            
        except Exception as e:
            print(f"[ShaddockHomesBrookvilleNowScraper] Error: {e}")
            return []
