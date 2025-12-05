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


class GrandHomesEdgewaterNowScraper(BaseScraper):
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

    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'(\d+(?:,\d+)?)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_availability(self, text):
        """Extract availability status from text."""
        if not text:
            return "Available"
        text_lower = text.lower().strip()
        if "now" in text_lower:
            return "Now"
        # Check if it's a date (MM/DD/YYYY format)
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
        if date_match:
            return date_match.group(1)
        return text.strip()

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[GrandHomesEdgewaterNowScraper] Starting to fetch GrandHomes data for Edgewater")
            
            # Setup Chrome options for Cloudflare protection
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            all_listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            for url in self.URLS:
                try:
                    print(f"[GrandHomesEdgewaterNowScraper] Fetching URL: {url}")
                    driver.get(url)
                    
                    # Wait for the page to load and content to be populated
                    print(f"[GrandHomesEdgewaterNowScraper] Waiting for page to load...")
                    time.sleep(10)
                    
                    # Scroll to trigger content loading
                    print(f"[GrandHomesEdgewaterNowScraper] Scrolling to trigger content loading...")
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(5)
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(2)
                    
                    # Wait for "Available Homes" section
                    wait = WebDriverWait(driver, 20)
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h4.BannerHeadingH4")))
                    except:
                        print(f"[GrandHomesEdgewaterNowScraper] Waiting for content...")
                        time.sleep(5)
                    
                    # Get the page source after JavaScript has loaded
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # Find the "Available Homes" section
                    available_homes_heading = soup.find('h4', class_='BannerHeadingH4', string=re.compile('Available Homes', re.I))
                    if not available_homes_heading:
                        print(f"[GrandHomesEdgewaterNowScraper] No 'Available Homes' section found for {url}")
                        continue
                    
                    # Find the container with home listings
                    container = available_homes_heading.find_next('div', class_='row')
                    if not container:
                        # Try to find any row container after the heading
                        parent = available_homes_heading.parent
                        container = parent.find('div', class_='row')
                    
                    if not container:
                        print(f"[GrandHomesEdgewaterNowScraper] No container found for {url}")
                        continue
                    
                    # Find all home listing divs
                    home_listings = container.find_all('div', class_=lambda x: x and 'col-xs-12' in x and 'col-sm-6' in x and 'col-md-4' in x)
                    print(f"[GrandHomesEdgewaterNowScraper] Found {len(home_listings)} home listings in {url}")
                    
                    for idx, listing in enumerate(home_listings):
                        try:
                            # Extract address - first strong tag contains address
                            address_elem = listing.find('strong')
                            if not address_elem:
                                continue
                            
                            # Get all text nodes and br tags
                            address_parts = []
                            for element in address_elem.children:
                                if hasattr(element, 'get_text'):
                                    text = element.get_text(strip=True)
                                    if text:
                                        address_parts.append(text)
                                elif element.name == 'br':
                                    continue
                                else:
                                    text = str(element).strip()
                                    if text and not text.startswith('<'):
                                        address_parts.append(text)
                            
                            # If we didn't get parts from children, try get_text with separator
                            if not address_parts:
                                address_text = address_elem.get_text(separator='\n', strip=True)
                                address_parts = [line.strip() for line in address_text.split('\n') if line.strip()]
                            
                            if len(address_parts) < 2:
                                continue
                            
                            address = f"{address_parts[0]}, {address_parts[1]}"
                            
                            # Check for duplicate addresses
                            if address in seen_addresses:
                                print(f"[GrandHomesEdgewaterNowScraper] Skipping duplicate address: {address}")
                                continue
                            seen_addresses.add(address)
                            
                            # Extract details from span
                            details_span = listing.find('span', style='font-size:13px;')
                            if not details_span:
                                continue
                            
                            # Extract floorplan
                            plan_name = ""
                            plan_link = details_span.find('a', href=re.compile('/inventory/'))
                            if plan_link:
                                plan_name = plan_link.get_text(strip=True)
                            
                            # Extract sale price - look for "Sale Price:" followed by price
                            price = None
                            details_text = details_span.get_text()
                            
                            # Try to find price after "Sale Price:" - handle spaces in price like "$835, 589"
                            price_match = re.search(r'Sale Price:\s*\$?([\d,\s]+)', details_text)
                            if price_match:
                                price_text = price_match.group(1).strip()
                                price = self.parse_price(price_text)
                            
                            if not price:
                                # Try alternative: find any price pattern with spaces after "Sale Price:"
                                price_match = re.search(r'Sale Price:.*?\$([\d,\s]+)', details_text, re.DOTALL)
                                if price_match:
                                    price_text = price_match.group(1).strip()
                                    price = self.parse_price(price_text)
                            
                            if not price:
                                # Fallback: find any price in the span
                                price_match = re.search(r'\$([\d,\s]+)', details_text)
                                if price_match:
                                    price_text = price_match.group(1).strip()
                                    price = self.parse_price(price_text)
                            
                            # Extract square footage - look for "Sq Ft Apx:" followed by number
                            sqft = None
                            sqft_match = re.search(r'Sq Ft Apx:\s*(\d+(?:,\d+)?)', details_text)
                            if sqft_match:
                                sqft = self.parse_sqft(sqft_match.group(1))
                            
                            if not sqft:
                                # Try alternative: find any number that looks like sqft (4 digits)
                                sqft_match = re.search(r'\b(\d{4,})\b', details_text)
                                if sqft_match:
                                    potential_sqft = int(sqft_match.group(1).replace(",", ""))
                                    # Reasonable sqft range check
                                    if 1000 <= potential_sqft <= 10000:
                                        sqft = potential_sqft
                            
                            # Extract availability - look for "Availability:" followed by status
                            status = "Available"
                            availability_match = re.search(r'Availability:\s*(.+?)(?:\s*</span>|$)', details_text, re.DOTALL)
                            if availability_match:
                                availability_text = availability_match.group(1).strip()
                                status = self.parse_availability(availability_text)
                            
                            if not price or not sqft:
                                print(f"[GrandHomesEdgewaterNowScraper] Skipping listing {idx+1}: Missing price or sqft")
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
                            link_tag = listing.find('a', href=re.compile('/inventory/'))
                            if link_tag and link_tag.get('href'):
                                href = link_tag['href']
                                if href.startswith('/'):
                                    detail_link = f"https://www.grandhomes.com{href}"
                                else:
                                    detail_link = href
                            
                            # Calculate price per sqft
                            price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                            
                            # Default stories (most homes are 2-story)
                            stories = "2"
                            
                            listing_data = {
                                "price": price,
                                "sqft": sqft,
                                "stories": stories,
                                "price_per_sqft": price_per_sqft,
                                "plan_name": plan_name or address,
                                "company": "GrandHomes",
                                "community": "Edgewater",
                                "type": "now",
                                "beds": "",  # Not available in the HTML provided
                                "baths": "",  # Not available in the HTML provided
                                "address": address,
                                "original_price": None,
                                "price_cut": "",
                                "status": status,
                                "mls": "",
                                "sub_community": "",
                                "image_url": image_url,
                                "detail_link": detail_link,
                                "garage": ""
                            }
                            
                            print(f"[GrandHomesEdgewaterNowScraper] Home {idx+1}: {address} - {plan_name} - ${price:,} - {sqft} sqft - {status}")
                            all_listings.append(listing_data)
                            
                        except Exception as e:
                            print(f"[GrandHomesEdgewaterNowScraper] Error processing listing {idx+1} from {url}: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
                
                except Exception as e:
                    print(f"[GrandHomesEdgewaterNowScraper] Error fetching {url}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[GrandHomesEdgewaterNowScraper] Successfully processed {len(all_listings)} homes")
            return all_listings
            
        except Exception as e:
            print(f"[GrandHomesEdgewaterNowScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                driver.quit()

