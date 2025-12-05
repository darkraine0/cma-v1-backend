import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ...base import BaseScraper
from typing import List, Dict

class WilliamRyanHomesCambridgeNowScraper(BaseScraper):
    URL = "https://www.williamryanhomes.com/dfw/celina/ten-mile-creek"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "3" and "3.5" formats
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_garages(self, text):
        """Extract number of garages from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[WilliamRyanHomesCambridgeNowScraper] Fetching URL: {self.URL}")
            
            # Setup Chrome options for headless browsing
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
            
            # Initialize Chrome driver
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(self.URL)
            
            # Wait for content to load - wait for quickMoveInsListContainer
            print(f"[WilliamRyanHomesCambridgeNowScraper] Waiting for content to load...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "quickMoveInsListContainer"))
            )
            
            # Scroll to load more content
            print(f"[WilliamRyanHomesCambridgeNowScraper] Scrolling to load more content...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Get the page source after JavaScript execution
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find the quick move-ins container
            qmi_container = soup.find('div', id='quickMoveInsListContainer')
            if not qmi_container:
                print(f"[WilliamRyanHomesCambridgeNowScraper] No quick move-ins container found")
                return []
            
            # Find all quick move-in cards - they are direct children divs with shadow-xl class
            qmi_cards = qmi_container.find_all('div', class_=lambda x: x and 'shadow-xl' in x and 'duration-250' in x)
            print(f"[WilliamRyanHomesCambridgeNowScraper] Found {len(qmi_cards)} quick move-in cards")
            
            for idx, card in enumerate(qmi_cards):
                try:
                    print(f"[WilliamRyanHomesCambridgeNowScraper] Processing card {idx+1}")
                    
                    # Extract address - it's in the second button with font-serif text-[28px]
                    address_buttons = card.find_all('button')
                    address = ""
                    # The address is in the second button (index 1) with font-serif class
                    if len(address_buttons) >= 2:
                        span = address_buttons[1].find('span')
                        if span and 'font-serif' in span.get('class', []):
                            address = span.get_text(strip=True)
                    
                    if not address:
                        print(f"[WilliamRyanHomesCambridgeNowScraper] Skipping card {idx+1}: No address found")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[WilliamRyanHomesCambridgeNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price - look for price span with font-bold
                    price_spans = card.find_all('span', class_=lambda x: x and 'font-bold' in x)
                    current_price = None
                    for span in price_spans:
                        text = span.get_text(strip=True)
                        if text.startswith('$'):
                            current_price = self.parse_price(text)
                            if current_price:
                                break
                    
                    if not current_price:
                        print(f"[WilliamRyanHomesCambridgeNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract home details (beds, baths, garages, sqft) from grid-cols-4 div
                    grid_div = card.find('div', class_=lambda x: x and 'grid-cols-4' in x)
                    beds = ""
                    baths = ""
                    sqft = None
                    garages = ""
                    
                    if grid_div:
                        detail_divs = grid_div.find_all('div', class_='flex')
                        for detail_div in detail_divs:
                            spans = detail_div.find_all('span')
                            if len(spans) >= 2:
                                value_span = spans[0]  # First span has the number
                                label_span = spans[1]  # Second span has the label
                                
                                value_text = value_span.get_text(strip=True)
                                label_text = label_span.get_text(strip=True)
                                
                                if 'Beds' in label_text:
                                    beds = self.parse_beds(value_text)
                                elif 'Baths' in label_text:
                                    baths = self.parse_baths(value_text)
                                elif 'Garage' in label_text:
                                    garages = self.parse_garages(value_text)
                                elif 'Sq. ft.' in label_text:
                                    sqft = self.parse_sqft(value_text)
                    
                    if not sqft:
                        print(f"[WilliamRyanHomesCambridgeNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Extract plan name from the first button (the description/tagline)
                    plan_name = ""
                    if address_buttons and len(address_buttons) >= 1:
                        first_btn = address_buttons[0]
                        span = first_btn.find('span')
                        if span and 'text-blue-500' in span.get('class', []):
                            plan_name = span.get_text(strip=True).replace('<br>', '').strip()
                    
                    # If no plan name found, use address
                    if not plan_name:
                        plan_name = address
                    
                    # Extract image URL if available
                    image_url = ""
                    img_tag = card.find('img', alt='cardImage')
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag['src']
                        # Convert relative URL to absolute if needed
                        if image_url.startswith('/'):
                            image_url = f"https://www.williamryanhomes.com{image_url}"
                    
                    # Extract detail link
                    detail_link = ""
                    view_link = card.find('a', href=lambda x: x and '/quick-move-ins/' in x)
                    if view_link and view_link.get('href'):
                        detail_link = view_link['href']
                        if detail_link.startswith('/'):
                            detail_link = f"https://www.williamryanhomes.com{detail_link}"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": "1",  # Default to 1 story
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "William Ryan Homes",
                        "community": "Cambridge",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "status": "Move-In Ready",
                        "completion_date": "",
                        "sub_community": "",
                        "image_url": image_url,
                        "detail_link": detail_link,
                        "garages": garages
                    }
                    
                    print(f"[WilliamRyanHomesCambridgeNowScraper] Home {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[WilliamRyanHomesCambridgeNowScraper] Error processing card {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[WilliamRyanHomesCambridgeNowScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[WilliamRyanHomesCambridgeNowScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                driver.quit()

