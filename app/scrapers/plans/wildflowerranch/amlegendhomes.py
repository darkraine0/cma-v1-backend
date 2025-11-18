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

class AmericanLegendHomesWildflowerRanchPlanScraper(BaseScraper):
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

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Fetching URL: {self.URL}")
            
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
            print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Waiting for content to load...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "css-zxy9ty"))
            )
            
            # Scroll to load more content (in case of lazy loading)
            print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Scrolling to load more content...")
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
                        print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Clicked 'Show More' button")
                    except:
                        pass
            except:
                pass
            
            # Get the page source after JavaScript execution and scrolling
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all plan cards
            plan_cards = soup.find_all('div', class_='css-zxy9ty', role='group')
            print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Found {len(plan_cards)} plan cards")
            
            # Debug: Print all plan names found
            print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Plan names found:")
            for i, card in enumerate(plan_cards):
                plan_name_elem = card.find('a', class_='flex-fill mr-auto PlanCard_title px-0')
                plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else "Unknown"
                print(f"  {i+1}. {plan_name}")
            
            listings = []
            
            for idx, card in enumerate(plan_cards):
                try:
                    # Extract plan name
                    plan_name_elem = card.find('a', class_='flex-fill mr-auto PlanCard_title px-0')
                    plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else None
                    
                    if not plan_name:
                        print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    # Extract price from the "Starting at" section
                    price_elem = card.find('strong')
                    price_text = price_elem.get_text(strip=True) if price_elem else ""
                    price = self.parse_price(price_text)
                    
                    if not price:
                        print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract property details from the list
                    details_list = card.find('ul', class_='list-unstyled m-0 px-3 d-flex align-items-center justify-content-between PlanCard_list flex-fill')
                    if not details_list:
                        print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Skipping card {idx+1}: No property details found")
                        continue
                    
                    stories = None
                    beds = None
                    baths = None
                    sqft = None
                    
                    list_items = details_list.find_all('li', class_='PlanCard_listItem')
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
                        print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Skipping card {idx+1}: Missing property details (stories: {stories}, beds: {beds}, baths: {baths}, sqft: {sqft})")
                        continue
                    
                    # Extract plan link
                    link_elem = card.find('a', class_='PlanCard_imageWrapper')
                    plan_url = link_elem.get('href') if link_elem else None
                    if plan_url and not plan_url.startswith('http'):
                        plan_url = f"https://www.amlegendhomes.com{plan_url}"
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft else None
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "American Legend Homes",
                        "community": "Wildflower Ranch",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",  # Plans don't have addresses
                        "design_number": plan_name,  # Use plan name as design number
                        "url": plan_url
                    }
                    
                    print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Plan {idx+1}: {plan_data['plan_name']} - ${price:,} - {sqft:,} sqft")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Error processing plan {idx+1}: {e}")
                    continue
            
            print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[AmericanLegendHomesWildflowerRanchPlanScraper] Error: {e}")
            return []
        finally:
            if driver:
                driver.quit()
