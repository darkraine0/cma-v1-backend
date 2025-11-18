#!/usr/bin/env python3
"""
William Ryan Homes Creekside Inventory Homes Scraper
"""

import requests
from bs4 import BeautifulSoup
import re
from app.scrapers.base import BaseScraper

class WilliamRyanHomesCreeksideNowScraper(BaseScraper):
    URL = "https://www.williamryanhomes.com/dfw/royse-city/creekside"
    
    def parse_price(self, text):
        """Parse price from text like '$269,990'"""
        if not text:
            return None
        
        # Remove any non-numeric characters except commas and dots
        price_text = re.sub(r'[^\d,.]', '', text)
        
        try:
            # Remove commas and convert to integer
            price = int(price_text.replace(',', ''))
            return price
        except (ValueError, AttributeError):
            return None
    
    def parse_sqft(self, text):
        """Parse square footage from text like '1,500'"""
        if not text:
            return None
        
        # Remove any non-numeric characters except commas and dots
        sqft_text = re.sub(r'[^\d,.]', '', text)
        
        try:
            # Remove commas and convert to integer
            sqft = int(sqft_text.replace(',', ''))
            return sqft
        except (ValueError, AttributeError):
            return None
    
    def parse_beds_baths_garages(self, text):
        """Parse beds, baths, or garages from text"""
        if not text:
            return None
        
        # Extract the first number from the text
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        if match:
            try:
                value = float(match.group(1))
                return int(value) if value.is_integer() else value
            except (ValueError, AttributeError):
                return None
        return None
    
    def extract_property_data(self, property_card):
        """Extract data from an inventory home card"""
        try:
            # Address - look for the font-serif span (this contains the address for inventory homes)
            # Use a more flexible selector since the element has additional classes
            address_elem = property_card.find('span', class_='font-serif')
            if not address_elem:
                # Fallback: try to find any span with font-serif class
                address_elem = property_card.find('span', class_=lambda x: x and 'font-serif' in x)
            
            if not address_elem:
                return None
            
            address = address_elem.get_text(strip=True)
            
            # Description - look for the first text-blue-500 span (description)
            description = None
            description_elem = property_card.find('span', class_='text-blue-500')
            if description_elem:
                description = description_elem.get_text(strip=True)
                # Clean up description - remove extra whitespace and newlines
                if description:
                    description = ' '.join(description.split())
            
            # Price - look for the font-bold span in the price section
            price_elem = property_card.find('div', class_='flex gap-2')
            price = None
            if price_elem:
                price_span = price_elem.find('span', class_='font-bold')
                if price_span:
                    price = self.parse_price(price_span.get_text(strip=True))
            
            # Features grid - look for the 4-column grid with py-4 class
            features_grid = property_card.find('div', class_='grid grid-cols-4 py-4')
            beds = baths = garages = sqft = None
            
            if features_grid:
                # The features are in flex containers within the grid
                feature_containers = features_grid.find_all('div', class_='flex')
                
                for container in feature_containers:
                    # Look for the flex-col container that holds the value and label
                    flex_col = container.find('div', class_='flex w-full flex-col items-center')
                    if flex_col:
                        # Find all spans in the flex-col container
                        spans = flex_col.find_all('span')
                        if len(spans) >= 2:
                            # First span should be the value (font-bold), second should be the label
                            value_elem = spans[0]  # First span
                            label_elem = spans[1]  # Second span
                            
                            value = value_elem.get_text(strip=True)
                            label = label_elem.get_text(strip=True).lower()
                            
                            if 'bed' in label:
                                beds = self.parse_beds_baths_garages(value)
                            elif 'bath' in label:
                                baths = self.parse_beds_baths_garages(value)
                            elif 'garage' in label:
                                garages = self.parse_beds_baths_garages(value)
                            elif 'sq' in label or 'ft' in label:
                                sqft = self.parse_sqft(value)
            
            # Plan number - extract from the View Home link
            plan_number = None
            view_link = property_card.find('a', href=re.compile(r'/quick-move-ins/\d+'))
            if view_link:
                href = view_link.get('href', '')
                match = re.search(r'/quick-move-ins/(\d+)', href)
                if match:
                    plan_number = match.group(1)
            
            # Image URL - extract from the img tag
            image_url = None
            img_elem = property_card.find('img')
            if img_elem and img_elem.get('src'):
                image_url = img_elem.get('src')
                # Convert relative URLs to absolute
                if image_url.startswith('/'):
                    image_url = f"https://www.williamryanhomes.com{image_url}"
            
            # Extract plan name from address (use first part as plan name)
            plan_name = address.split(',')[0] if address else None
            
            return {
                'address': address,
                'plan_name': plan_name,
                'description': description,
                'price': price,
                'sqft': sqft,
                'beds': beds,
                'baths': baths,
                'garages': garages,
                'plan_number': plan_number,
                'image_url': image_url
            }
            
        except Exception as e:
            print(f"[WilliamRyanHomesCreeksideNowScraper] Error extracting property data: {e}")
            return None
    
    def fetch_plans(self):
        """Fetch inventory homes from William Ryan Homes Creekside"""
        try:
            print(f"[WilliamRyanHomesCreeksideNowScraper] Fetching URL: {self.URL}")
            
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
            
            if resp.status_code != 200:
                print(f"[WilliamRyanHomesCreeksideNowScraper] Request failed with status {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.content, 'html.parser')

            # Look for the quick move-ins container
            quick_move_ins_container = soup.find('div', id='quickMoveInsListContainer')
            if not quick_move_ins_container:
                print("[WilliamRyanHomesCreeksideNowScraper] Could not find quick move-ins container")
                return []

            # Find all inventory home cards
            property_cards = quick_move_ins_container.find_all('div', class_='duration-250')
            print(f"[WilliamRyanHomesCreeksideNowScraper] Found {len(property_cards)} inventory home cards")
            
            if not property_cards:
                print("[WilliamRyanHomesCreeksideNowScraper] No inventory home cards found")
                return []
            
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates

            for card_idx, property_card in enumerate(property_cards):
                try:
                    print(f"[WilliamRyanHomesCreeksideNowScraper] Processing card {card_idx + 1}")

                    # Extract data from the property card
                    property_data = self.extract_property_data(property_card)
                    if not property_data:
                        print(f"[WilliamRyanHomesCreeksideNowScraper] Card {card_idx + 1}: Failed to extract property data")
                        continue

                    # Check for required fields - require address
                    if not property_data.get('address'):
                        print(f"[WilliamRyanHomesCreeksideNowScraper] Card {card_idx + 1}: Missing address")
                        continue

                    # Check for duplicate addresses
                    address = property_data.get('address')
                    if address in seen_addresses:
                        print(f"[WilliamRyanHomesCreeksideNowScraper] Card {card_idx + 1}: Duplicate address {address}")
                        continue
                    seen_addresses.add(address)

                    # Calculate price per square foot if both price and sqft are available
                    price_per_sqft = None
                    if property_data.get('price') and property_data.get('sqft'):
                        price_per_sqft = round(property_data['price'] / property_data['sqft'], 2) if property_data['sqft'] > 0 else None

                    # Create the final listing data
                    final_listing_data = {
                        "price": property_data['price'],
                        "sqft": property_data['sqft'],
                        "stories": "1",  # Default to 1 story for single-family homes
                        "price_per_sqft": price_per_sqft,
                        "plan_name": property_data['address'],  # Use address as plan_name for inventory
                        "floor_plan_name": property_data['plan_name'],  # Store extracted plan name
                        "company": "William Ryan Homes",
                        "community": "Creekside",
                        "type": "now",
                        "beds": property_data['beds'],
                        "baths": property_data['baths'],
                        "status": "Available",
                        "address": property_data['address'],
                        "plan_number": property_data['plan_number'],
                        "garages": property_data['garages'],
                        "description": property_data.get('description'),
                        "image_url": property_data.get('image_url')
                    }

                    print(f"[WilliamRyanHomesCreeksideNowScraper] Card {card_idx + 1}: {final_listing_data}")
                    listings.append(final_listing_data)

                except Exception as e:
                    print(f"[WilliamRyanHomesCreeksideNowScraper] Error processing card {card_idx + 1}: {e}")
                    continue

            print(f"[WilliamRyanHomesCreeksideNowScraper] Successfully processed {len(listings)} total listings")
            return listings

        except Exception as e:
            print(f"[WilliamRyanHomesCreeksideNowScraper] Error in fetch_plans: {e}")
            return []
