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

class AmericanLegendHomesCambridgeNowScraper(BaseScraper):
    URL = "https://www.amlegendhomes.com/communities/texas/celina/ten-mile-creek"
    
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
        match = re.search(r'(\d+(?:-\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "3" and "3.5" formats
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def extract_mls(self, card):
        """Extract MLS number from the card."""
        mls_li = card.find('li', class_='HomeCard_link', string=re.compile(r'MLS:'))
        if mls_li:
            mls_text = mls_li.get_text(strip=True)
            mls_match = re.search(r'MLS:\s*(\d+)', mls_text)
            return mls_match.group(1) if mls_match else ""
        return ""

    def extract_floor_plan(self, card):
        """Extract floor plan name from the card."""
        # Look for all HomeCard_link elements and find the one with Floor Plan
        floor_plan_links = card.find_all('li', class_='HomeCard_link')
        for link_li in floor_plan_links:
            link_text = link_li.get_text(strip=True)
            if 'Floor Plan:' in link_text:
                # Try to find a link first
                floor_plan_link = link_li.find('a')
                if floor_plan_link:
                    return floor_plan_link.get_text(strip=True)
                else:
                    # If no link, extract from the text
                    plan_name = link_text.replace('Floor Plan:', '').strip()
                    return plan_name
        return ""

    def extract_community(self, card):
        """Extract community name from the card."""
        # Look for all HomeCard_link elements and find the one with Community
        community_links = card.find_all('li', class_='HomeCard_link')
        for link_li in community_links:
            link_text = link_li.get_text(strip=True)
            if 'Community:' in link_text:
                # Try to find a link first
                community_link = link_li.find('a')
                if community_link:
                    return community_link.get_text(strip=True)
                else:
                    # If no link, extract from the text
                    community_name = link_text.replace('Community:', '').strip()
                    return community_name
        return ""

    def extract_status(self, card):
        """Extract availability status from the card."""
        status_span = card.find('span', class_='HomeCard_priceStatus')
        if status_span:
            return status_span.get_text(strip=True)
        return ""

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[AmericanLegendHomesCambridgeNowScraper] Fetching URL: {self.URL}")
            
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
            
            # Wait for content to load
            print(f"[AmericanLegendHomesCambridgeNowScraper] Waiting for content to load...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "css-1j4dvj6"))
            )
            
            # Scroll to load more content and make buttons visible
            print(f"[AmericanLegendHomesCambridgeNowScraper] Scrolling to load more content...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Click "Load More Homes" button until it disappears or no more items load
            max_clicks = 10  # Safety limit
            click_count = 0
            while click_count < max_clicks:
                try:
                    load_more_button = driver.find_element(By.CLASS_NAME, "CommunityHomes_load")
                    if load_more_button and load_more_button.is_displayed():
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Clicking 'Load More Homes' button (attempt {click_count + 1})...")
                        driver.execute_script("arguments[0].click();", load_more_button)
                        time.sleep(3)  # Wait for content to load
                        click_count += 1
                    else:
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Load More button not visible, stopping")
                        break
                except Exception as e:
                    print(f"[AmericanLegendHomesCambridgeNowScraper] No more 'Load More Homes' button found: {e}")
                    break
            
            if click_count > 0:
                print(f"[AmericanLegendHomesCambridgeNowScraper] Clicked 'Load More Homes' button {click_count} times")
            
            # Scroll again to ensure all content is loaded
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Get the page source after JavaScript execution and clicking
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all home cards
            home_cards = soup.find_all('div', class_='css-1j4dvj6')
            print(f"[AmericanLegendHomesCambridgeNowScraper] Found {len(home_cards)} home cards")
            
            for idx, card in enumerate(home_cards):
                try:
                    print(f"[AmericanLegendHomesCambridgeNowScraper] Processing card {idx+1}")
                    
                    # Extract address
                    title_link = card.find('a', class_='HomeCard_title')
                    if not title_link:
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Skipping card {idx+1}: No title link found")
                        continue
                    
                    # Get the full text and extract just the address part
                    full_title_text = title_link.get_text(strip=True)
                    # The address is typically the first part before any comma
                    address_parts = full_title_text.split(',')
                    if len(address_parts) >= 2:
                        address = address_parts[0].strip()
                        # Remove any trailing "Celina" or other city names that might be attached
                        if address.endswith('Celina'):
                            address = address[:-6].strip()
                        elif address.endswith('TX'):
                            address = address[:-2].strip()
                        elif address.endswith('75009'):
                            address = address[:-5].strip()
                    else:
                        address = full_title_text
                    
                    if not address:
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Skipping card {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price
                    price_span = card.find('span', class_='HomeCard_price')
                    if not price_span:
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_span.get_text())
                    if not current_price:
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract status
                    status = self.extract_status(card)
                    
                    # Extract floor plan
                    floor_plan = self.extract_floor_plan(card)
                    
                    # Extract community
                    community = self.extract_community(card)
                    
                    # Extract MLS
                    mls = self.extract_mls(card)
                    
                    # Extract home details (stories, beds, baths, sqft)
                    detail_list = card.find('ul', class_='HomeCard_list')
                    beds = ""
                    baths = ""
                    stories = ""
                    sqft = None
                    
                    if detail_list:
                        detail_items = detail_list.find_all('li', class_='HomeCard_listItem')
                        for item in detail_items:
                            item_text = item.get_text(strip=True)
                            if 'Stories' in item_text:
                                stories = self.parse_stories(item_text)
                            elif 'Beds' in item_text:
                                beds = self.parse_beds(item_text)
                            elif 'Baths' in item_text:
                                baths = self.parse_baths(item_text)
                            elif 'Sqft' in item_text:
                                sqft = self.parse_sqft(item_text)
                    
                    if not sqft:
                        print(f"[AmericanLegendHomesCambridgeNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Determine if this is a quick move-in or under construction
                    home_type = "now"
                    if "Under Construction" in status:
                        home_type = "construction"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories or "1",
                        "price_per_sqft": price_per_sqft,
                        "plan_name": floor_plan or address,
                        "company": "American Legend Homes",
                        "community": "Cambridge",
                        "type": home_type,
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "status": status,
                        "mls": mls,
                        "sub_community": community
                    }
                    
                    print(f"[AmericanLegendHomesCambridgeNowScraper] Home {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[AmericanLegendHomesCambridgeNowScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[AmericanLegendHomesCambridgeNowScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[AmericanLegendHomesCambridgeNowScraper] Error: {e}")
            return []
        finally:
            if driver:
                driver.quit()
