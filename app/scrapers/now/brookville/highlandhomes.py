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


class HighlandHomesBrookvilleNowScraper(BaseScraper):
    URL = "https://www.highlandhomes.com/dfw/forney/devonshire"
    
    def parse_price(self, text):
        """Extract price from text."""
        if not text:
            return None
        cleaned_text = text.replace(" ", "").replace("$", "").replace(",", "")
        match = re.search(r'(\d+)', cleaned_text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    def parse_sqft(self, text):
        """Extract square footage from text."""
        if not text:
            return None
        cleaned_text = text.replace(",", "")
        match = re.search(r'(\d+)', cleaned_text)
        return int(match.group(1)) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        if not text:
            return ""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text (format like '4/2')."""
        if not text:
            return ""
        # Extract the full baths part (first number)
        match = re.search(r'(\d+)/', text)
        if match:
            return str(match.group(1))
        # Fallback: just get first number
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        if not text:
            return ""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_status(self, text):
        """Extract status from text."""
        if not text:
            return "Available"
        text_lower = text.lower().strip()
        if "complete" in text_lower and "move-in" in text_lower:
            return "Complete & Move-in Ready!"
        return text.strip()

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[HighlandHomesBrookvilleNowScraper] Starting to fetch HighlandHomes data for Brookville")
            
            # Setup Chrome options for Cloudflare protection
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            print(f"[HighlandHomesBrookvilleNowScraper] Fetching URL: {self.URL}")
            driver.get(self.URL)
            
            # Wait for the page to load and Cloudflare to pass
            print(f"[HighlandHomesBrookvilleNowScraper] Waiting for page to load...")
            time.sleep(15)  # Extra time for Cloudflare
            
            # Scroll to trigger content loading
            print(f"[HighlandHomesBrookvilleNowScraper] Scrolling to trigger content loading...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(3)
            
            # Wait for quick move-in container
            wait = WebDriverWait(driver, 30)
            try:
                wait.until(EC.presence_of_element_located((By.ID, "moveInReadyContainer")))
            except:
                print(f"[HighlandHomesBrookvilleNowScraper] Waiting for moveInReadyContainer...")
                time.sleep(5)
            
            # Get the page source after JavaScript has loaded
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find the quick move-in section
            move_in_section = soup.find('section', class_=lambda x: x and 'alternate' in x and 'extra_padding_top' in x)
            if not move_in_section:
                print(f"[HighlandHomesBrookvilleNowScraper] No quick move-in section found")
                return []
            
            # Find the container with home listings
            container = move_in_section.find('div', id='moveInReadyContainer')
            if not container:
                print(f"[HighlandHomesBrookvilleNowScraper] No moveInReadyContainer found")
                return []
            
            # Find all home cards - search for <a> tags that have both 'home-container' and 'homeSpec' classes
            home_cards = []
            all_links = container.find_all('a')
            for link in all_links:
                classes = link.get('class', [])
                if isinstance(classes, list):
                    if 'home-container' in classes and 'homeSpec' in classes:
                        home_cards.append(link)
                elif isinstance(classes, str):
                    if 'home-container' in classes and 'homeSpec' in classes:
                        home_cards.append(link)
            
            print(f"[HighlandHomesBrookvilleNowScraper] Found {len(home_cards)} home cards")
            
            # If no cards found, try finding by href pattern (fallback)
            if len(home_cards) == 0:
                print(f"[HighlandHomesBrookvilleNowScraper] Trying href pattern selector as fallback...")
                home_cards = container.find_all('a', href=re.compile(r'/dfw/'))
                print(f"[HighlandHomesBrookvilleNowScraper] Found {len(home_cards)} home cards with href pattern")
            
            all_listings = []
            seen_addresses = set()
            
            for idx, card in enumerate(home_cards):
                try:
                    # Extract address
                    address_elem = card.find('span', class_='homeIdentifier')
                    if not address_elem:
                        continue
                    
                    address = address_elem.get_text(strip=True)
                    if not address:
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[HighlandHomesBrookvilleNowScraper] Skipping duplicate address: {address}")
                        continue
                    seen_addresses.add(address)
                    
                    # Extract plan name
                    plan_name = ""
                    plan_elem = card.find('p', class_='homeUpgrades')
                    if plan_elem:
                        plan_text = plan_elem.get_text(strip=True)
                        plan_match = re.search(r'^(.+?)\s+Plan\s+(?:with|$)', plan_text)
                        if plan_match:
                            plan_name = plan_match.group(1).strip() + " Plan"
                        else:
                            if ' with ' in plan_text:
                                plan_name = plan_text.split(' with ')[0].strip()
                            else:
                                plan_name = plan_text.strip()
                    
                    # Extract price
                    price = None
                    price_elem = card.find('span', class_='price')
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self.parse_price(price_text)
                    
                    # Extract square footage
                    sqft = None
                    sqft_elem = card.find('div', class_='homeSqFootage')
                    if sqft_elem:
                        numeral_elem = sqft_elem.find('span', class_='numeral')
                        if numeral_elem:
                            sqft_text = numeral_elem.get_text(strip=True)
                            sqft = self.parse_sqft(sqft_text)
                    
                    if not price or not sqft:
                        print(f"[HighlandHomesBrookvilleNowScraper] Skipping listing {idx+1}: Missing price or sqft")
                        continue
                    
                    # Extract beds
                    beds = ""
                    beds_elem = card.find('span', class_='label', string=re.compile('beds', re.I))
                    if beds_elem:
                        beds_parent = beds_elem.find_parent('div', class_='homeDetailItem')
                        if beds_parent:
                            numeral_elem = beds_parent.find('span', class_='numeral')
                            if numeral_elem:
                                beds_text = numeral_elem.get_text(strip=True)
                                beds = self.parse_beds(beds_text)
                    
                    # Extract baths (format like "4/2")
                    baths = ""
                    baths_elem = card.find('span', class_='label', string=re.compile('baths', re.I))
                    if baths_elem:
                        baths_parent = baths_elem.find_parent('div', class_='homeDetailItem')
                        if baths_parent:
                            numeral_elem = baths_parent.find('span', class_='numeral')
                            if numeral_elem:
                                baths_text = numeral_elem.get_text(strip=True)
                                baths = self.parse_baths(baths_text)
                    
                    # Extract stories
                    stories = ""
                    stories_elem = card.find('span', class_='label', string=re.compile('stories', re.I))
                    if stories_elem:
                        stories_parent = stories_elem.find_parent('div', class_='homeDetailItem')
                        if stories_parent:
                            numeral_elem = stories_parent.find('span', class_='numeral')
                            if numeral_elem:
                                stories = numeral_elem.get_text(strip=True)
                    
                    # Extract garages
                    garage = ""
                    garage_elem = card.find('span', class_='label', string=re.compile('garages', re.I))
                    if garage_elem:
                        garage_parent = garage_elem.find_parent('div', class_='homeDetailItem')
                        if garage_parent:
                            numeral_elem = garage_parent.find('span', class_='numeral')
                            if numeral_elem:
                                garage_text = numeral_elem.get_text(strip=True)
                                garage = self.parse_garage(garage_text)
                    
                    # Extract status
                    status = "Available"
                    status_elem = card.find('span', class_=lambda x: x and 'home-tag' in x and 'completed-home' in x)
                    if not status_elem:
                        status_elem = card.find('span', class_=lambda x: x and 'completed-home' in x)
                    if status_elem:
                        status_text = status_elem.get_text(strip=True)
                        status = self.parse_status(status_text)
                    
                    # Extract image URL
                    image_url = ""
                    img_tag = card.find('img')
                    if img_tag:
                        img_src = img_tag.get('src') or img_tag.get('data-src')
                        if img_src:
                            if img_src.startswith('//'):
                                image_url = f"https:{img_src}"
                            elif img_src.startswith('/'):
                                image_url = f"https://www.highlandhomes.com{img_src}"
                            else:
                                image_url = img_src
                    
                    # Extract detail link
                    detail_link = ""
                    href = card.get('href')
                    if href:
                        if href.startswith('/'):
                            detail_link = f"https://www.highlandhomes.com{href}"
                        elif href.startswith('http'):
                            detail_link = href
                        else:
                            detail_link = f"https://www.highlandhomes.com/{href}"
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                    
                    listing_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name or address,
                        "company": "HighlandHomes",
                        "community": "Brookville",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "status": status,
                        "mls": "",
                        "sub_community": "",
                        "image_url": image_url,
                        "detail_link": detail_link,
                        "garage": garage
                    }
                    
                    print(f"[HighlandHomesBrookvilleNowScraper] Home {idx+1}: {address} - {plan_name} - ${price:,} - {sqft} sqft - {status}")
                    all_listings.append(listing_data)
                    
                except Exception as e:
                    print(f"[HighlandHomesBrookvilleNowScraper] Error processing listing {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[HighlandHomesBrookvilleNowScraper] Successfully processed {len(all_listings)} homes")
            return all_listings
            
        except Exception as e:
            print(f"[HighlandHomesBrookvilleNowScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                driver.quit()
