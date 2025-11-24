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

class PerryHomesBrookvilleNowScraper(BaseScraper):
    URL = "https://www.perryhomes.com/new-homes?city=Dallas+-+Fort+Worth&community=Devonshire"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        # Handle both current price and original price
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_original_price(self, text):
        """Extract original price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "3" and "3.5" formats
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract garage capacity from text."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def get_status(self, container):
        """Extract the status of the home."""
        status_div = container.find('div', class_='grid h-[2.4rem] w-fit place-items-center rounded-full border-[0.1rem] font-body font-medium uppercase subpixel-antialiased px-[1rem] text-[1.2rem] sm:h-[1.632rem] sm:px-[0.68em] sm:text-[0.8rem] md:h-[2.4rem] md:px-[1rem] md:text-[1.2rem] text-chipDefaultTitle bg-chipDefaultBg border-chipDefaultBorder')
        if status_div:
            status_text = status_div.get_text(strip=True).lower()
            if 'move-in ready' in status_text:
                return "move-in ready"
            elif 'under construction' in status_text:
                return "under construction"
            elif 'coming soon' in status_text:
                return "coming soon"
        return "unknown"

    def get_price_cut(self, container):
        """Extract price cut information if available."""
        # Look for original price that's crossed out
        original_price_div = container.find('div', class_='sm:text-[1.0836rem] md:text-[1.6rem] font-body text-[1.6rem] font-extralight line-through')
        if original_price_div:
            original_price = self.parse_original_price(original_price_div.get_text())
            current_price_div = container.find('div', class_='font-headline font-normal text-headlineColor')
            if current_price_div:
                current_price = self.parse_price(current_price_div.get_text())
                if original_price and current_price:
                    price_cut = original_price - current_price
                    return str(price_cut)
        return ""

    def fetch_plans(self) -> List[Dict]:
        """
        Fetch "now" (available homes) information from Perry Homes using Selenium
        """
        print(f"[PerryHomesBrookvilleNowScraper] Fetching URL: {self.URL}")
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(self.URL)
            
            # Wait for the page to load and content to be populated
            print(f"[PerryHomesBrookvilleNowScraper] Waiting for page to load...")
            time.sleep(10)
            
            # Scroll to trigger content loading
            print(f"[PerryHomesBrookvilleNowScraper] Scrolling to trigger content loading...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Wait for home listings to be loaded
            wait = WebDriverWait(driver, 20)
            try:
                # Try to find li elements with id attribute
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li[id]")))
            except:
                print(f"[PerryHomesBrookvilleNowScraper] Waiting for content...")
                time.sleep(5)
            
            # Get the page source after JavaScript has loaded
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            # Find all home listings - Perry Homes uses li elements with id attribute
            # Try multiple selectors to find listings
            home_listings = soup.find_all('li', id=True)
            if not home_listings:
                # Try alternative: look for any li elements
                home_listings = soup.find_all('li')
                print(f"[PerryHomesBrookvilleNowScraper] Found {len(home_listings)} li elements (no id filter)")
            
            # Debug: Print page structure
            print(f"[PerryHomesBrookvilleNowScraper] Found {len(home_listings)} home listings")
            if home_listings:
                # Print first listing structure for debugging
                first_listing_html = str(home_listings[0])[:500] if home_listings[0] else "No listing"
                print(f"[PerryHomesBrookvilleNowScraper] First listing sample: {first_listing_html}")
            else:
                # Debug: Check what's actually on the page
                all_divs = soup.find_all('div', limit=10)
                print(f"[PerryHomesBrookvilleNowScraper] Debug: Found {len(all_divs)} divs (showing first 10)")
                for i, div in enumerate(all_divs[:5]):
                    div_classes = div.get('class', [])
                    div_id = div.get('id', '')
                    print(f"  Div {i+1}: id='{div_id}', classes={div_classes[:3] if div_classes else 'none'}")
            
            for idx, listing in enumerate(home_listings):
                try:
                    print(f"[PerryHomesBrookvilleNowScraper] Processing listing {idx+1}")
                    
                    # Extract address - try multiple approaches
                    address = None
                    
                    # Method 1: Look for div with address pattern
                    address_div = listing.find('div', string=re.compile(r'^\d+.*Lane|Drive|Street|Avenue|Road'))
                    if address_div:
                        address = address_div.get_text(strip=True)
                    
                    # Method 2: Search in all divs for address pattern
                    if not address:
                        all_divs = listing.find_all('div')
                        for div in all_divs:
                            div_text = div.get_text(strip=True)
                            address_match = re.search(r'(\d+\s+[A-Za-z\s]+(?:Lane|Drive|Street|Avenue|Road|Court|Trail|Way))', div_text)
                            if address_match:
                                address = address_match.group(1).strip()
                                break
                    
                    # Method 3: Search entire listing text
                    if not address:
                        listing_text = listing.get_text()
                        address_match = re.search(r'(\d+\s+[A-Za-z\s]+(?:Lane|Drive|Street|Avenue|Road|Court|Trail|Way))', listing_text)
                        if address_match:
                            address = address_match.group(1).strip()
                    
                    if not address:
                        print(f"[PerryHomesBrookvilleNowScraper] Skipping listing {idx+1}: No address found")
                        # Debug: print listing text sample
                        listing_text_sample = listing.get_text()[:200] if listing else "No listing"
                        print(f"[PerryHomesBrookvilleNowScraper] Listing text sample: {listing_text_sample}")
                        continue
                    
                    if not address:
                        print(f"[PerryHomesBrookvilleNowScraper] Skipping listing {idx+1}: Empty address")
                        continue
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[PerryHomesBrookvilleNowScraper] Skipping listing {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract current price
                    price_div = listing.find('div', class_='font-headline font-normal text-headlineColor')
                    if not price_div:
                        print(f"[PerryHomesBrookvilleNowScraper] Skipping listing {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_div.get_text())
                    if not current_price:
                        print(f"[PerryHomesBrookvilleNowScraper] Skipping listing {idx+1}: No current price found")
                        continue
                    
                    # Extract plan name - try multiple approaches
                    plan_name = ""
                    
                    # Method 1: Look for heading or title elements
                    heading = listing.find('h1') or listing.find('h2') or listing.find('h3') or listing.find('h4')
                    if heading:
                        heading_text = heading.get_text(strip=True)
                        # Skip generic headings
                        if heading_text and len(heading_text) > 3 and 'perry' not in heading_text.lower():
                            plan_name = heading_text
                    
                    # Method 2: Extract from address (e.g., "2723 Kirkhill Lane" -> "2723 Kirkhill")
                    if not plan_name:
                        address_match = re.search(r'(\d+\s+[A-Za-z]+)', address)
                        if address_match:
                            plan_name = address_match.group(1)
                    
                    # Method 3: Look for links with plan-like text
                    if not plan_name:
                        links = listing.find_all('a', href=True)
                        for link in links:
                            link_text = link.get_text(strip=True)
                            # Skip if it's just a community name or generic text
                            if link_text and len(link_text) > 3 and 'devonshire' not in link_text.lower() and 'perry' not in link_text.lower():
                                # Check if it looks like a plan name
                                if re.search(r'\d+', link_text) or len(link_text.split()) <= 3:
                                    plan_name = link_text
                                    break
                    
                    # Fallback: use address as plan name
                    if not plan_name:
                        plan_name = address
                    
                    # Extract beds, baths, sqft, stories, and garage from amenities
                    amenities = listing.find_all('div', class_=lambda x: x and 'flex items-center gap-' in x)
                    beds = ""
                    baths = ""
                    sqft = None
                    stories = ""
                    garage = ""
                    
                    for amenity in amenities:
                        amenity_text = amenity.get_text(strip=True)
                        if 'Beds' in amenity_text:
                            beds = self.parse_beds(amenity_text)
                        elif 'Baths' in amenity_text:
                            baths = self.parse_baths(amenity_text)
                        elif 'Sq. Ft.' in amenity_text:
                            sqft = self.parse_sqft(amenity_text)
                        elif 'Stories' in amenity_text:
                            stories = self.parse_stories(amenity_text)
                        elif 'Cars' in amenity_text:
                            garage = self.parse_garage(amenity_text)
                    
                    if not sqft:
                        print(f"[PerryHomesBrookvilleNowScraper] Skipping listing {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Get status and price cut information
                    status = self.get_status(listing)
                    price_cut = self.get_price_cut(listing)
                    
                    # Determine if it's a quick move-in home
                    is_quick_move_in = status == "move-in ready"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories if stories else "1",
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Perry Homes",
                        "community": "Brookville",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,  # Will be calculated if needed
                        "price_cut": price_cut
                    }
                    
                    # Add additional metadata
                    if status:
                        plan_data["status"] = status
                    if garage:
                        plan_data["garage"] = garage
                    
                    print(f"[PerryHomesBrookvilleNowScraper] Listing {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[PerryHomesBrookvilleNowScraper] Error processing listing {idx+1}: {e}")
                    continue
            
            print(f"[PerryHomesBrookvilleNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[PerryHomesBrookvilleNowScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                driver.quit()
