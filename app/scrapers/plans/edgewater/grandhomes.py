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


class GrandHomesEdgewaterPlanScraper(BaseScraper):
    # URLs to scrape - Monterra will be treated as EdgeWater
    URLS = [
        "https://www.grandhomes.com/community/edgewater/115/",
        "https://www.grandhomes.com/community/monterra/121/"
    ]
    
    def parse_price(self, text):
        """Extract price from text, handling spaces in price strings like '$835, 589'."""
        # Remove spaces and dollar signs, then extract digits and commas
        cleaned_text = text.replace(" ", "").replace("$", "")
        match = re.search(r'([\d,]+)', cleaned_text)
        if match:
            # Remove commas and convert to int
            price_str = match.group(1).replace(",", "")
            try:
                return int(price_str)
            except ValueError:
                return None
        return None

    def parse_sqft_range(self, text):
        """Extract square footage range from text like '1895-2350' or '2465 - 3016'."""
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

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[GrandHomesEdgewaterPlanScraper] Starting to fetch GrandHomes plans for Edgewater")
            
            # Setup Chrome options for Cloudflare protection
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            all_plans = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            for url in self.URLS:
                try:
                    print(f"[GrandHomesEdgewaterPlanScraper] Fetching URL: {url}")
                    driver.get(url)
                    
                    # Wait for the page to load and content to be populated
                    print(f"[GrandHomesEdgewaterPlanScraper] Waiting for page to load...")
                    time.sleep(10)
                    
                    # Scroll to trigger content loading
                    print(f"[GrandHomesEdgewaterPlanScraper] Scrolling to trigger content loading...")
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(5)
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(2)
                    
                    # Wait for "Available Floor Plans" section
                    wait = WebDriverWait(driver, 20)
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h4.BannerHeadingH4")))
                    except:
                        print(f"[GrandHomesEdgewaterPlanScraper] Waiting for content...")
                        time.sleep(5)
                    
                    # Get the page source after JavaScript has loaded
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # Find the "Available Floor Plans" section
                    floor_plans_heading = soup.find('h4', class_='BannerHeadingH4', string=re.compile('Available Floor Plans', re.I))
                    if not floor_plans_heading:
                        print(f"[GrandHomesEdgewaterPlanScraper] No 'Available Floor Plans' section found for {url}")
                        continue
                    
                    # Find the container with plan listings
                    container = floor_plans_heading.find_next('div', class_='row')
                    if not container:
                        # Try to find any row container after the heading
                        parent = floor_plans_heading.parent
                        container = parent.find('div', class_='row')
                    
                    if not container:
                        print(f"[GrandHomesEdgewaterPlanScraper] No container found for {url}")
                        continue
                    
                    # Find all plan listing divs
                    plan_listings = container.find_all('div', class_=lambda x: x and 'col-xs-12' in x and 'col-sm-4' in x and 'col-md-4' in x)
                    print(f"[GrandHomesEdgewaterPlanScraper] Found {len(plan_listings)} plan listings in {url}")
                    
                    for idx, listing in enumerate(plan_listings):
                        try:
                            # Extract plan name
                            plan_name_elem = listing.find('strong')
                            if not plan_name_elem:
                                continue
                            
                            plan_name = plan_name_elem.get_text(strip=True)
                            if not plan_name:
                                continue
                            
                            # Check for duplicate plan names
                            if plan_name in seen_plan_names:
                                print(f"[GrandHomesEdgewaterPlanScraper] Skipping duplicate plan: {plan_name}")
                                continue
                            seen_plan_names.add(plan_name)
                            
                            # Extract details from span
                            details_span = listing.find('span', style='font-size:13px;')
                            if not details_span:
                                continue
                            
                            # Extract price - look for "Priced From:" followed by price
                            price = None
                            details_text = details_span.get_text()
                            
                            # Try to find price after "Priced From:" - handle spaces in price like "$835, 589"
                            price_match = re.search(r'Priced From:\s*\$?([\d,\s]+)', details_text)
                            if price_match:
                                price_text = price_match.group(1).strip()
                                price = self.parse_price(price_text)
                            
                            if not price:
                                # Try alternative: find any price pattern with spaces after "Priced From:"
                                price_match = re.search(r'Priced From:.*?\$([\d,\s]+)', details_text, re.DOTALL)
                                if price_match:
                                    price_text = price_match.group(1).strip()
                                    price = self.parse_price(price_text)
                            
                            if not price:
                                # Fallback: find any price in the span
                                price_match = re.search(r'\$([\d,\s]+)', details_text)
                                if price_match:
                                    price_text = price_match.group(1).strip()
                                    price = self.parse_price(price_text)
                            
                            # Extract square footage range - look for "Sq Ft Apx:" followed by range
                            sqft = None
                            sqft_match = re.search(r'Sq Ft Apx:\s*([\d\s,-]+)', details_text)
                            if sqft_match:
                                sqft_text = sqft_match.group(1).strip()
                                sqft = self.parse_sqft_range(sqft_text)
                            
                            if not sqft:
                                # Try alternative: find any range pattern
                                sqft_match = re.search(r'(\d+(?:,\d+)?)\s*-\s*(\d+(?:,\d+)?)', details_text)
                                if sqft_match:
                                    sqft = self.parse_sqft_range(sqft_match.group(0))
                            
                            if not price or not sqft:
                                print(f"[GrandHomesEdgewaterPlanScraper] Skipping plan {idx+1}: Missing price or sqft")
                                continue
                            
                            # Extract image URL
                            image_url = ""
                            img_tag = listing.find('img', class_='img-thumbnail')
                            if img_tag and img_tag.get('src'):
                                img_src = img_tag['src']
                                if img_src.startswith('/'):
                                    image_url = f"https://www.grandhomes.com{img_src}"
                                else:
                                    image_url = img_src
                            
                            # Extract detail link
                            detail_link = ""
                            link_tag = listing.find('a', href=re.compile('/plan/'))
                            if link_tag and link_tag.get('href'):
                                href = link_tag['href']
                                if href.startswith('/'):
                                    detail_link = f"https://www.grandhomes.com{href}"
                                else:
                                    detail_link = href
                            
                            # Calculate price per sqft
                            price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                            
                            # Default stories (most plans are 2-story)
                            stories = "2"
                            
                            plan_data = {
                                "price": price,
                                "sqft": sqft,
                                "stories": stories,
                                "price_per_sqft": price_per_sqft,
                                "plan_name": plan_name,
                                "company": "GrandHomes",
                                "community": "Edgewater",
                                "type": "plan",
                                "beds": "",  # Not available in the HTML provided
                                "baths": "",  # Not available in the HTML provided
                                "address": plan_name,  # Use plan name as address for plans
                                "original_price": None,
                                "price_cut": "",
                                "status": "",
                                "mls": "",
                                "sub_community": "",
                                "image_url": image_url,
                                "detail_link": detail_link,
                                "garage": ""
                            }
                            
                            print(f"[GrandHomesEdgewaterPlanScraper] Plan {idx+1}: {plan_name} - ${price:,} - {sqft} sqft")
                            all_plans.append(plan_data)
                            
                        except Exception as e:
                            print(f"[GrandHomesEdgewaterPlanScraper] Error processing plan {idx+1} from {url}: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
                
                except Exception as e:
                    print(f"[GrandHomesEdgewaterPlanScraper] Error fetching {url}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[GrandHomesEdgewaterPlanScraper] Successfully processed {len(all_plans)} plans")
            return all_plans
            
        except Exception as e:
            print(f"[GrandHomesEdgewaterPlanScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                driver.quit()

