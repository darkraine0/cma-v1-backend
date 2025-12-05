import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict


class FirstTexasHomesMilranyPlanScraper(BaseScraper):
    URL = "https://www.firsttexashomes.com/community/melissa/16555/brookfield/"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract starting price from text."""
        # Try "Starting from $X" pattern first
        match = re.search(r'Starting from \$([\d,]+)', text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
        # Fall back to "$X" pattern
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)\s+Stories?', text, re.IGNORECASE)
        return str(match.group(1)) if match else "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[FirstTexasHomesMilranyPlanScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            response = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[FirstTexasHomesMilranyPlanScraper] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[FirstTexasHomesMilranyPlanScraper] Request failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the Plans tab pane
            plans_tab = soup.find('div', id='plans-border')
            if not plans_tab:
                print(f"[FirstTexasHomesMilranyPlanScraper] No plans-border tab found")
                return []
            
            # Find the Plans grid within the tab
            plans_grid = plans_tab.find('div', id='plans-grid')
            if not plans_grid:
                print(f"[FirstTexasHomesMilranyPlanScraper] No plans-grid found")
                return []
            
            # Find all plan card containers, then get the card divs inside them
            inventory_cards = plans_grid.find_all('div', class_='inventory-card')
            cards = []
            for inv_card in inventory_cards:
                card = inv_card.find('div', class_='card')
                if card:
                    cards.append(card)
            
            print(f"[FirstTexasHomesMilranyPlanScraper] Found {len(cards)} plan cards")
            
            listings = []
            seen_plan_names = set()
            
            for idx, card in enumerate(cards):
                try:
                    # Extract data attributes
                    data_price = card.get('data-price', '0')
                    data_sqft = card.get('data-sqft', '0')
                    data_beds = card.get('data-beds', '')
                    data_baths = card.get('data-baths', '')
                    data_garage = card.get('data-garage', '')
                    data_name = card.get('data-name', '')
                    
                    if not data_price or data_price == '0':
                        print(f"[FirstTexasHomesMilranyPlanScraper] Skipping card {idx+1}: No price")
                        continue
                    
                    price = int(data_price)
                    sqft = int(data_sqft) if data_sqft else None
                    
                    if not sqft:
                        print(f"[FirstTexasHomesMilranyPlanScraper] Skipping card {idx+1}: No square footage")
                        continue
                    
                    # Extract plan name from card body
                    card_body = card.find('div', class_='card-body')
                    plan_name = data_name
                    
                    if card_body:
                        # Plan name is in a div with style containing font-weight:700
                        plan_name_elem = card_body.find('div', style=lambda x: x and 'font-weight:700' in x and 'font-size:1.3em' in x)
                        if plan_name_elem:
                            plan_name = plan_name_elem.get_text(strip=True)
                    
                    if not plan_name:
                        print(f"[FirstTexasHomesMilranyPlanScraper] Skipping card {idx+1}: No plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[FirstTexasHomesMilranyPlanScraper] Skipping card {idx+1}: Duplicate plan '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract starting price from price section
                    if card_body:
                        price_div = card_body.find('div', style=lambda x: x and 'color:#002d62' in x and 'font-size:1.12em' in x)
                        if price_div:
                            price_text = price_div.get_text(strip=True)
                            parsed_price = self.parse_price(price_text)
                            if parsed_price:
                                price = parsed_price
                    
                    # Extract stories from details text
                    stories = "1"
                    if card_body:
                        details_div = card_body.find('div', style=lambda x: x and 'font-size:.94em' in x)
                        if details_div:
                            details_text = details_div.get_text(strip=True)
                            stories = self.parse_stories(details_text)
                    
                    # Extract detail link
                    detail_link = ""
                    link_tag = card.find('a', class_='ftxbluebutton')
                    if link_tag and link_tag.get('href'):
                        href = link_tag['href']
                        if href.startswith('/'):
                            detail_link = f"https://www.firsttexashomes.com{href}"
                        else:
                            detail_link = href
                    
                    # Extract image URL
                    image_url = ""
                    img_tag = card.find('img')
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag['src']
                        if image_url.startswith('//'):
                            image_url = f"https:{image_url}"
                        elif image_url.startswith('/'):
                            image_url = f"https://www.firsttexashomes.com{image_url}"
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "First Texas Homes",
                        "community": "Milrany",
                        "type": "plan",
                        "beds": data_beds if data_beds else "",
                        "baths": data_baths if data_baths else "",
                        "address": "",
                        "original_price": None,
                        "price_cut": "",
                        "status": "",
                        "mls": "",
                        "sub_community": "Brookfield",
                        "image_url": image_url,
                        "detail_link": detail_link,
                        "garage": data_garage if data_garage else ""
                    }
                    
                    print(f"[FirstTexasHomesMilranyPlanScraper] Plan {idx+1}: {plan_name} - ${price:,} - {sqft} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[FirstTexasHomesMilranyPlanScraper] Error processing card {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[FirstTexasHomesMilranyPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[FirstTexasHomesMilranyPlanScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []

