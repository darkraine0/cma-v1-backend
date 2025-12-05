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

class ShaddockHomesCambridgePlanScraper(BaseScraper):
    URL = "https://www.shaddockhomes.com/communities/celina/hillside-village"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text (handles 'From $X' format)."""
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

    def parse_lot_size(self, text):
        """Extract lot size from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[ShaddockHomesCambridgePlanScraper] Fetching URL: {self.URL}")
            
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
            
            # Wait for content to load - wait for PlanCard_wrapper elements
            print(f"[ShaddockHomesCambridgePlanScraper] Waiting for content to load...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "PlanCard_wrapper"))
            )
            
            # Scroll to load more content
            print(f"[ShaddockHomesCambridgePlanScraper] Scrolling to load more content...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Get the page source after JavaScript execution
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all plan cards - they have the class "PlanCard_wrapper"
            plan_cards = soup.find_all('div', class_='PlanCard_wrapper')
            print(f"[ShaddockHomesCambridgePlanScraper] Found {len(plan_cards)} plan cards")
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[ShaddockHomesCambridgePlanScraper] Processing plan card {idx+1}")
                    
                    # Extract plan name from PlanCard_name link
                    plan_name_link = card.find('h4', class_='PlanCard_name')
                    if not plan_name_link:
                        print(f"[ShaddockHomesCambridgePlanScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    plan_name_tag = plan_name_link.find('a')
                    if not plan_name_tag:
                        print(f"[ShaddockHomesCambridgePlanScraper] Skipping card {idx+1}: No plan name link found")
                        continue
                    
                    plan_name = plan_name_tag.get_text(strip=True)
                    if not plan_name:
                        print(f"[ShaddockHomesCambridgePlanScraper] Skipping card {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[ShaddockHomesCambridgePlanScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract price from PlanCard_priceValue
                    price_div = card.find('div', class_='PlanCard_priceValue')
                    if not price_div:
                        print(f"[ShaddockHomesCambridgePlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    price_text = price_div.get_text(strip=True)
                    current_price = self.parse_price(price_text)
                    if not current_price:
                        print(f"[ShaddockHomesCambridgePlanScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract plan details (beds, baths, sqft, garages) from PlanCard_contentRow
                    detail_list = card.find('ul', class_='PlanCard_contentRow')
                    beds = ""
                    baths = ""
                    sqft = None
                    garages = ""
                    
                    if detail_list:
                        detail_items = detail_list.find_all('li', class_='PlanCard_specItem')
                        for item in detail_items:
                            label_span = item.find('span', class_='PlanCard_iconListLabel')
                            value_span = item.find('span', class_='PlanCard_iconListValue')
                            
                            if label_span and value_span:
                                label = label_span.get_text(strip=True)
                                value_text = value_span.get_text(strip=True)
                                
                                if 'Beds' in label:
                                    beds = self.parse_beds(value_text)
                                elif 'Baths' in label:
                                    baths = self.parse_baths(value_text)
                                elif 'SQ FT' in label:
                                    sqft = self.parse_sqft(value_text)
                                elif 'Garages' in label:
                                    garages = self.parse_beds(value_text)
                    
                    if not sqft:
                        print(f"[ShaddockHomesCambridgePlanScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Extract lot size from the div with "Lot Size:" text
                    lot_size = ""
                    lot_size_divs = card.find_all('div', class_='PlanCard_contentRow')
                    for div in lot_size_divs:
                        div_text = div.get_text(strip=True)
                        if 'Lot Size:' in div_text:
                            lot_size_b = div.find('b')
                            if lot_size_b:
                                lot_size = self.parse_lot_size(lot_size_b.get_text(strip=True))
                            break
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Extract image URL if available
                    image_url = ""
                    image_wrapper = card.find('div', class_='PlanCard_media')
                    if image_wrapper:
                        img_tag = image_wrapper.find('img', class_='PlanCard_image')
                        if img_tag and img_tag.get('src'):
                            image_url = img_tag['src']
                    
                    # Extract plan detail link
                    detail_link = ""
                    if plan_name_tag and plan_name_tag.get('href'):
                        detail_link = plan_name_tag['href']
                        # Make it absolute URL if it's relative
                        if detail_link.startswith('/'):
                            detail_link = f"https://www.shaddockhomes.com{detail_link}"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": "1",  # Default to 1 story
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Shaddock Homes",
                        "community": "Cambridge",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",
                        "original_price": None,
                        "price_cut": "",
                        "image_url": image_url,
                        "detail_link": detail_link,
                        "lot_size": lot_size,
                        "garages": garages
                    }
                    
                    print(f"[ShaddockHomesCambridgePlanScraper] Plan {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[ShaddockHomesCambridgePlanScraper] Error processing plan card {idx+1}: {e}")
                    continue
            
            print(f"[ShaddockHomesCambridgePlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[ShaddockHomesCambridgePlanScraper] Error: {e}")
            return []
        finally:
            if driver:
                driver.quit()

