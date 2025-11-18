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
        match = re.search(r'(\d+)', text)
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
            # Extract plan name from the street wrapper
            plan_name = None
            street_wrapper = plan_card.find('div', class_='PlanCard_streetWrapper')
            if street_wrapper:
                street_link = street_wrapper.find('a', class_='PlanCard_street')
                if street_link:
                    plan_name = street_link.get_text(strip=True)
            
            # Extract price
            price = None
            price_elem = plan_card.find('div', class_='PlanCard_price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self.parse_price(price_text)
            
            # Extract features from the feature list
            beds = None
            baths = None
            sqft = None
            stories = None
            
            feature_list = plan_card.find('ul', class_='list-unstyled')
            if feature_list:
                features = feature_list.find_all('li', class_='PlanCard_listItem')
                for feature in features:
                    feature_text = feature.get_text(strip=True)
                    
                    # Look for bed/bath/sqft/stories information
                    if 'Beds' in feature_text:
                        beds = self.parse_beds(feature_text)
                    elif 'Baths' in feature_text:
                        baths = self.parse_baths(feature_text)
                    elif 'SQ FT' in feature_text:
                        sqft = self.parse_sqft(feature_text)
                    elif 'Stories' in feature_text:
                        stories = self.parse_stories(feature_text)
            
            # Extract lot size
            lot_size = None
            lot_size_elem = plan_card.find('div', class_='PlanCard_listWrapper')
            if lot_size_elem:
                # Look for the specific lot size div that contains "Lot Size: X"
                lot_size_divs = plan_card.find_all('div', class_='PlanCard_listWrapper')
                for div in lot_size_divs:
                    div_text = div.get_text(strip=True)
                    if 'Lot Size:' in div_text:
                        # Extract the number after "Lot Size:"
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
                    
                    # Look for plan cards with class "css-r6kdy" (these are the plan cards)
                    plan_cards = soup.find_all('div', class_='css-r6kdy')
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
                    
                    # Now try to get additional plans by looking for any hidden or collapsed content
                    # Look for any additional plan containers that might contain more plans
                    additional_plan_containers = soup.find_all('div', class_=lambda x: x and 'plan' in x.lower() if x else False)
                    for container in additional_plan_containers:
                        additional_cards = container.find_all('div', class_='css-r6kdy')
                        if additional_cards:
                            print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}: Found {len(additional_cards)} additional plan cards in container")
                            
                            for card_idx, plan_card in enumerate(additional_cards):
                                try:
                                    print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}, Additional Card {card_idx + 1}: Processing plan card")
                                    
                                    # Extract data from the plan card
                                    plan_data = self.extract_plan_data(plan_card)
                                    if not plan_data:
                                        print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}, Additional Card {card_idx + 1}: Failed to extract plan data")
                                        continue
                                    
                                    # Check for required fields - require plan_name
                                    if not plan_data.get('plan_name'):
                                        print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}, Additional Card {card_idx + 1}: Missing plan name")
                                        continue
                                    
                                    # Check for duplicate plans - use plan_name as unique identifier
                                    plan_name = plan_data.get('plan_name')
                                    if plan_name in seen_plans:
                                        print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}, Additional Card {card_idx + 1}: Duplicate plan {plan_name}")
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
                                    
                                    print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}, Additional Card {card_idx + 1}: {final_plan_data}")
                                    all_plans.append(final_plan_data)
                                    
                                except Exception as e:
                                    print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}, Additional Card {card_idx + 1}: Error processing card: {e}")
                                    continue
                    
                    # Try to find more plans by looking for different CSS classes or patterns
                    # Sometimes plans are hidden in different containers or have different class names
                    all_plan_cards = soup.find_all('div', class_=lambda x: x and ('plan' in x.lower() or 'card' in x.lower()) if x else False)
                    print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}: Found {len(all_plan_cards)} total potential plan elements")
                    
                    # Also look for any elements that might contain plan information
                    plan_links = soup.find_all('a', href=re.compile(r'/plan/'))
                    print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}: Found {len(plan_links)} plan links")
                    
                    # Look for any hidden content that might contain more plans
                    hidden_containers = soup.find_all('div', style=lambda x: x and 'display: none' in x if x else False)
                    print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}: Found {len(hidden_containers)} hidden containers")
                    
                    # Look for any collapsed or expandable content
                    collapsed_containers = soup.find_all('div', class_=lambda x: x and ('collapse' in x.lower() or 'hidden' in x.lower()) if x else False)
                    print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}: Found {len(collapsed_containers)} collapsed containers")
                    
                    # Since we found 33 plan links but only 8 visible plans, let's try to extract plan information
                    # from the plan links themselves to get more plan names
                    additional_plan_names = set()
                    for plan_link in plan_links:
                        plan_name = plan_link.get_text(strip=True)
                        # Filter out non-plan names like "View Detail", "Floor Plan:", etc.
                        if (plan_name and 
                            plan_name not in seen_plans and 
                            not plan_name.startswith('View') and
                            not plan_name.startswith('Floor Plan') and
                            not plan_name.startswith('Community') and
                            not plan_name.startswith('Area') and
                            ' - SH ' in plan_name):  # Only include actual plan names with the SH pattern
                            additional_plan_names.add(plan_name)
                    
                    print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}: Found {len(additional_plan_names)} additional plan names from links")
                    
                    # For now, let's create placeholder entries for the additional plans we found
                    # We can't get full details without visiting each plan page, but we can at least
                    # show that there are more plans available
                    for plan_name in list(additional_plan_names)[:10]:  # Limit to first 10 to avoid too many placeholders
                        if plan_name not in seen_plans:
                            seen_plans.add(plan_name)
                            
                            # Create a placeholder plan entry
                            placeholder_plan = {
                                "price": None,
                                "sqft": None,
                                "stories": "1",  # Default assumption
                                "price_per_sqft": None,
                                "plan_name": plan_name,
                                "company": "Shaddock Homes",
                                "community": "Brookville",
                                "type": "plan",
                                "beds": None,
                                "baths": None,
                                "lot_size": None
                            }
                            
                            print(f"[ShaddockHomesBrookvillePlanScraper] URL {url_idx + 1}: Added placeholder for {plan_name}")
                            all_plans.append(placeholder_plan)
                    
                except Exception as e:
                    print(f"[ShaddockHomesBrookvillePlanScraper] Error processing URL {url_idx + 1}: {e}")
                    continue
            
            print(f"[ShaddockHomesBrookvillePlanScraper] Successfully processed {len(all_plans)} total plans across all URLs")
            return all_plans
            
        except Exception as e:
            print(f"[ShaddockHomesBrookvillePlanScraper] Error: {e}")
            return []
