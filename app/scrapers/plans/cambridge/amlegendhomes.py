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

class AmericanLegendHomesCambridgePlanScraper(BaseScraper):
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

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[AmericanLegendHomesCambridgePlanScraper] Fetching URL: {self.URL}")
            
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
            print(f"[AmericanLegendHomesCambridgePlanScraper] Waiting for content to load...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "css-zxy9ty"))
            )
            
            # Scroll to load more content and make buttons visible
            print(f"[AmericanLegendHomesCambridgePlanScraper] Scrolling to load more content...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Click "Load More Plans" button until it disappears or no more items load
            max_clicks = 10  # Safety limit
            click_count = 0
            while click_count < max_clicks:
                try:
                    load_more_button = driver.find_element(By.CLASS_NAME, "CommunityPlans_load")
                    if load_more_button and load_more_button.is_displayed():
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Clicking 'Load More Plans' button (attempt {click_count + 1})...")
                        driver.execute_script("arguments[0].click();", load_more_button)
                        time.sleep(3)  # Wait for content to load
                        click_count += 1
                    else:
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Load More button not visible, stopping")
                        break
                except Exception as e:
                    print(f"[AmericanLegendHomesCambridgePlanScraper] No more 'Load More Plans' button found: {e}")
                    break
            
            if click_count > 0:
                print(f"[AmericanLegendHomesCambridgePlanScraper] Clicked 'Load More Plans' button {click_count} times")
            
            # Scroll again to ensure all content is loaded
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Get the page source after JavaScript execution and clicking
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all plan cards - they have the class "css-zxy9ty" and contain plan information
            plan_cards = soup.find_all('div', class_='css-zxy9ty')
            print(f"[AmericanLegendHomesCambridgePlanScraper] Found {len(plan_cards)} plan cards")
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[AmericanLegendHomesCambridgePlanScraper] Processing plan card {idx+1}")
                    
                    # Extract plan name and number
                    title_link = card.find('a', class_='PlanCard_title')
                    if not title_link:
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Skipping card {idx+1}: No title link found")
                        continue
                    
                    plan_name = title_link.get_text(strip=True)
                    if not plan_name:
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Skipping card {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract price - look for the strong tag with price
                    price_strong = card.find('strong')
                    if not price_strong:
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_strong.get_text())
                    if not current_price:
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract plan details (stories, beds, baths, sqft) from the PlanCard_list
                    detail_list = card.find('ul', class_='PlanCard_list')
                    beds = ""
                    baths = ""
                    stories = ""
                    sqft = None
                    
                    if detail_list:
                        detail_items = detail_list.find_all('li', class_='PlanCard_listItem')
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
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Extract image URL if available
                    image_wrapper = card.find('a', class_='PlanCard_imageWrapper')
                    image_url = ""
                    if image_wrapper:
                        img_tag = image_wrapper.find('img')
                        if img_tag and img_tag.get('src'):
                            image_url = img_tag['src']
                    
                    # Extract plan detail link
                    detail_link = ""
                    detail_link_tag = card.find('a', class_='PlanCard_linkDetail')
                    if detail_link_tag and detail_link_tag.get('href'):
                        detail_link = detail_link_tag['href']
                        # Make it absolute URL if it's relative
                        if detail_link.startswith('/'):
                            detail_link = f"https://www.amlegendhomes.com{detail_link}"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories or "1",
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "American Legend Homes",
                        "community": "Cambridge",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",
                        "original_price": None,
                        "price_cut": "",
                        "image_url": image_url,
                        "detail_link": detail_link
                    }
                    
                    print(f"[AmericanLegendHomesCambridgePlanScraper] Plan {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[AmericanLegendHomesCambridgePlanScraper] Error processing plan card {idx+1}: {e}")
                    continue
            
            print(f"[AmericanLegendHomesCambridgePlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[AmericanLegendHomesCambridgePlanScraper] Error: {e}")
            return []
        finally:
            if driver:
                driver.quit()
