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

class PerryHomesBrookvillePlanScraper(BaseScraper):
    URL = "https://www.perryhomes.com/new-homes?city=Dallas+-+Fort+Worth&community=Devonshire"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract starting price from text."""
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

    def fetch_plans(self) -> List[Dict]:
        """
        Fetch plan information from Perry Homes using Selenium
        """
        print(f"[PerryHomesBrookvillePlanScraper] Fetching URL: {self.URL}")
        
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
            print(f"[PerryHomesBrookvillePlanScraper] Waiting for page to load...")
            time.sleep(10)
            
            # Scroll to trigger content loading
            print(f"[PerryHomesBrookvillePlanScraper] Scrolling to trigger content loading...")
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
                print(f"[PerryHomesBrookvillePlanScraper] Waiting for content...")
                time.sleep(5)
            
            # Get the page source after JavaScript has loaded
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            plans = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all home listings to extract floor plan information
            # Try multiple selectors to find listings
            home_listings = soup.find_all('li', id=True)
            if not home_listings:
                # Try alternative: look for any li elements
                home_listings = soup.find_all('li')
                print(f"[PerryHomesBrookvillePlanScraper] Found {len(home_listings)} li elements (no id filter)")
            
            # Debug: Print page structure
            print(f"[PerryHomesBrookvillePlanScraper] Found {len(home_listings)} home listings")
            if home_listings:
                # Print first listing structure for debugging
                first_listing_html = str(home_listings[0])[:500] if home_listings[0] else "No listing"
                print(f"[PerryHomesBrookvillePlanScraper] First listing sample: {first_listing_html}")
            else:
                # Debug: Check what's actually on the page
                all_divs = soup.find_all('div', limit=10)
                print(f"[PerryHomesBrookvillePlanScraper] Debug: Found {len(all_divs)} divs (showing first 10)")
                for i, div in enumerate(all_divs[:5]):
                    div_classes = div.get('class', [])
                    div_id = div.get('id', '')
                    print(f"  Div {i+1}: id='{div_id}', classes={div_classes[:3] if div_classes else 'none'}")
            
            for idx, listing in enumerate(home_listings):
                try:
                    print(f"[PerryHomesBrookvillePlanScraper] Processing listing {idx+1}")
                    
                    # Skip listings with specific addresses (those are "now" listings, not floor plans)
                    address_div = listing.find('div', string=re.compile(r'^\d+.*Lane|Drive|Street|Avenue|Road|Court|Trail|Way'))
                    if address_div:
                        # This is a specific home listing, not a floor plan
                        print(f"[PerryHomesBrookvillePlanScraper] Skipping listing {idx+1}: Has specific address (this is a 'now' listing)")
                        continue
                    
                    # Extract plan name - try multiple approaches
                    plan_name = ""
                    
                    # Method 1: Look for heading or title elements
                    heading = listing.find('h1') or listing.find('h2') or listing.find('h3') or listing.find('h4')
                    if heading:
                        plan_name = heading.get_text(strip=True)
                    
                    # Method 2: Look for links with plan-like text
                    if not plan_name:
                        links = listing.find_all('a', href=True)
                        for link in links:
                            link_text = link.get_text(strip=True)
                            # Skip if it's just a community name or generic text
                            if link_text and len(link_text) > 3 and 'devonshire' not in link_text.lower() and 'perry' not in link_text.lower():
                                # Check if it looks like a plan name (contains numbers or specific patterns)
                                if re.search(r'\d+', link_text) or len(link_text.split()) <= 3:
                                    plan_name = link_text
                                    break
                    
                    # Method 3: Extract from address if available (for plans that have addresses)
                    if not plan_name:
                        address_div = listing.find('div', string=re.compile(r'^\d+.*Lane|Drive|Street|Avenue|Road'))
                        if address_div:
                            address = address_div.get_text(strip=True)
                            # Extract plan name from address (e.g., "2723 Kirkhill Lane" -> "2723 Kirkhill")
                            address_match = re.search(r'(\d+\s+[A-Za-z]+)', address)
                            if address_match:
                                plan_name = address_match.group(1)
                    
                    # Method 4: Look for any div with plan-like text
                    if not plan_name:
                        all_divs = listing.find_all('div')
                        for div in all_divs:
                            div_text = div.get_text(strip=True)
                            # Look for patterns like "Plan 123" or model names
                            plan_match = re.search(r'(?:Plan|Model|Design)\s*[:\-]?\s*([A-Za-z0-9\s]+)', div_text, re.IGNORECASE)
                            if plan_match:
                                potential_name = plan_match.group(1).strip()
                                if len(potential_name) > 2:
                                    plan_name = potential_name
                                    break
                    
                    # Method 5: Use a combination of specs as plan identifier if no name found
                    if not plan_name:
                        # Extract specs first to create a plan identifier
                        amenities = listing.find_all('div', class_=lambda x: x and 'flex items-center gap-' in x)
                        beds = ""
                        sqft = None
                        for amenity in amenities:
                            amenity_text = amenity.get_text(strip=True)
                            if 'Beds' in amenity_text:
                                beds = self.parse_beds(amenity_text)
                            elif 'Sq. Ft.' in amenity_text:
                                sqft = self.parse_sqft(amenity_text)
                        
                        if beds and sqft:
                            plan_name = f"{beds} Bed {sqft} SqFt Plan"
                        else:
                            # Debug: print listing content to understand structure
                            listing_text_sample = listing.get_text()[:300] if listing else "No listing"
                            print(f"[PerryHomesBrookvillePlanScraper] Skipping listing {idx+1}: No plan name found")
                            print(f"[PerryHomesBrookvillePlanScraper] Listing text sample: {listing_text_sample}")
                            continue
                    
                    if not plan_name:
                        print(f"[PerryHomesBrookvillePlanScraper] Skipping listing {idx+1}: Empty plan name")
                        # Debug: print listing HTML snippet
                        listing_html = str(listing)[:500] if listing else "No listing"
                        print(f"[PerryHomesBrookvillePlanScraper] Listing HTML sample: {listing_html}")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[PerryHomesBrookvillePlanScraper] Skipping listing {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract starting price (use current price as starting price for floor plans)
                    price_div = listing.find('div', class_='font-headline font-normal text-headlineColor')
                    if not price_div:
                        print(f"[PerryHomesBrookvillePlanScraper] Skipping listing {idx+1}: No price found")
                        continue
                    
                    starting_price = self.parse_price(price_div.get_text())
                    if not starting_price:
                        print(f"[PerryHomesBrookvillePlanScraper] Skipping listing {idx+1}: No starting price found")
                        continue
                    
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
                        print(f"[PerryHomesBrookvillePlanScraper] Skipping listing {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                    
                    plan_data = {
                        "price": starting_price,
                        "sqft": sqft,
                        "stories": stories if stories else "1",
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Perry Homes",
                        "community": "Brookville",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",  # Floor plans don't have specific addresses
                        "original_price": None,
                        "price_cut": ""
                    }
                    
                    # Add additional metadata
                    if garage:
                        plan_data["garage"] = garage
                    
                    print(f"[PerryHomesBrookvillePlanScraper] Floor Plan {idx+1}: {plan_data}")
                    plans.append(plan_data)
                    
                except Exception as e:
                    print(f"[PerryHomesBrookvillePlanScraper] Error processing listing {idx+1}: {e}")
                    continue
            
            print(f"[PerryHomesBrookvillePlanScraper] Successfully processed {len(plans)} floor plans")
            return plans
            
        except Exception as e:
            print(f"[PerryHomesBrookvillePlanScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                driver.quit()
