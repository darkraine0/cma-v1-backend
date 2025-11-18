#!/usr/bin/env python3
"""
William Ryan Homes Creekside Floor Plans Scraper
"""

import requests
from bs4 import BeautifulSoup
import re
from app.scrapers.base import BaseScraper

class WilliamRyanHomesCreeksidePlanScraper(BaseScraper):
    URL = "https://www.williamryanhomes.com/dfw/royse-city/creekside"
    
    def parse_price(self, text):
        """Parse price from text like '$268,990'"""
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
    
    def extract_plan_data(self, plan_card):
        """Extract data from a floor plan card"""
        try:
            # Plan name - look for the font-serif span with text-[28px] class
            # Use a more flexible selector since the element has additional classes
            plan_name_elem = plan_card.find('span', class_='font-serif')
            if not plan_name_elem:
                # Fallback: try to find any span with font-serif class
                plan_name_elem = plan_card.find('span', class_=lambda x: x and 'font-serif' in x)
            
            if not plan_name_elem:
                return None
            
            plan_name = plan_name_elem.get_text(strip=True)
            
            if not plan_name:
                return None
            
            # Description - look for the first text-blue-500 span (description)
            description = None
            description_elem = plan_card.find('span', class_='text-blue-500')
            if description_elem:
                description = description_elem.get_text(strip=True)
                # Clean up description - remove extra whitespace and newlines
                if description:
                    description = ' '.join(description.split())
            
            # Price - look for the font-bold span in the price section
            price_elem = plan_card.find('div', class_='flex gap-2')
            price = None
            if price_elem:
                price_span = price_elem.find('span', class_='font-bold')
                if price_span:
                    price = self.parse_price(price_span.get_text(strip=True))
            
            # Features grid - look for the 4-column grid with py-4 class (this is the actual features grid)
            features_grid = plan_card.find('div', class_='grid grid-cols-4 py-4')
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
            
            # If the above method didn't work, try an alternative approach
            if not any([beds, baths, garages, sqft]):
                # Look for any grid with 4 columns as fallback
                alt_features_grid = plan_card.find('div', class_=lambda x: x and 'grid' in x and 'grid-cols-4' in x)
                if alt_features_grid:
                    # Find all direct div children that contain the feature data
                    feature_divs = alt_features_grid.find_all('div', class_='flex', recursive=False)
                    
                    for feature_div in feature_divs:
                        # Each feature div should contain a flex-col with value and label
                        flex_col = feature_div.find('div', class_='flex w-full flex-col items-center')
                        if flex_col:
                            spans = flex_col.find_all('span')
                            if len(spans) >= 2:
                                value = spans[0].get_text(strip=True)
                                label = spans[1].get_text(strip=True).lower()
                                
                                if 'bed' in label:
                                    beds = self.parse_beds_baths_garages(value)
                                elif 'bath' in label:
                                    baths = self.parse_beds_baths_garages(value)
                                elif 'garage' in label:
                                    garages = self.parse_beds_baths_garages(value)
                                elif 'sq' in label or 'ft' in label:
                                    sqft = self.parse_sqft(value)
            
            # Plan number - extract from the View Floorplan link
            plan_number = None
            view_link = plan_card.find('a', href=re.compile(r'/floor-plans/\d+'))
            if view_link:
                href = view_link.get('href', '')
                match = re.search(r'/floor-plans/(\d+)', href)
                if match:
                    plan_number = match.group(1)
            
            # Image URL - extract from the img tag
            image_url = None
            img_elem = plan_card.find('img')
            if img_elem and img_elem.get('src'):
                image_url = img_elem.get('src')
                # Convert relative URLs to absolute
                if image_url.startswith('/'):
                    image_url = f"https://www.williamryanhomes.com{image_url}"
            
            return {
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
            print(f"[WilliamRyanHomesCreeksidePlanScraper] Error extracting plan data: {e}")
            return None
    
    def fetch_plans(self):
        """Fetch floor plans from William Ryan Homes Creekside"""
        try:
            print(f"[WilliamRyanHomesCreeksidePlanScraper] Fetching URL: {self.URL}")
            
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
                print(f"[WilliamRyanHomesCreeksidePlanScraper] Request failed with status {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.content, 'html.parser')

            # Look for the floor plans container
            floor_plans_container = soup.find('div', id='floorPlansListContainer')
            if not floor_plans_container:
                print("[WilliamRyanHomesCreeksidePlanScraper] Could not find floor plans container")
                return []

            # Find all floor plan cards
            plan_cards = floor_plans_container.find_all('div', class_='duration-250')
            print(f"[WilliamRyanHomesCreeksidePlanScraper] Found {len(plan_cards)} floor plan cards")
            
            if not plan_cards:
                print("[WilliamRyanHomesCreeksidePlanScraper] No floor plan cards found")
                return []
            
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates

            for card_idx, plan_card in enumerate(plan_cards):
                try:
                    print(f"[WilliamRyanHomesCreeksidePlanScraper] Processing card {card_idx + 1}")

                    # Extract data from the plan card
                    plan_data = self.extract_plan_data(plan_card)
                    if not plan_data:
                        print(f"[WilliamRyanHomesCreeksidePlanScraper] Card {card_idx + 1}: Failed to extract plan data")
                        continue

                    # Check for required fields - require plan name
                    if not plan_data.get('plan_name'):
                        print(f"[WilliamRyanHomesCreeksidePlanScraper] Card {card_idx + 1}: Missing plan name")
                        continue

                    # Check for duplicate plan names
                    plan_name = plan_data.get('plan_name')
                    if plan_name in seen_plan_names:
                        print(f"[WilliamRyanHomesCreeksidePlanScraper] Card {card_idx + 1}: Duplicate plan name {plan_name}")
                        continue
                    seen_plan_names.add(plan_name)

                    # Calculate price per square foot if both price and sqft are available
                    price_per_sqft = None
                    if plan_data.get('price') and plan_data.get('sqft'):
                        price_per_sqft = round(plan_data['price'] / plan_data['sqft'], 2) if plan_data['sqft'] > 0 else None

                    # Create the final listing data
                    final_listing_data = {
                        "price": plan_data['price'],
                        "sqft": plan_data['sqft'],
                        "stories": "1",  # Default to 1 story for single-family homes
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_data['plan_name'],
                        "floor_plan_name": plan_data['plan_name'],
                        "company": "William Ryan Homes",
                        "community": "Creekside",
                        "type": "plan",
                        "beds": plan_data['beds'],
                        "baths": plan_data['baths'],
                        "status": "Available",
                        "address": None,  # Floor plans don't have addresses
                        "plan_number": plan_data['plan_number'],
                        "garages": plan_data['garages'],
                        "description": plan_data.get('description'),
                        "image_url": plan_data.get('image_url')
                    }

                    print(f"[WilliamRyanHomesCreeksidePlanScraper] Card {card_idx + 1}: {final_listing_data}")
                    listings.append(final_listing_data)

                except Exception as e:
                    print(f"[WilliamRyanHomesCreeksidePlanScraper] Error processing card {card_idx + 1}: {e}")
                    continue

            print(f"[WilliamRyanHomesCreeksidePlanScraper] Successfully processed {len(listings)} total listings")
            return listings

        except Exception as e:
            print(f"[WilliamRyanHomesCreeksidePlanScraper] Error in fetch_plans: {e}")
            return []
