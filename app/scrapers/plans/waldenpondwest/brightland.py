import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app.scrapers.base import BaseScraper


class BrightlandWaldenPondWestPlanScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.URL = "https://www.brightlandhomes.com/new-homes/texas/dallas/walden-pond"
        self.COMPANY = "Brightland Homes"
        self.COMMUNITY = "Walden Pond West"
        self.TYPE = "plan"

    def fetch_plans(self):
        """
        Fetch plan information from Brightland Homes Walden Pond West using Selenium
        """
        print(f"[BrightlandWaldenPondWestPlanScraper] Fetching URL: {self.URL}")
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(self.URL)
            
            # Wait for the page to load and content to be populated
            print(f"[BrightlandWaldenPondWestPlanScraper] Waiting for page to load...")
            time.sleep(10)
            
            # Scroll to trigger content loading
            print(f"[BrightlandWaldenPondWestPlanScraper] Scrolling to trigger content loading...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            
            # Wait for plan cards to be loaded
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "FloorPlansBlock_plansList__rdw8x")))
            
            # Try to click "View More" button to load all plans
            try:
                view_more_button = driver.find_element(By.CLASS_NAME, "FloorPlansBlock_viewMoreButton__UmNga")
                if view_more_button:
                    print(f"[BrightlandWaldenPondWestPlanScraper] Clicking 'View More' button to load all plans...")
                    driver.execute_script("arguments[0].click();", view_more_button)
                    time.sleep(5)  # Wait for additional plans to load
            except Exception as e:
                print(f"[BrightlandWaldenPondWestPlanScraper] Could not find or click 'View More' button: {e}")
            
            # Get the page source after JavaScript has loaded
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find plan cards only in the FloorPlansBlock (exclude SpecHomesBlock)
            floor_plans_block = soup.find('div', class_='FloorPlansBlock_mainContent__MwEgU')
            plan_cards = []
            if floor_plans_block:
                plans_list = floor_plans_block.find('div', class_='FloorPlansBlock_plansList__rdw8x')
                if plans_list:
                    plan_cards = plans_list.find_all('div', class_='Inventory-card_card__zCZYC')
            print(f"[BrightlandWaldenPondWestPlanScraper] Found {len(plan_cards)} plan cards")
            
            plans = []
            
            for card in plan_cards:
                try:
                    # Extract plan name
                    plan_name_elem = card.find('div', class_='Inventory-card_cardTitle__sfWte')
                    if not plan_name_elem:
                        continue
                    plan_name = plan_name_elem.get_text(strip=True)
                    if not plan_name:
                        continue
                    
                    # Extract price
                    price_elem = card.find('div', class_='Inventory-card_priceBox__9qHxs')
                    price = None
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        # Extract price from "Priced from $249,990"
                        price_match = re.search(r'\$([\d,]+)', price_text)
                        if price_match:
                            price = int(price_match.group(1).replace(',', ''))
                    
                    # Extract room details
                    room_details = card.find('div', class_='Inventory-card_roomDetails__0id2t')
                    beds = None
                    baths = None
                    sqft = None
                    
                    if room_details:
                        detail_items = room_details.find_all('div', class_='Inventory-card_roomDetail__dVHSI')
                        for item in detail_items:
                            # Get the text from the <p> tag
                            p_tag = item.find('p')
                            if p_tag:
                                text = p_tag.get_text(strip=True)
                                # Check if this is beds, baths, or sqft based on the icon
                                img = item.find('img')
                                if img:
                                    alt_text = img.get('alt', '').lower()
                                    if 'bedroom' in alt_text:
                                        beds = text
                                    elif 'bathroom' in alt_text:
                                        baths = text
                                    elif 'floor plan' in alt_text or 'plan' in alt_text:
                                        # Extract number from sqft text
                                        sqft_match = re.search(r'([\d,]+)', text)
                                        if sqft_match:
                                            sqft = int(sqft_match.group(1).replace(',', ''))
                    
                    # Extract URL
                    url = None
                    link_elem = card.find('a', href=True)
                    if link_elem:
                        url = link_elem.get('href')
                        if url and not url.startswith('http'):
                            url = f"https://www.brightlandhomes.com{url}"
                    
                    # Calculate price per sqft
                    price_per_sqft = None
                    if price and sqft:
                        price_per_sqft = round(price / sqft, 2)
                    
                    plan_data = {
                        'plan_name': plan_name,
                        'price': price,
                        'price_per_sqft': price_per_sqft,
                        'sqft': sqft,
                        'stories': None,  # Not available in this format
                        'beds': beds,
                        'baths': baths,
                        'company': self.COMPANY,
                        'community': self.COMMUNITY,
                        'type': self.TYPE,
                        'address': None,  # Plans don't have specific addresses
                        'design_number': None,
                        'url': url
                    }
                    
                    plans.append(plan_data)
                    print(f"[BrightlandWaldenPondWestPlanScraper] Plan: {plan_name} - ${price:,} - {sqft} sqft - {beds} beds - {baths} baths")
                        
                except Exception as e:
                    print(f"[BrightlandWaldenPondWestPlanScraper] Error processing plan card: {e}")
                    continue
            
            print(f"[BrightlandWaldenPondWestPlanScraper] Successfully processed {len(plans)} plans")
            return plans
            
        except Exception as e:
            print(f"[BrightlandWaldenPondWestPlanScraper] Error fetching plans: {e}")
            return []
        finally:
            if driver:
                driver.quit()
