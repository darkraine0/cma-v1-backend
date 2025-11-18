import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class AshtonWoodsBrookvilleNowScraper(BaseScraper):
    URLS = [
        "https://www.ashtonwoods.com/dallas/devonshire?comm=DAL|MCDVS",
        "https://www.ashtonwoods.com/dallas/gateway-parks?comm=DAL|D287"
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
        
        # Handle "K" suffix (thousands)
        if 'K' in text:
            match = re.search(r'\$([\d,]+)K', text)
            if match:
                price_str = match.group(1)
                return int(price_str.replace(",", "")) * 1000
        
        # Handle price ranges like "From $301K—$389K" (note: the dash is actually an em dash)
        if 'From' in text and ('—' in text or 'â€"' in text):
            # Extract the first price (lower bound)
            match = re.search(r'From\s*\$([\d,]+)K', text)
            if match:
                price_str = match.group(1)
                return int(price_str.replace(",", "")) * 1000
        
        # Handle individual prices like "$373,000"
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
            # Extract plan name from title
            title_elem = property_card.find('h4', class_='property-card__title')
            plan_name = None
            if title_elem:
                title_link = title_elem.find('a')
                if title_link:
                    plan_name = title_link.get_text(strip=True)
            
            # Extract price information
            price = None
            price_reduction = None
            
            price_elem = property_card.find('div', class_='property-card__price')
            if price_elem:
                # Check for price reduction (strike-through + current price)
                strike_price = price_elem.find('span', class_='property-card__price--strike')
                current_price = price_elem.find('span', class_='property-card__price--red')
                
                if strike_price and current_price:
                    # This is a price reduction
                    strike_text = strike_price.get_text(strip=True)
                    current_text = current_price.get_text(strip=True)
                    
                    price = self.parse_price(current_text)
                    strike_price_val = self.parse_price(strike_text)
                    
                    if price and strike_price_val:
                        price_reduction = strike_price_val - price
                else:
                    # Regular price or price range
                    price_text = price_elem.get_text(strip=True)
                    price = self.parse_price(price_text)
            
            # Extract features from the feature list
            beds = None
            baths = None
            sqft = None
            address = None
            
            feature_list = property_card.find('ul', class_='property-card__feature-list')
            if feature_list:
                features = feature_list.find_all('li')
                for feature in features:
                    feature_text = feature.get_text(strip=True)
                    
                    # Look for location (usually contains city, state)
                    if 'TX' in feature_text or 'Forney' in feature_text:
                        address = feature_text
                    
                    # Look for bed/bath information
                    if 'bed' in feature_text.lower():
                        beds = self.parse_beds(feature_text)
                    elif 'bath' in feature_text.lower():
                        baths = self.parse_baths(feature_text)
                    
                    # Look for sqft information
                    if 'sq' in feature_text.lower() and 'ft' in feature_text.lower():
                        sqft = self.parse_sqft(feature_text)
            
            # Extract stories (default to 1 if not found)
            stories = "1"
            
            # Extract status
            status = "Now"
            
            # Check for price reduction flag
            price_reduction_flag = property_card.find('span', class_='image-content__flag')
            if price_reduction_flag and 'Price Reduced' in price_reduction_flag.get_text():
                status = "Price Reduced"
            
            return {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "plan_name": plan_name,
                "beds": beds,
                "baths": baths,
                "status": status,
                "address": address,
                "price_reduction": price_reduction
            }
            
        except Exception as e:
            print(f"[AshtonWoodsBrookvilleNowScraper] Error extracting property data: {e}")
            return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[AshtonWoodsBrookvilleNowScraper] Fetching URLs: {self.URLS}")
            
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
                    print(f"[AshtonWoodsBrookvilleNowScraper] Processing URL {url_idx + 1}: {url}")
                    
                    resp = requests.get(url, headers=headers, timeout=15)
                    print(f"[AshtonWoodsBrookvilleNowScraper] URL {url_idx + 1} response status: {resp.status_code}")
                    
                    if resp.status_code != 200:
                        print(f"[AshtonWoodsBrookvilleNowScraper] URL {url_idx + 1} request failed with status {resp.status_code}")
                        continue
                    
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    
                    # Look for property cards with "Available" text in the tabs__series container
                    tabs_series = soup.find('div', class_='tabs__series')
                    if not tabs_series:
                        print(f"[AshtonWoodsBrookvilleNowScraper] URL {url_idx + 1}: No tabs__series found")
                        continue
                    
                    # Find all property cards in the tabs series
                    property_cards = tabs_series.find_all('div', class_='property-card')
                    print(f"[AshtonWoodsBrookvilleNowScraper] URL {url_idx + 1}: Found {len(property_cards)} property cards")
                    
                    for card_idx, property_card in enumerate(property_cards):
                        try:
                            print(f"[AshtonWoodsBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Processing property card")
                            
                            # Check if this is an "Available" property by looking for "Available" text
                            body_title = property_card.find('div', class_='property-card__body-title')
                            if not body_title or 'Available' not in body_title.get_text():
                                print(f"[AshtonWoodsBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Not an 'Available' property, skipping")
                                continue
                            
                            # Extract data from the property card
                            property_data = self.extract_property_data(property_card)
                            if not property_data:
                                print(f"[AshtonWoodsBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Failed to extract property data")
                                continue
                            
                            # Check for required fields - only require plan_name, price is optional
                            if not property_data.get('plan_name'):
                                print(f"[AshtonWoodsBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Missing plan name")
                                continue
                            
                            # Check for duplicate properties - use plan_name + address as unique identifier
                            address = property_data.get('address')
                            plan_name = property_data.get('plan_name')
                            unique_id = f"{plan_name}_{address}" if address else plan_name
                            if unique_id in seen_properties:
                                print(f"[AshtonWoodsBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Duplicate property {unique_id}")
                                continue
                            seen_properties.add(unique_id)
                            
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
                                "company": "AshtonWoods Homes",
                                "community": "Brookville",
                                "type": "now",
                                "beds": property_data['beds'],
                                "baths": property_data['baths'],
                                "status": property_data['status'],
                                "address": address,
                                "price_reduction": property_data.get('price_reduction')
                            }
                            
                            print(f"[AshtonWoodsBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: {listing_data}")
                            all_listings.append(listing_data)
                            
                        except Exception as e:
                            print(f"[AshtonWoodsBrookvilleNowScraper] URL {url_idx + 1}, Card {card_idx + 1}: Error processing card: {e}")
                            continue
                    
                except Exception as e:
                    print(f"[AshtonWoodsBrookvilleNowScraper] Error processing URL {url_idx + 1}: {e}")
                    continue
            
            print(f"[AshtonWoodsBrookvilleNowScraper] Successfully processed {len(all_listings)} total listings across all URLs")
            return all_listings
            
        except Exception as e:
            print(f"[AshtonWoodsBrookvilleNowScraper] Error: {e}")
            return []
