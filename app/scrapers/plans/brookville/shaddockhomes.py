import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class ShaddockHomesBrookvillePlanScraper(BaseScraper):
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
        
        # Handle individual prices like "$394,000"
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

    def parse_lot_size(self, text):
        """Extract lot size from text."""
        if not text:
            return None
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else None

    def extract_plan_data(self, plan_card):
        """Extract data from a plan card div."""
        try:
            # Extract plan name from h4.PlanCard_name > a
            plan_name = None
            plan_name_elem = plan_card.find('h4', class_='PlanCard_name')
            if plan_name_elem:
                plan_link = plan_name_elem.find('a')
                if plan_link:
                    plan_name = plan_link.get_text(strip=True)
            
            # Extract price from div.PlanCard_priceValue
            price = None
            price_elem = plan_card.find('div', class_='PlanCard_priceValue')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self.parse_price(price_text)
            
            # Extract features from ul.PlanCard_contentRow > li.PlanCard_specItem
            beds = None
            baths = None
            sqft = None
            stories = None
            
            feature_list = plan_card.find('ul', class_='PlanCard_contentRow')
            if feature_list:
                features = feature_list.find_all('li', class_='PlanCard_specItem')
                for feature in features:
                    # Get the label to identify what this feature is
                    label_elem = feature.find('span', class_='PlanCard_iconListLabel')
                    value_elem = feature.find('span', class_='PlanCard_iconListValue')
                    
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
                        elif 'Stories' in label_text:
                            stories = self.parse_stories(value_text)
            
            # Extract lot size from div.PlanCard_contentRow.pt-0
            lot_size = None
            lot_size_divs = plan_card.find_all('div', class_=lambda x: x and 'PlanCard_contentRow' in x and 'pt-0' in x if x else False)
            for div in lot_size_divs:
                div_text = div.get_text(strip=True)
                if 'Lot Size:' in div_text:
                    # Extract the number from the <b> tag
                    b_tag = div.find('b')
                    if b_tag:
                        lot_size = b_tag.get_text(strip=True)
                    else:
                        # Fallback to regex if no <b> tag
                        match = re.search(r'Lot Size:\s*(\d+)', div_text)
                        if match:
                            lot_size = match.group(1)
                    break
            
            # Extract stories (default to 1 if not found)
            if not stories:
                stories = "1"
            
            return {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "plan_name": plan_name,
                "beds": beds,
                "baths": baths,
                "lot_size": lot_size
            }
            
        except Exception as e:
            print(f"[ShaddockHomesBrookvillePlanScraper] Error extracting plan data: {e}")
            return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[ShaddockHomesBrookvillePlanScraper] Fetching URLs: {self.URLS}")
            
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
            
            all_plans = []
            seen_plans = set()  # Track plans to prevent duplicates
            
            for url_idx, url in enumerate(self.URLS):
                try:
                    print(f"[ShaddockHomesBrookvillePlanScraper] Processing URL {url_idx + 1}: {url}")
                    
                    # First, get the initial page to see how many plans are available
                    resp = requests.get(url, headers=headers, timeout=15)
                    print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1} response status: {resp.status_code}")
                    
                    if resp.status_code != 200:
                        print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1} request failed with status {resp.status_code}")
                        continue
                    
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    
                    # Look for plan cards with class "PlanCard_wrapper" (these are the plan cards)
                    plan_cards = soup.find_all('div', class_='PlanCard_wrapper')
                    print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}: Found {len(plan_cards)} initial plan cards")
                    
                    # Process the initial plan cards
                    for card_idx, plan_card in enumerate(plan_cards):
                        try:
                            print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Processing plan card")
                            
                            # Extract data from the plan card
                            plan_data = self.extract_plan_data(plan_card)
                            if not plan_data:
                                print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Failed to extract plan data")
                                continue
                            
                            # Check for required fields - require plan_name
                            if not plan_data.get('plan_name'):
                                print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Missing plan name")
                                continue
                            
                            # Check for duplicate plans - use plan_name as unique identifier
                            plan_name = plan_data.get('plan_name')
                            if plan_name in seen_plans:
                                print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Duplicate plan {plan_name}")
                                continue
                            seen_plans.add(plan_name)
                            
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
                                "company": "Shaddock Homes",
                                "community": "Brookville",
                                "type": "plan",
                                "beds": plan_data['beds'],
                                "baths": plan_data['baths'],
                                "lot_size": plan_data['lot_size']
                            }
                            
                            print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: {final_plan_data}")
                            all_plans.append(final_plan_data)
                            
                        except Exception as e:
                            print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}, Card {card_idx + 1}: Error processing card: {e}")
                            continue
                    
                    
                except Exception as e:
                    print(f"[ShaddockHomesBrookvillePlanScraper] Error processing URL {url_idx + 1}: {e}")
                    continue
            
            print(f"[ShaddockHomesBrookvillePlanScraper] Successfully processed {len(all_plans)} total plans across all URLs")
            return all_plans
            
        except Exception as e:
            print(f"[ShaddockHomesBrookvillePlanScraper] Error: {e}")
            return []
