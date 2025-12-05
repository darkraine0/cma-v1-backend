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

class ShaddockHomesCambridgeNowScraper(BaseScraper):
    URL = "https://www.shaddockhomes.com/communities/celina/hillside-village"
    
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

    def extract_status(self, card):
        """Extract availability status from the card."""
        status_banner = card.find('div', class_='HomeCard_statusBanner')
        if status_banner:
            status_span = status_banner.find('span')
            if status_span:
                status_class = status_span.get('class', [])
                if 'active' in status_class:
                    return "Move-In Ready"
                elif 'under_construction' in status_class:
                    return "Under Construction"
                else:
                    return status_span.get_text(strip=True)
        
        # Also check for completion date banner
        completion_banner = card.find('div', class_='HomeCard_completionDateBanner')
        if completion_banner:
            return "Under Construction"
        
        return ""

    def extract_completion_date(self, card):
        """Extract completion date from the card if available."""
        completion_banner = card.find('div', class_='HomeCard_completionDateBanner')
        if completion_banner:
            content_div = completion_banner.find('div', class_='HomeCard_completionDateBannerContent')
            if content_div:
                return content_div.get_text(strip=True)
        return ""

    def extract_floor_plan(self, card):
        """Extract floor plan name from the card."""
        floor_plan_items = card.find_all('li', class_='HomeCard_specItemAlt')
        for item in floor_plan_items:
            span_tag = item.find('span')
            if span_tag and span_tag.get_text(strip=True) == 'Floor Plan':
                floor_plan_link = item.find('a')
                if floor_plan_link:
                    return floor_plan_link.get_text(strip=True)
        return ""

    def extract_community(self, card):
        """Extract community name from the card."""
        community_items = card.find_all('li', class_='HomeCard_specItemAlt')
        for item in community_items:
            span_tag = item.find('span')
            if span_tag and span_tag.get_text(strip=True) == 'Community':
                community_link = item.find('a')
                if community_link:
                    return community_link.get_text(strip=True)
        return ""

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[ShaddockHomesCambridgeNowScraper] Fetching URL: {self.URL}")
            
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
            
            # Wait for content to load - wait for HomeCard_wrapper elements
            print(f"[ShaddockHomesCambridgeNowScraper] Waiting for content to load...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "HomeCard_wrapper"))
            )
            
            # Scroll to load more content
            print(f"[ShaddockHomesCambridgeNowScraper] Scrolling to load more content...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Get the page source after JavaScript execution
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all home cards - they have the class "HomeCard_wrapper"
            home_cards = soup.find_all('div', class_='HomeCard_wrapper')
            print(f"[ShaddockHomesCambridgeNowScraper] Found {len(home_cards)} home cards")
            
            for idx, card in enumerate(home_cards):
                try:
                    print(f"[ShaddockHomesCambridgeNowScraper] Processing card {idx+1}")
                    
                    # Extract address from HomeCard_city span
                    address_span = card.find('span', class_='HomeCard_city')
                    if not address_span:
                        print(f"[ShaddockHomesCambridgeNowScraper] Skipping card {idx+1}: No address found")
                        continue
                    
                    # Get the full text and extract just the address part (first part before comma)
                    full_text = address_span.get_text(strip=True)
                    address_parts = full_text.split(',')
                    address = address_parts[0].strip() if address_parts else full_text
                    
                    if not address:
                        print(f"[ShaddockHomesCambridgeNowScraper] Skipping card {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[ShaddockHomesCambridgeNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price from HomeCard_priceValue
                    price_div = card.find('div', class_='HomeCard_priceValue')
                    if not price_div:
                        print(f"[ShaddockHomesCambridgeNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_div.get_text(strip=True))
                    if not current_price:
                        print(f"[ShaddockHomesCambridgeNowScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract status
                    status = self.extract_status(card)
                    
                    # Extract completion date if available
                    completion_date = self.extract_completion_date(card)
                    
                    # Extract floor plan
                    floor_plan = self.extract_floor_plan(card)
                    
                    # Extract community
                    community = self.extract_community(card)
                    
                    # Extract home details (beds, baths, sqft, garages) from HomeCard_contentRow
                    detail_list = card.find('ul', class_='HomeCard_contentRow')
                    beds = ""
                    baths = ""
                    sqft = None
                    garages = ""
                    
                    if detail_list:
                        detail_items = detail_list.find_all('li', class_='HomeCard_specItem')
                        for item in detail_items:
                            label_span = item.find('span', class_='HomeCard_iconListLabel')
                            value_span = item.find('span', class_='HomeCard_iconListValue')
                            
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
                        print(f"[ShaddockHomesCambridgeNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Determine if this is a quick move-in or under construction
                    home_type = "now"
                    if "Under Construction" in status or completion_date:
                        home_type = "construction"
                    
                    # Extract image URL if available
                    image_url = ""
                    image_wrapper = card.find('div', class_='HomeCard_media')
                    if image_wrapper:
                        img_tag = image_wrapper.find('img', class_='HomeCard_image')
                        if img_tag and img_tag.get('src'):
                            image_url = img_tag['src']
                    
                    # Extract detail link
                    detail_link = ""
                    view_home_link = card.find('a', class_='btn')
                    if view_home_link and view_home_link.get('href'):
                        detail_link = view_home_link['href']
                        if detail_link.startswith('/'):
                            detail_link = f"https://www.shaddockhomes.com{detail_link}"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": "1",  # Default to 1 story
                        "price_per_sqft": price_per_sqft,
                        "plan_name": floor_plan or address,
                        "company": "Shaddock Homes",
                        "community": "Cambridge",
                        "type": home_type,
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "status": status,
                        "completion_date": completion_date,
                        "sub_community": community,
                        "image_url": image_url,
                        "detail_link": detail_link,
                        "garages": garages
                    }
                    
                    print(f"[ShaddockHomesCambridgeNowScraper] Home {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[ShaddockHomesCambridgeNowScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[ShaddockHomesCambridgeNowScraper] Successfully processed {len(listings)} items")
            return listings
            
        except Exception as e:
            print(f"[ShaddockHomesCambridgeNowScraper] Error: {e}")
            return []
        finally:
            if driver:
                driver.quit()

