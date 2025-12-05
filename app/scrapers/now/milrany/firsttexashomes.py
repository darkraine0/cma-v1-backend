import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict


class FirstTexasHomesMilranyNowScraper(BaseScraper):
    URL = "https://www.firsttexashomes.com/community/melissa/16555/brookfield/"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text."""
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
            print(f"[FirstTexasHomesMilranyNowScraper] Fetching URL: {self.URL}")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            response = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[FirstTexasHomesMilranyNowScraper] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[FirstTexasHomesMilranyNowScraper] Request failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the Quick Move-In Homes tab pane (might be in inactive tab)
            qmi_tab = soup.find('div', id='qmi-border')
            if not qmi_tab:
                print(f"[FirstTexasHomesMilranyNowScraper] No qmi-border tab found")
                return []
            
            # Find the Quick Move-In Homes grid within the tab
            qmi_grid = qmi_tab.find('div', id='qmi-grid')
            if not qmi_grid:
                print(f"[FirstTexasHomesMilranyNowScraper] No qmi-grid found")
                return []
            
            # Find all inventory card containers, then get the card divs inside them
            inventory_cards = qmi_grid.find_all('div', class_='inventory-card')
            cards = []
            for inv_card in inventory_cards:
                card = inv_card.find('div', class_='card')
                if card:
                    cards.append(card)
            
            print(f"[FirstTexasHomesMilranyNowScraper] Found {len(cards)} inventory cards")
            
            listings = []
            seen_addresses = set()
            
            for idx, card in enumerate(cards):
                try:
                    # Check if sold
                    data_sold = card.get('data-sold', '0')
                    if data_sold == '1':
                        print(f"[FirstTexasHomesMilranyNowScraper] Skipping card {idx+1}: Sold")
                        continue
                    
                    # Extract data attributes
                    data_price = card.get('data-price', '0')
                    data_sqft = card.get('data-sqft', '0')
                    data_beds = card.get('data-beds', '')
                    data_baths = card.get('data-baths', '')
                    data_garage = card.get('data-garage', '')
                    data_name = card.get('data-name', '')
                    
                    if not data_price or data_price == '0':
                        print(f"[FirstTexasHomesMilranyNowScraper] Skipping card {idx+1}: No price")
                        continue
                    
                    price = int(data_price)
                    sqft = int(data_sqft) if data_sqft else None
                    
                    if not sqft:
                        print(f"[FirstTexasHomesMilranyNowScraper] Skipping card {idx+1}: No square footage")
                        continue
                    
                    # Extract plan name from card body
                    card_body = card.find('div', class_='card-body')
                    plan_name = data_name
                    address = ""
                    
                    if card_body:
                        # Plan name is in a div with style containing font-weight:700
                        plan_name_elem = card_body.find('div', style=lambda x: x and 'font-weight:700' in x and 'font-size:1.3em' in x)
                        if plan_name_elem:
                            plan_name = plan_name_elem.get_text(strip=True)
                        
                        # Address is in divs with style containing color:#444
                        address_divs = card_body.find_all('div', style=lambda x: x and 'color:#444' in x and 'font-size:1.06em' in x)
                        if len(address_divs) >= 2:
                            street = address_divs[0].get_text(strip=True)
                            city_state = address_divs[1].get_text(strip=True)
                            address = f"{street}, {city_state}"
                            seen_key = address.lower()
                            if seen_key in seen_addresses:
                                print(f"[FirstTexasHomesMilranyNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                                continue
                            seen_addresses.add(seen_key)
                    
                    # Extract original price and current price from price section
                    original_price = None
                    price_cut = ""
                    
                    price_section = card_body.find('div', style=lambda x: x and 'margin-bottom:6px' in x)
                    if price_section:
                        was_span = price_section.find('span', style=lambda x: x and 'text-decoration:line-through' in x)
                        if was_span:
                            was_text = was_span.get_text(strip=True)
                            original_price = self.parse_price(was_text)
                            if original_price and price:
                                price_cut = f"${original_price - price:,}"
                        
                        now_span = price_section.find('span', style=lambda x: x and 'color:#002d62' in x and 'font-size:1.15em' in x)
                        if now_span:
                            now_text = now_span.get_text(strip=True)
                            parsed_now = self.parse_price(now_text)
                            if parsed_now:
                                price = parsed_now
                    
                    # Extract status
                    status = "Available"
                    status_ribbon = card.find('div', class_='status-ribbon')
                    if status_ribbon:
                        status = status_ribbon.get('data-status', 'Available')
                    
                    # Extract stories from details text
                    stories = "1"
                    details_text = ""
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
                        "plan_name": plan_name or address,
                        "company": "First Texas Homes",
                        "community": "Milrany",
                        "type": "now",
                        "beds": data_beds if data_beds else "",
                        "baths": data_baths if data_baths else "",
                        "address": address,
                        "original_price": original_price,
                        "price_cut": price_cut,
                        "status": status,
                        "mls": "",
                        "sub_community": "Brookfield",
                        "image_url": image_url,
                        "detail_link": detail_link,
                        "garage": data_garage if data_garage else ""
                    }
                    
                    print(f"[FirstTexasHomesMilranyNowScraper] Home {idx+1}: {plan_name} - {address} - ${price:,} - {sqft} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[FirstTexasHomesMilranyNowScraper] Error processing card {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[FirstTexasHomesMilranyNowScraper] Successfully processed {len(listings)} homes")
            return listings
            
        except Exception as e:
            print(f"[FirstTexasHomesMilranyNowScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []

