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
        match = re.search(r'(\d+)', text)
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
            # Extract address from the street wrapper
            address = None
            street_wrapper = property_card.find('div', class_='HomeCard_streetWrapper')
            if street_wrapper:
                street_link = street_wrapper.find('a', class_='HomeCard_street')
                if street_link:
                    # Get all text content from the link, excluding the span
                    all_text = street_link.get_text()
                    
                    # Find the subtitle span to extract city/state info
                    subtitle = street_link.find('span', class_='HomeCard_subtitle')
                    if subtitle:
                        subtitle_text = subtitle.get_text(strip=True)
                        # Remove the subtitle text from all_text to get just the street address
                        street_text = all_text.replace(subtitle_text, '').strip()
                        # Clean up any extra whitespace or special characters
                        street_text = re.sub(r'\s+', ' ', street_text).strip()
                        address = f"{street_text}, {subtitle_text}"
                    else:
                        address = all_text.strip()
            
            # Extract price
            price = None
            price_elem = property_card.find('span', class_='HomeCard_price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self.parse_price(price_text)
            
            # Extract status
            status = "Now"
            status_elem = property_card.find('span', class_='HomeCard_status')
            if status_elem:
                status_text = status_elem.get_text(strip=True)
                if status_text:
                    status = status_text
            
            # Extract features from the feature list
            beds = None
            baths = None
            sqft = None
            
            feature_list = property_card.find('ul', class_='list-unstyled')
            if feature_list:
                features = feature_list.find_all('li', class_='HomeCard_listItem')
                for feature in features:
                    feature_text = feature.get_text(strip=True)
                    
                    # Look for bed/bath/sqft information
                    if 'Beds' in feature_text:
                        beds = self.parse_beds(feature_text)
                    elif 'Baths' in feature_text:
                        baths = self.parse_baths(feature_text)
                    elif 'SQ FT' in feature_text:
                        sqft = self.parse_sqft(feature_text)
            
            # Extract plan name from community info
            plan_name = None
            community_list = property_card.find('ul', class_='HomeCard_community')
            if community_list:
                plan_link = community_list.find('a', href=re.compile(r'/plan/'))
                if plan_link:
                    plan_name = plan_link.get_text(strip=True)
            
            # Extract stories (default to 1 if not found)
            stories = "1"
            
            # Check for completion date banner
            completion_banner = property_card.find('div', class_='HomeCard_completionDateBanner')
            if completion_banner:
                completion_text = completion_banner.get_text(strip=True)
                if completion_text:
                    status = completion_text
            
            # Check for sold banner
            sold_banner = property_card.find('div', class_='SoldHome_banner')
            if sold_banner:
                status = "Sold"
            
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
                    
                    # Look for property cards with class "css-mrdg38" (these are the home cards)
                    property_cards = soup.find_all('div', class_='css-mrdg38')
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
