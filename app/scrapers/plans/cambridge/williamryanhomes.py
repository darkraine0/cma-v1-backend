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

class WilliamRyanHomesCambridgePlanScraper(BaseScraper):
    URL = "https://www.williamryanhomes.com/dfw/celina/ten-mile-creek"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text (handles 'From $X' format)."""
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

    def parse_garages(self, text):
        """Extract number of garages from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[WilliamRyanHomesCambridgePlanScraper] Fetching URL: {self.URL}")
            
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
            
            # Wait for content to load - wait for floorPlansListContainer
            print(f"[WilliamRyanHomesCambridgePlanScraper] Waiting for content to load...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "floorPlansListContainer"))
            )
            
            # Scroll to load more content
            print(f"[WilliamRyanHomesCambridgePlanScraper] Scrolling to load more content...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Get the page source after JavaScript execution
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find the floor plans container
            plans_container = soup.find('div', id='floorPlansListContainer')
            if not plans_container:
                print(f"[WilliamRyanHomesCambridgePlanScraper] No floor plans container found")
                return []
            
            # Find all plan cards - they are direct children divs with shadow-xl class
            plan_cards = plans_container.find_all('div', class_=lambda x: x and 'shadow-xl' in x and 'duration-250' in x)
            print(f"[WilliamRyanHomesCambridgePlanScraper] Found {len(plan_cards)} plan cards")
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[WilliamRyanHomesCambridgePlanScraper] Processing plan card {idx+1}")
                    
                    # Extract plan name - it's in the second button with font-serif text-[28px]
                    plan_name_buttons = card.find_all('button')
                    plan_name = ""
                    # The plan name is in the second button (index 1) with font-serif class
                    if len(plan_name_buttons) >= 2:
                        span = plan_name_buttons[1].find('span')
                        if span and 'font-serif' in span.get('class', []):
                            plan_name = span.get_text(strip=True)
                    
                    if not plan_name:
                        print(f"[WilliamRyanHomesCambridgePlanScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[WilliamRyanHomesCambridgePlanScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract price - look for "From" text followed by price
                    price_spans = card.find_all('span', class_=lambda x: x and 'font-bold' in x)
                    current_price = None
                    for span in price_spans:
                        text = span.get_text(strip=True)
                        if text.startswith('$'):
                            current_price = self.parse_price(text)
                            if current_price:
                                break
                    
                    if not current_price:
                        print(f"[WilliamRyanHomesCambridgePlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    # Extract plan details (beds, baths, garages, sqft) from grid-cols-4 div
                    grid_div = card.find('div', class_=lambda x: x and 'grid-cols-4' in x)
                    beds = ""
                    baths = ""
                    sqft = None
                    garages = ""
                    
                    if grid_div:
                        detail_divs = grid_div.find_all('div', class_='flex')
                        for detail_div in detail_divs:
                            spans = detail_div.find_all('span')
                            if len(spans) >= 2:
                                value_span = spans[0]  # First span has the number
                                label_span = spans[1]  # Second span has the label
                                
                                value_text = value_span.get_text(strip=True)
                                label_text = label_span.get_text(strip=True)
                                
                                if 'Beds' in label_text:
                                    beds = self.parse_beds(value_text)
                                elif 'Baths' in label_text:
                                    baths = self.parse_baths(value_text)
                                elif 'Garage' in label_text:
                                    garages = self.parse_garages(value_text)
                                elif 'Sq. ft.' in label_text:
                                    sqft = self.parse_sqft(value_text)
                    
                    if not sqft:
                        print(f"[WilliamRyanHomesCambridgePlanScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Extract image URL if available
                    image_url = ""
                    img_tag = card.find('img', alt='cardImage')
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag['src']
                        # Convert relative URL to absolute if needed
                        if image_url.startswith('/'):
                            image_url = f"https://www.williamryanhomes.com{image_url}"
                    
                    # Extract plan detail link
                    detail_link = ""
                    view_link = card.find('a', href=lambda x: x and '/floor-plans/' in x)
                    if view_link and view_link.get('href'):
                        detail_link = view_link['href']
                        # Make it absolute URL if it's relative
                        if detail_link.startswith('/'):
                            detail_link = f"https://www.williamryanhomes.com{detail_link}"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": "1",  # Default to 1 story
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "William Ryan Homes",
                        "community": "Cambridge",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",
                        "original_price": None,
                        "price_cut": "",
                        "image_url": image_url,
                        "detail_link": detail_link,
                        "lot_size": "",
                        "garages": garages
                    }
                    
                    print(f"[WilliamRyanHomesCambridgePlanScraper] Plan {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[WilliamRyanHomesCambridgePlanScraper] Error processing plan card {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[WilliamRyanHomesCambridgePlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[WilliamRyanHomesCambridgePlanScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                driver.quit()

