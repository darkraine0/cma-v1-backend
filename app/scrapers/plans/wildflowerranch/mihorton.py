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

class MIHortonWildflowerRanchPlanScraper(BaseScraper):
    URL = "https://www.mihomes.com/new-homes/texas/dallas-fort-worth-metroplex/plans-ready-to-build?community=The%20Preserve"
    
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

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[MIHortonWildflowerRanchPlanScraper] Fetching URL: {self.URL}")
            
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
            
            # Wait for content to load - try different selectors
            print(f"[MIHortonWildflowerRanchPlanScraper] Waiting for content to load...")
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "is-plan-card"))
                )
            except:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "search-card"))
                    )
                except:
                    print(f"[MIHortonWildflowerRanchPlanScraper] No specific cards found, proceeding with page content")
            
            # Scroll to load more content (in case of lazy loading)
            print(f"[MIHortonWildflowerRanchPlanScraper] Scrolling to load more content...")
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
                        print(f"[MIHortonWildflowerRanchPlanScraper] Clicked 'Show More' button")
                    except:
                        pass
            except:
                pass
            
            # Get the page source after JavaScript execution and scrolling
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all plan cards using the correct CSS classes (they are article elements, not div)
            plan_cards = soup.find_all('article', class_='is-plan-card')
            
            print(f"[MIHortonWildflowerRanchPlanScraper] Found {len(plan_cards)} plan cards")
            
            listings = []
            
            for idx, card in enumerate(plan_cards):
                try:
                    # First try to extract data from JSON-LD script tag
                    script_tag = card.find('script', type='application/ld+json')
                    plan_name = None
                    price = None
                    beds = None
                    baths = None
                    sqft = None
                    stories = "1"
                    plan_url = None
                    
                    if script_tag and script_tag.string:
                        try:
                            import json
                            json_data = json.loads(script_tag.string)
                            
                            # Extract data from JSON
                            plan_name = json_data.get('name', '')
                            price_str = json_data.get('offers', {}).get('price', '')
                            if price_str:
                                price = int(float(price_str))
                            
                            # Extract from description or other fields
                            description = json_data.get('description', '')
                            if description:
                                # Look for beds in description
                                beds_match = re.search(r'(\d+(?:&mdash;|–|-)\d+|\d+)\s*bedrooms?', description, re.IGNORECASE)
                                if beds_match:
                                    beds = beds_match.group(1).replace('&mdash;', '-').replace('–', '-')
                                
                                # Look for baths in description
                                baths_match = re.search(r'(\d+(?:\.\d+)?(?:&mdash;|–|-)\d+(?:\.\d+)?|\d+(?:\.\d+)?)\s*bathrooms?', description, re.IGNORECASE)
                                if baths_match:
                                    baths = baths_match.group(1).replace('&mdash;', '-').replace('–', '-')
                                
                                # Look for sqft in description
                                sqft_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:-\d{1,3}(?:,\d{3})*)?)\s*square\s*feet', description, re.IGNORECASE)
                                if sqft_match:
                                    sqft_range = sqft_match.group(1)
                                    # Take the first number in the range
                                    sqft_first = re.search(r'([\d,]+)', sqft_range)
                                    sqft = self.parse_sqft(sqft_first.group(1)) if sqft_first else None
                            
                            # Extract URL
                            plan_url = json_data.get('offers', {}).get('url', '')
                            if plan_url and not plan_url.startswith('http'):
                                plan_url = f"https://www.mihomes.com{plan_url}"
                                
                        except Exception as e:
                            print(f"[MIHortonWildflowerRanchPlanScraper] Error parsing JSON for card {idx+1}: {e}")
                    
                    # If JSON parsing failed or missing data, try HTML extraction
                    if not all([plan_name, price, beds, baths, sqft]):
                        card_text = card.get_text()
                        
                        # Extract plan name from HTML
                        if not plan_name:
                            name_elem = card.find('a', class_='community-card__name')
                            if name_elem:
                                plan_name = name_elem.get_text(strip=True)
                        
                        # Extract price from HTML
                        if not price:
                            price_elem = card.find('span', class_='community-card__meta-value')
                            if price_elem:
                                price = self.parse_price(price_elem.get_text())
                        
                        # Extract other details from HTML
                        if not beds:
                            beds_match = re.search(r'Bed\s*(\d+(?:-\d+)?)', card_text)
                            beds = beds_match.group(1) if beds_match else None
                        
                        if not baths:
                            baths_match = re.search(r'Bath\s*(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)', card_text)
                            baths = baths_match.group(1) if baths_match else None
                        
                        if not sqft:
                            sqft_match = re.search(r'Sq\s*Ft\s*([\d,]+(?:-[\d,]+)?)', card_text)
                            if sqft_match:
                                sqft_range = sqft_match.group(1)
                                sqft_first = re.search(r'([\d,]+)', sqft_range)
                                sqft = self.parse_sqft(sqft_first.group(1)) if sqft_first else None
                        
                        # Extract URL from HTML
                        if not plan_url:
                            link_elem = card.find('a', href=True)
                            if link_elem:
                                plan_url = link_elem.get('href')
                                if plan_url and not plan_url.startswith('http'):
                                    plan_url = f"https://www.mihomes.com{plan_url}"
                    
                    # Skip if missing essential details
                    if not all([plan_name, price, beds, baths, sqft]):
                        print(f"[MIHortonWildflowerRanchPlanScraper] Skipping card {idx+1}: Missing essential details (name: {plan_name}, price: {price}, beds: {beds}, baths: {baths}, sqft: {sqft})")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "MI Horton",
                        "community": "Wildflower Ranch",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",  # Plans don't have addresses
                        "design_number": plan_name,  # Use plan name as design number
                        "url": plan_url
                    }
                    
                    print(f"[MIHortonWildflowerRanchPlanScraper] Plan {idx+1}: {plan_data['plan_name']} - ${price:,} - {sqft:,} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[MIHortonWildflowerRanchPlanScraper] Error processing plan {idx+1}: {e}")
                    continue
            
            print(f"[MIHortonWildflowerRanchPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[MIHortonWildflowerRanchPlanScraper] Error: {e}")
            return []
        finally:
            if driver:
                driver.quit()
