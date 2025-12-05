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


class HighlandHomesEdgewaterPlanScraper(BaseScraper):
    URL = "https://www.highlandhomes.com/dfw/mclendon-chisholm/sonoma-verde/70ft-lots/section"
    
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

    def parse_sqft_range(self, text):
        """Extract minimum square footage from range like '2,802 - 2,822'."""
        if not text:
            return None
        
        # Try to find a range pattern
        range_match = re.search(r'(\d+(?:,\d+)?)\s*-\s*(\d+(?:,\d+)?)', text)
        if range_match:
            # Return the minimum value
            min_sqft = int(range_match.group(1).replace(",", ""))
            return min_sqft
        
        # If no range, try to find a single number
        single_match = re.search(r'(\d+(?:,\d+)?)', text)
        if single_match:
            return int(single_match.group(1).replace(",", ""))
        
        return None

    def parse_beds(self, text):
        """Extract number of bedrooms from text (can be range like '3-4')."""
        if not text:
            return ""
        # Extract first number from range or single number
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text (can be range like '3-4')."""
        if not text:
            return ""
        # Extract first number from range or single number
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        if not text:
            return ""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[HighlandHomesEdgewaterPlanScraper] Starting to fetch HighlandHomes plans for Edgewater")
            
            # Setup Chrome options for Cloudflare protection
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            print(f"[HighlandHomesEdgewaterPlanScraper] Fetching URL: {self.URL}")
            driver.get(self.URL)
            
            # Wait for the page to load and Cloudflare to pass
            print(f"[HighlandHomesEdgewaterPlanScraper] Waiting for page to load...")
            time.sleep(15)  # Extra time for Cloudflare
            
            # Scroll to trigger content loading
            print(f"[HighlandHomesEdgewaterPlanScraper] Scrolling to trigger content loading...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(3)
            
            # Wait for plan cards section
            wait = WebDriverWait(driver, 30)
            try:
                wait.until(EC.presence_of_element_located((By.ID, "planCards")))
            except:
                print(f"[HighlandHomesEdgewaterPlanScraper] Waiting for planCards section...")
                time.sleep(5)
            
            # Get the page source after JavaScript has loaded
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find the plan cards section
            plan_section = soup.find('section', id='planCards')
            if not plan_section:
                print(f"[HighlandHomesEdgewaterPlanScraper] No planCards section found")
                return []
            
            # Find all plan cards
            plan_cards = plan_section.find_all('a', class_='home-container homePlan')
            print(f"[HighlandHomesEdgewaterPlanScraper] Found {len(plan_cards)} plan cards")
            
            all_plans = []
            seen_plan_names = set()
            
            for idx, card in enumerate(plan_cards):
                try:
                    # Extract plan name
                    plan_name_elem = card.find('span', class_='homeIdentifier')
                    if not plan_name_elem:
                        continue
                    
                    plan_name = plan_name_elem.get_text(strip=True)
                    if not plan_name:
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[HighlandHomesEdgewaterPlanScraper] Skipping duplicate plan: {plan_name}")
                        continue
                    seen_plan_names.add(plan_name)
                    
                    # Extract starting price
                    price = None
                    price_elem = card.find('span', class_='price')
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self.parse_price(price_text)
                    
                    # Extract square footage (range)
                    sqft = None
                    sqft_elem = card.find('span', class_='label', string=re.compile('sq ft', re.I))
                    if sqft_elem:
                        sqft_parent = sqft_elem.find_parent('div', class_='homeDetailItem')
                        if sqft_parent:
                            numeral_elem = sqft_parent.find('span', class_='numeral')
                            if numeral_elem:
                                sqft_text = numeral_elem.get_text(strip=True)
                                sqft = self.parse_sqft_range(sqft_text)
                    
                    if not price or not sqft:
                        print(f"[HighlandHomesEdgewaterPlanScraper] Skipping plan {idx+1}: Missing price or sqft")
                        continue
                    
                    # Extract beds (can be range like "3-4")
                    beds = ""
                    beds_elem = card.find('span', class_='label', string=re.compile('beds', re.I))
                    if beds_elem:
                        beds_parent = beds_elem.find_parent('div', class_='homeDetailItem')
                        if beds_parent:
                            numeral_elem = beds_parent.find('span', class_='numeral')
                            if numeral_elem:
                                beds_text = numeral_elem.get_text(strip=True)
                                beds = self.parse_beds(beds_text)
                    
                    # Extract full baths (can be range like "3-4")
                    baths = ""
                    full_baths_elem = card.find('span', class_='label', string=re.compile('full baths', re.I))
                    if full_baths_elem:
                        baths_parent = full_baths_elem.find_parent('div', class_='homeDetailItem')
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
                    
                    # Extract image URL
                    image_url = ""
                    img_tag = card.find('img', class_='homePlan_ifp')
                    if img_tag:
                        img_src = img_tag.get('data-src') or img_tag.get('src')
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
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "HighlandHomes",
                        "community": "Edgewater",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": plan_name,  # Use plan name as address for plans
                        "original_price": None,
                        "price_cut": "",
                        "status": "",
                        "mls": "",
                        "sub_community": "",
                        "image_url": image_url,
                        "detail_link": detail_link,
                        "garage": garage
                    }
                    
                    print(f"[HighlandHomesEdgewaterPlanScraper] Plan {idx+1}: {plan_name} - ${price:,} - {sqft} sqft")
                    all_plans.append(plan_data)
                    
                except Exception as e:
                    print(f"[HighlandHomesEdgewaterPlanScraper] Error processing plan {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[HighlandHomesEdgewaterPlanScraper] Successfully processed {len(all_plans)} plans")
            return all_plans
            
        except Exception as e:
            print(f"[HighlandHomesEdgewaterPlanScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                driver.quit()

