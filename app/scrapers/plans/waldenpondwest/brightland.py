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


class BrightlandWaldenPondWestPlanScraper(BaseScraper):
    URL = "https://www.drbhomes.com/drbhomes/find-your-home/communities/texas/dallasfort-worth/walden-pond/home-plans"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract starting price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text (can be range like '3 - 4')."""
        # Extract first number from range or single number
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text (can be range like '2 - 3')."""
        # Extract first number from range or single number
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract number of garage spaces from text (can be range like '2 - 3')."""
        # Extract first number from range or single number
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[BrightlandWaldenPondWestPlanScraper] Fetching URL: {self.URL}")
            
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
            print(f"[BrightlandWaldenPondWestPlanScraper] Waiting for page to load...")
            time.sleep(10)
            
            # Scroll to trigger content loading
            print(f"[BrightlandWaldenPondWestPlanScraper] Scrolling to trigger content loading...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            
            # Wait for plan cards to be loaded
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "drb-home-plan-card")))
            
            # Get the page source after JavaScript has loaded
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all plan cards
            plan_cards = soup.find_all('drb-home-plan-card')
            print(f"[BrightlandWaldenPondWestPlanScraper] Found {len(plan_cards)} plan cards")
            
            listings = []
            seen_plans = set()  # Track plan names to prevent duplicates
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[BrightlandWaldenPondWestPlanScraper] Processing card {idx+1}")
                    
                    # Extract plan name from h2 in heading-content
                    heading_content = card.find('div', class_='heading-content')
                    if not heading_content:
                        print(f"[BrightlandWaldenPondWestPlanScraper] Skipping card {idx+1}: No heading-content found")
                        continue
                    
                    plan_name_elem = heading_content.find('h2')
                    if not plan_name_elem:
                        print(f"[BrightlandWaldenPondWestPlanScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    plan_name = plan_name_elem.get_text(strip=True)
                    if not plan_name:
                        print(f"[BrightlandWaldenPondWestPlanScraper] Skipping card {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plans
                    if plan_name in seen_plans:
                        print(f"[BrightlandWaldenPondWestPlanScraper] Skipping card {idx+1}: Duplicate plan '{plan_name}'")
                        continue
                    
                    seen_plans.add(plan_name)
                    
                    # Extract starting price
                    price_elem = heading_content.find('p', class_=lambda x: x and 'ng-star-inserted' in x)
                    price = None
                    if price_elem:
                        price_b = price_elem.find('b')
                        if price_b:
                            price_text = price_b.get_text(strip=True)
                            price = self.parse_price(price_text)
                    
                    if not price:
                        print(f"[BrightlandWaldenPondWestPlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract details from details-container
                    details_container = card.find('div', class_='details-container')
                    beds = ""
                    baths = ""
                    sqft = None
                    garage = ""
                    
                    if details_container:
                        detail_rows = details_container.find_all('div', class_='details-row')
                        
                        # First row: beds and baths
                        if len(detail_rows) > 0:
                            first_row = detail_rows[0]
                            bed_elem = first_row.find('p', class_='bed')
                            if bed_elem:
                                bed_b = bed_elem.find('b')
                                if bed_b:
                                    beds = self.parse_beds(bed_b.get_text(strip=True))
                            
                            bath_elems = first_row.find_all('p', class_=lambda x: x and 'ng-star-inserted' in x)
                            for bath_elem in bath_elems:
                                bath_b = bath_elem.find('b')
                                if bath_b:
                                    bath_text = bath_b.get_text(strip=True)
                                    if 'Full Bath' in bath_elem.get_text() or 'Bath' in bath_elem.get_text():
                                        baths = self.parse_baths(bath_text)
                                        break
                        
                        # Second row: sqft and garage
                        if len(detail_rows) > 1:
                            second_row = detail_rows[1]
                            sqft_elems = second_row.find_all('p', class_=lambda x: x and 'ng-star-inserted' in x)
                            for sqft_elem in sqft_elems:
                                sqft_text = sqft_elem.get_text(strip=True)
                                if 'Sq. Ft.' in sqft_text or 'Sq Ft' in sqft_text:
                                    sqft_b = sqft_elem.find('b')
                                    if sqft_b:
                                        sqft = self.parse_sqft(sqft_b.get_text(strip=True))
                                elif 'Car Garage' in sqft_text or 'Garage' in sqft_text:
                                    garage_b = sqft_elem.find('b')
                                    if garage_b:
                                        garage = self.parse_garage(garage_b.get_text(strip=True))
                    
                    if not sqft:
                        print(f"[BrightlandWaldenPondWestPlanScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                    
                    # Extract image URL
                    image_url = ""
                    img_tag = card.find('img', class_='gallery-image')
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag['src']
                    
                    # Extract detail link
                    detail_link = ""
                    link_tag = card.find('a', class_='btn-primary')
                    if link_tag and link_tag.get('href'):
                        href = link_tag['href']
                        if href.startswith('/'):
                            detail_link = f"https://www.drbhomes.com{href}"
                        else:
                            detail_link = href
                    
                    # Default stories (most plans are 2-story)
                    stories = "2"
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Brightland Homes",
                        "community": "Walden Pond West",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",
                        "original_price": None,
                        "price_cut": "",
                        "status": "",
                        "mls": "",
                        "sub_community": "",
                        "image_url": image_url,
                        "detail_link": detail_link,
                        "garage": garage
                    }
                    
                    print(f"[BrightlandWaldenPondWestPlanScraper] Plan {idx+1}: {plan_name} - ${price:,} - {sqft} sqft - {beds} beds - {baths} baths")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[BrightlandWaldenPondWestPlanScraper] Error processing card {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[BrightlandWaldenPondWestPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[BrightlandWaldenPondWestPlanScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                driver.quit()
