import requests
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

class MIHortonWildflowerRanchNowScraper(BaseScraper):
    URL = "https://www.mihomes.com/new-homes/texas/dallas-fort-worth-metroplex/quick-move-in-homes?community=The%20Preserve"
    
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
        return str(match.group(1)) if match else "1"

    def get_status(self, container):
        """Extract the status of the home."""
        container_text = container.get_text().lower()
        if "sold" in container_text:
            return "sold"
        elif "available" in container_text or "move-in" in container_text:
            return "available"
        return "available"

    def get_plan_number(self, container):
        """Extract plan number from the container."""
        container_text = container.get_text()
        plan_match = re.search(r'plan\s*(\d+)', container_text, re.IGNORECASE)
        return plan_match.group(1) if plan_match else None

    def get_mls_number(self, container):
        """Extract MLS number if available."""
        container_text = container.get_text()
        mls_match = re.search(r'mls[:\s]*(\d+)', container_text, re.IGNORECASE)
        return mls_match.group(1) if mls_match else None

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[MIHortonWildflowerRanchNowScraper] Fetching URL: {self.URL}")
            
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
            print(f"[MIHortonWildflowerRanchNowScraper] Waiting for content to load...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "home-card"))
            )
            
            # Scroll to load more content (in case of lazy loading)
            print(f"[MIHortonWildflowerRanchNowScraper] Scrolling to load more content...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Look for "Show More" or similar buttons and click them
            try:
                show_more_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Show More') or contains(text(), 'Load More') or contains(text(), 'View All') or contains(text(), 'See More')]")
                for button in show_more_buttons:
                    try:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(2)
                        print(f"[MIHortonWildflowerRanchNowScraper] Clicked 'Show More' button")
                    except:
                        pass
            except:
                pass
            
            # Get the page source after JavaScript execution and scrolling
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all home cards using the correct CSS classes
            home_cards = soup.find_all('div', class_='home-card')
            
            print(f"[MIHortonWildflowerRanchNowScraper] Found {len(home_cards)} home cards")
            
            listings = []
            
            for idx, card in enumerate(home_cards):
                try:
                    # Extract address from home-card-name
                    address_elem = card.find('p', class_='home-card-name')
                    address = address_elem.get_text(strip=True) if address_elem else None
                    
                    if not address:
                        print(f"[MIHortonWildflowerRanchNowScraper] Skipping card {idx+1}: No address found")
                        continue
                    
                    # Extract price from home-card-price-new (current price)
                    price_elem = card.find('span', class_='home-card-price-new')
                    if not price_elem:
                        price_elem = card.find('span', class_='home-card-price')
                    price_text = price_elem.get_text(strip=True) if price_elem else ""
                    price = self.parse_price(price_text)
                    
                    if not price:
                        print(f"[MIHortonWildflowerRanchNowScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract property details from home-card-meta
                    meta_divs = card.find_all('div', class_='home-card-meta')
                    beds = None
                    baths = None
                    sqft = None
                    stories = "1"  # Default
                    
                    for meta_div in meta_divs:
                        meta_text = meta_div.get_text(strip=True)
                        
                        # Look for beds
                        beds_match = re.search(r'Bed\s*(\d+)', meta_text, re.IGNORECASE)
                        if beds_match:
                            beds = beds_match.group(1)
                        
                        # Look for baths
                        baths_match = re.search(r'Bath\s*(\d+(?:\.\d+)?)', meta_text, re.IGNORECASE)
                        if baths_match:
                            baths = baths_match.group(1)
                        
                        # Look for sqft
                        sqft_match = re.search(r'Sq\s*Ft\s*([\d,]+)', meta_text, re.IGNORECASE)
                        if sqft_match:
                            sqft = self.parse_sqft(sqft_match.group(1))
                    
                    # Skip if missing essential details
                    if not all([beds, baths, sqft]):
                        print(f"[MIHortonWildflowerRanchNowScraper] Skipping card {idx+1}: Missing property details (beds: {beds}, baths: {baths}, sqft: {sqft})")
                        continue
                    
                    # Get additional details
                    status = "available"  # All QMI listings are available
                    plan_number = self.get_plan_number(card)
                    mls_number = self.get_mls_number(card)
                    
                    # Extract property link if available
                    link_elem = card.find('a', href=True)
                    property_url = link_elem.get('href') if link_elem else None
                    if property_url and not property_url.startswith('http'):
                        property_url = f"https://www.mihomes.com{property_url}"
                    
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
                        "company": "MI Horton",
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
                    
                    print(f"[MIHortonWildflowerRanchNowScraper] Property {idx+1}: {plan_data['plan_name']} - ${price:,} - {sqft:,} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[MIHortonWildflowerRanchNowScraper] Error processing property {idx+1}: {e}")
                    continue
            
            print(f"[MIHortonWildflowerRanchNowScraper] Successfully processed {len(listings)} properties")
            return listings
            
        except Exception as e:
            print(f"[MIHortonWildflowerRanchNowScraper] Error: {e}")
            return []
        finally:
            if driver:
                driver.quit()
