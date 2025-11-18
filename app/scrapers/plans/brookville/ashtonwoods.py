import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class AshtonWoodsBrookvillePlanScraper(BaseScraper):
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

    def extract_plan_data(self, property_card):
        """Extract data from a property card div for floor plans."""
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
            
            price_elem = property_card.find('div', class_='property-card__price')
            if price_elem:
                # Check for price reduction (strike-through + current price)
                strike_price = price_elem.find('span', class_='property-card__price--strike')
                current_price = price_elem.find('span', class_='property-card__price--red')
                
                if strike_price and current_price:
                    # This is a price reduction
                    current_text = current_price.get_text(strip=True)
                    price = self.parse_price(current_text)
                else:
                    # Regular price or price range
                    price_text = price_elem.get_text(strip=True)
                    price = self.parse_price(price_text)
            
            # Extract features from the feature list
            beds = None
            baths = None
            sqft = None
            
            feature_list = property_card.find('ul', class_='property-card__feature-list')
            if feature_list:
                features = feature_list.find_all('li')
                for feature in features:
                    feature_text = feature.get_text(strip=True)
                    
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
            
            # Extract status (for plans, this is typically "Plan")
            status = "Plan"
            
            return {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "plan_name": plan_name,
                "beds": beds,
                "baths": baths,
                "status": status
            }
            
        except Exception as e:
            print(f"[AshtonWoodsBrookvillePlanScraper] Error extracting plan data: {e}")
            return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[AshtonWoodsBrookvillePlanScraper] Fetching URLs: {self.URLS}")
            
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
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            for url_idx, url in enumerate(self.URLS):
                try:
                    print(f"[AshtonWoodsBrookvillePlanScraper] Processing URL {url_idx + 1}: {url}")
                    
                    resp = requests.get(url, headers=headers, timeout=15)
                    print(f"[AshtonWoodsBrookvillePlanScraper] URL {url_idx + 1} response status: {resp.status_code}")
                    
                    if resp.status_code != 200:
                        print(f"[AshtonWoodsBrookvillePlanScraper] URL {url_idx + 1} request failed with status {resp.status_code}")
                        continue
                    
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    
                    # Look for the home-plans panel
                    home_plans_panel = soup.find('li', id='panel-home-plans')
                    if not home_plans_panel:
                        print(f"[AshtonWoodsBrookvillePlanScraper] URL {url_idx + 1}: No home-plans panel found")
                        continue
                    
                    # Find all property cards in the home-plans panel
                    property_cards = home_plans_panel.find_all('div', class_='property-card')
                    print(f"[AshtonWoodsBrookvillePlanScraper] URL {url_idx + 1}: Found {len(property_cards)} property cards")
                    
                    for card_idx, property_card in enumerate(property_cards):
                        try:
                            print(f"[AshtonWoodsBrookvillePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Processing property card")
                            
                            # Extract data from the property card
                            plan_data = self.extract_plan_data(property_card)
                            if not plan_data:
                                print(f"[AshtonWoodsBrookvillePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Failed to extract plan data")
                                continue
                            
                            # Check for required fields - only require plan_name, price is optional
                            if not plan_data.get('plan_name'):
                                print(f"[AshtonWoodsBrookvillePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Missing plan name")
                                continue
                            
                            # Check for duplicate plan names
                            plan_name = plan_data.get('plan_name')
                            if plan_name in seen_plan_names:
                                print(f"[AshtonWoodsBrookvillePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Duplicate plan name {plan_name}")
                                continue
                            seen_plan_names.add(plan_name)
                            
                            # Calculate price per square foot if both price and sqft are available
                            price_per_sqft = None
                            if plan_data.get('price') and plan_data.get('sqft'):
                                price_per_sqft = round(plan_data['price'] / plan_data['sqft'], 2) if plan_data['sqft'] > 0 else None
                            
                            # Create the final listing data
                            listing_data = {
                                "price": plan_data['price'],
                                "sqft": plan_data['sqft'],
                                "stories": plan_data['stories'],
                                "price_per_sqft": price_per_sqft,
                                "plan_name": plan_data['plan_name'],
                                "company": "AshtonWoods Homes",
                                "community": "Brookville",
                                "type": "plan",
                                "beds": plan_data['beds'],
                                "baths": plan_data['baths'],
                                "status": plan_data['status']
                            }
                            
                            print(f"[AshtonWoodsBrookvillePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: {listing_data}")
                            all_listings.append(listing_data)
                            
                        except Exception as e:
                            print(f"[AshtonWoodsBrookvillePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Error processing card: {e}")
                            continue
                    
                except Exception as e:
                    print(f"[AshtonWoodsBrookvillePlanScraper] Error processing URL {url_idx + 1}: {e}")
                    continue
            
            print(f"[AshtonWoodsBrookvillePlanScraper] Successfully processed {len(all_listings)} total listings across all URLs")
            return all_listings
            
        except Exception as e:
            print(f"[AshtonWoodsBrookvillePlanScraper] Error: {e}")
            return []
