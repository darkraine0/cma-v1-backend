import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ...base import BaseScraper
from typing import List, Dict


class BrightlandHomesCambridgeNowScraper(BaseScraper):
    URL = "https://www.drbhomes.com/drbhomes/find-your-home/communities/texas/dallasfort-worth/green-meadows/quick-move-in-homes"
    
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
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[BrightlandHomesCambridgeNowScraper] Fetching URL: {self.URL}")
            
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(self.URL)
            
            # Wait for the page to load and content to be populated
            print(f"[BrightlandHomesCambridgeNowScraper] Waiting for page to load...")
            time.sleep(10)
            
            # Scroll to trigger content loading
            print(f"[BrightlandHomesCambridgeNowScraper] Scrolling to trigger content loading...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            
            # Wait for home cards to be loaded
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "drb-qmi-home-card")))
            
            # Get the page source after JavaScript has loaded
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all home cards
            home_cards = soup.find_all('drb-qmi-home-card')
            print(f"[BrightlandHomesCambridgeNowScraper] Found {len(home_cards)} home cards")
            
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            for idx, card in enumerate(home_cards):
                try:
                    print(f"[BrightlandHomesCambridgeNowScraper] Processing card {idx+1}")
                    
                    # Extract address from h2 in heading-container
                    heading_container = card.find('div', class_='heading-container')
                    if not heading_container:
                        print(f"[BrightlandHomesCambridgeNowScraper] Skipping card {idx+1}: No heading-container found")
                        continue
                    
                    address_elem = heading_container.find('h2')
                    if not address_elem:
                        print(f"[BrightlandHomesCambridgeNowScraper] Skipping card {idx+1}: No address found")
                        continue
                    
                    address = address_elem.get_text(strip=True).replace('<br>', ' ').replace('\n', ' ').strip()
                    if not address:
                        print(f"[BrightlandHomesCambridgeNowScraper] Skipping card {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[BrightlandHomesCambridgeNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract price from heading-container paragraph
                    price = None
                    price_span = heading_container.find('span', class_=lambda x: x and 'ng-star-inserted' in x)
                    if price_span:
                        price_b = price_span.find('b')
                        if price_b:
                            price_text = price_b.get_text(strip=True)
                            price = self.parse_price(price_text)
                    
                    # If no price found, check if it's sold
                    if not price:
                        # Check if there's a "sold" indicator
                        special_elem = card.find('p', class_=lambda x: x and 'sold' in str(x).lower())
                        if special_elem and 'sold' in special_elem.get_text(strip=True).lower():
                            print(f"[BrightlandHomesCambridgeNowScraper] Skipping card {idx+1}: Home is sold")
                            continue
                        print(f"[BrightlandHomesCambridgeNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract details from details-container
                    details_container = card.find('div', class_='details-container')
                    beds = ""
                    baths = ""
                    sqft = None
                    garage = ""
                    plan_name = ""
                    status = ""
                    
                    if details_container:
                        detail_rows = details_container.find_all('div', class_='details-row')
                        
                        # First row: beds and baths
                        if len(detail_rows) > 0:
                            first_row = detail_rows[0]
                            bed_elems = first_row.find_all('p', class_=lambda x: x and 'ng-star-inserted' in x)
                            for bed_elem in bed_elems:
                                bed_text = bed_elem.get_text(strip=True)
                                if 'Bed' in bed_text or 'Beds' in bed_text:
                                    bed_b = bed_elem.find('b')
                                    if bed_b:
                                        beds = self.parse_beds(bed_b.get_text(strip=True))
                                elif 'Bath' in bed_text:
                                    bath_b = bed_elem.find('b')
                                    if bath_b:
                                        baths = self.parse_baths(bath_b.get_text(strip=True))
                        
                        # Second row: sqft and garage
                        if len(detail_rows) > 1:
                            second_row = detail_rows[1]
                            second_row_elems = second_row.find_all('p', class_=lambda x: x and 'ng-star-inserted' in x)
                            for elem in second_row_elems:
                                elem_text = elem.get_text(strip=True)
                                if 'Sq. Ft.' in elem_text or 'Sq Ft' in elem_text:
                                    sqft_b = elem.find('b')
                                    if sqft_b:
                                        sqft = self.parse_sqft(sqft_b.get_text(strip=True))
                                elif 'Car Garage' in elem_text or 'Garage' in elem_text:
                                    garage_b = elem.find('b')
                                    if garage_b:
                                        garage = self.parse_garage(garage_b.get_text(strip=True))
                        
                        # Third row: plan name and availability
                        if len(detail_rows) > 2:
                            third_row = detail_rows[2]
                            third_row_elems = third_row.find_all('p', class_=lambda x: x and 'ng-star-inserted' in x)
                            for elem in third_row_elems:
                                elem_text = elem.get_text(strip=True)
                                if 'Plan' in elem_text:
                                    plan_b = elem.find('b')
                                    if plan_b:
                                        plan_name = plan_b.get_text(strip=True)
                                elif 'Available' in elem_text:
                                    status_b = elem.find('b')
                                    if status_b:
                                        status = status_b.get_text(strip=True)
                    
                    if not sqft:
                        print(f"[BrightlandHomesCambridgeNowScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                    
                    # Extract detail link
                    detail_link = ""
                    link_tag = card.find('a', class_='btn-primary')
                    if link_tag and link_tag.get('href'):
                        href = link_tag['href']
                        if href.startswith('/'):
                            detail_link = f"https://www.drbhomes.com{href}"
                        else:
                            detail_link = href
                    
                    # Extract image URL
                    image_url = ""
                    img_tag = card.find('img', class_='gallery-image')
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag['src']
                    
                    # Default stories (most homes are 2-story)
                    stories = "2"
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name or address,
                        "company": "Brightland Homes",
                        "community": "Cambridge",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "status": status or "Available Now",
                        "mls": "",
                        "sub_community": "Green Meadows",
                        "image_url": image_url,
                        "detail_link": detail_link,
                        "garage": garage
                    }
                    
                    print(f"[BrightlandHomesCambridgeNowScraper] Home {idx+1}: {address} - {plan_name} - ${price:,} - {sqft} sqft - {beds} beds - {baths} baths")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[BrightlandHomesCambridgeNowScraper] Error processing card {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[BrightlandHomesCambridgeNowScraper] Successfully processed {len(listings)} homes")
            return listings
            
        except Exception as e:
            print(f"[BrightlandHomesCambridgeNowScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                driver.quit()
