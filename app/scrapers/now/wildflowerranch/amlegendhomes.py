import requests
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ...base import BaseScraper
from typing import List, Dict

class AmericanLegendHomesWildflowerRanchNowScraper(BaseScraper):
    URL = "https://www.amlegendhomes.com/communities/texas/justin/treeline#homes"
    
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
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def get_status(self, container):
        """Extract the status of the home."""
        status_elem = container.find('span', class_='flex-fill px-3 py-2 HomeCard_priceStatus')
        if status_elem:
            status_text = status_elem.get_text(strip=True)
            if "SOLD" in status_text:
                return "sold"
            elif "Available" in status_text:
                return "available"
        return "available"

    def get_plan_number(self, container):
        """Extract plan number from the container."""
        plan_link = container.find('a', href=re.compile(r'/plan/plan-\d+'))
        if plan_link:
            plan_text = plan_link.get_text(strip=True)
            plan_match = re.search(r'Plan (\d+)', plan_text)
            return plan_match.group(1) if plan_match else None
        return None

    def get_mls_number(self, container):
        """Extract MLS number if available."""
        mls_elem = container.find('li', class_='HomeCard_link')
        if mls_elem and 'MLS:' in mls_elem.get_text():
            mls_text = mls_elem.get_text(strip=True)
            mls_match = re.search(r'MLS:\s*(\d+)', mls_text)
            return mls_match.group(1) if mls_match else None
        return None

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[AmericanLegendHomesWildflowerRanchNowScraper] Fetching URL: {self.URL}")
            
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
            print(f"[AmericanLegendHomesWildflowerRanchNowScraper] Waiting for content to load...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "css-1j4dvj6"))
            )
            
            # Get the page source after JavaScript execution
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all home cards
            home_cards = soup.find_all('div', class_='css-1j4dvj6', role='group')
            print(f"[AmericanLegendHomesWildflowerRanchNowScraper] Found {len(home_cards)} home cards")
            
            listings = []
            
            for idx, card in enumerate(home_cards):
                try:
                    # Extract address
                    address_elem = card.find('a', class_='flex-fill mr-auto HomeCard_title px-0')
                    address = address_elem.get_text(strip=True) if address_elem else None
                    
                    if not address:
                        print(f"[AmericanLegendHomesWildflowerRanchNowScraper] Skipping card {idx+1}: No address found")
                        continue
                    
                    # Extract price
                    price_elem = card.find('span', class_='px-3 py-2 HomeCard_price')
                    price_text = price_elem.get_text(strip=True) if price_elem else ""
                    price = self.parse_price(price_text)
                    
                    if not price:
                        print(f"[AmericanLegendHomesWildflowerRanchNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract property details from the list
                    details_list = card.find('ul', class_='list-unstyled m-0 px-3 d-flex align-items-center justify-content-between HomeCard_list flex-fill')
                    if not details_list:
                        print(f"[AmericanLegendHomesWildflowerRanchNowScraper] Skipping card {idx+1}: No property details found")
                        continue
                    
                    stories = None
                    beds = None
                    baths = None
                    sqft = None
                    
                    list_items = details_list.find_all('li', class_='HomeCard_listItem')
                    for item in list_items:
                        text = item.get_text(strip=True)
                        bold_elem = item.find('b')
                        if bold_elem:
                            label = bold_elem.get_text(strip=True)
                            value = text.replace(label, '').strip()
                            
                            if label == 'Stories':
                                stories = value
                            elif label == 'Beds':
                                beds = value
                            elif label == 'Baths':
                                baths = value
                            elif label == 'Sqft':
                                sqft = int(value.replace(',', '')) if value.replace(',', '').isdigit() else None
                    
                    if not all([stories, beds, baths, sqft]):
                        print(f"[AmericanLegendHomesWildflowerRanchNowScraper] Skipping card {idx+1}: Missing property details (stories: {stories}, beds: {beds}, baths: {baths}, sqft: {sqft})")
                        continue
                    
                    # Get additional details
                    status = self.get_status(card)
                    plan_number = self.get_plan_number(card)
                    mls_number = self.get_mls_number(card)
                    
                    # Extract property link
                    link_elem = card.find('a', class_='HomeCard_imageWrapper')
                    property_url = link_elem.get('href') if link_elem else None
                    if property_url and not property_url.startswith('http'):
                        property_url = f"https://www.amlegendhomes.com{property_url}"
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    # Create plan name with address
                    plan_name = address
                    if plan_number:
                        plan_name += f" (Plan {plan_number})"
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "American Legend Homes",
                        "community": "Wildflower Ranch",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": "",
                        "status": status,
                        "url": property_url,
                        "plan_number": plan_number,
                        "mls_number": mls_number
                    }
                    
                    print(f"[AmericanLegendHomesWildflowerRanchNowScraper] Property {idx+1}: {plan_data['plan_name']} - ${price:,} - {sqft:,} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[AmericanLegendHomesWildflowerRanchNowScraper] Error processing property {idx+1}: {e}")
                    continue
            
            print(f"[AmericanLegendHomesWildflowerRanchNowScraper] Successfully processed {len(listings)} properties")
            return listings
            
        except Exception as e:
            print(f"[AmericanLegendHomesWildflowerRanchNowScraper] Error: {e}")
            return []
        finally:
            if driver:
                driver.quit()
