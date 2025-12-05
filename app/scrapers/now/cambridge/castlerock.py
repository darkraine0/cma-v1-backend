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


class CastlerockCambridgeNowScraper(BaseScraper):
    URL = "https://www.c-rock.com/community/texas/dallas/green_meadows?splitPageTabBar=2"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text (can be decimal like 2.5)."""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract number of garage spaces from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def fetch_plans(self) -> List[Dict]:
        driver = None
        try:
            print(f"[CastlerockCambridgeNowScraper] Fetching URL: {self.URL}")
            
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(self.URL)
            
            # Wait for the page to load
            print(f"[CastlerockCambridgeNowScraper] Waiting for page to load...")
            time.sleep(10)
            
            # Wait for the Quick Move-Ins tab content to be visible
            try:
                wait = WebDriverWait(driver, 20)
                # Wait for the tabpanel-an (Quick Move-Ins tab panel) to be visible
                wait.until(EC.presence_of_element_located((By.ID, "tabpanel-an")))
                print(f"[CastlerockCambridgeNowScraper] Quick Move-Ins tab loaded")
                
                # Make sure the Quick Move-Ins tab is active (click it if needed)
                try:
                    an_tab = driver.find_element(By.ID, "an")
                    if an_tab.get_attribute("aria-selected") != "true":
                        driver.execute_script("arguments[0].click();", an_tab)
                        time.sleep(2)
                        print(f"[CastlerockCambridgeNowScraper] Clicked Quick Move-Ins tab")
                except:
                    pass
            except Exception as e:
                print(f"[CastlerockCambridgeNowScraper] Warning: Could not find Quick Move-Ins tab panel: {e}")
            
            # Collect items incrementally as we scroll (virtual scrolling removes items from DOM)
            collected_listing_data = {}  # Use dict to avoid duplicates by address
            scroll_step = 400  # Scroll increment
            max_scrolls = 100  # Increased max scrolls
            
            print(f"[CastlerockCambridgeNowScraper] Starting incremental collection of listings...")
            
            # Start from top
            scroll_container = None
            try:
                scroll_container = driver.find_element(By.CSS_SELECTOR, "[data-scrollbars='y']")
                driver.execute_script("arguments[0].scrollTop = 0", scroll_container)
            except:
                driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            last_scroll_pos = -1
            no_progress_count = 0
            
            for scroll_attempt in range(max_scrolls):
                # Collect items currently visible in the DOM
                current_items_html = driver.execute_script("""
                    var items = [];
                    var cards = document.querySelectorAll('[class*="_itemWrapper"], [class*="_cardRoot"]');
                    for (var i = 0; i < cards.length; i++) {
                        items.push(cards[i].outerHTML);
                    }
                    return items;
                """)
                
                # Parse and collect listing data from current visible items
                for item_html in current_items_html:
                    try:
                        item_soup = BeautifulSoup(item_html, 'html.parser')
                        card = item_soup.find('div')
                        if not card:
                            continue
                        
                        # Extract address from subtitle (Quick Move-Ins have addresses, not plan names)
                        subtitle_elem = card.find('p', class_=lambda x: x and '_subtitle' in x if x else False)
                        if subtitle_elem:
                            address_text = subtitle_elem.get_text(strip=True)
                            # Address format: "16116 Garden Drive\n\nCelina, TX 75009"
                            # Extract just the street address (first line)
                            address_lines = [line.strip() for line in address_text.split('\n') if line.strip()]
                            if address_lines:
                                address = address_lines[0]  # Use first line as address
                                if address and address not in collected_listing_data:
                                    # Store the HTML for later processing
                                    collected_listing_data[address] = item_html
                    except:
                        pass
                
                print(f"[CastlerockCambridgeNowScraper] Scroll attempt {scroll_attempt + 1}: Collected {len(collected_listing_data)} unique listings")
                
                # Scroll down
                if scroll_container:
                    try:
                        current_scroll = driver.execute_script("return arguments[0].scrollTop", scroll_container)
                        scroll_height = driver.execute_script("return arguments[0].scrollHeight", scroll_container)
                        client_height = driver.execute_script("return arguments[0].clientHeight", scroll_container)
                        max_scroll = scroll_height - client_height
                        
                        # Check if we've reached the bottom
                        if current_scroll >= max_scroll - 10:
                            print(f"[CastlerockCambridgeNowScraper] Reached bottom of scroll container")
                            break
                        
                        # Scroll down
                        new_scroll = min(current_scroll + scroll_step, max_scroll)
                        driver.execute_script("arguments[0].scrollTop = arguments[1]", scroll_container, new_scroll)
                        
                        # Check if scroll position changed
                        if abs(new_scroll - current_scroll) < 1:
                            no_progress_count += 1
                            if no_progress_count >= 3:
                                print(f"[CastlerockCambridgeNowScraper] No scroll progress, stopping")
                                break
                        else:
                            no_progress_count = 0
                            last_scroll_pos = new_scroll
                    except Exception as e:
                        print(f"[CastlerockCambridgeNowScraper] Error scrolling: {e}")
                        break
                else:
                    current_scroll = driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop")
                    max_scroll = driver.execute_script("return document.body.scrollHeight - window.innerHeight")
                    
                    if current_scroll >= max_scroll - 10:
                        break
                    
                    driver.execute_script(f"window.scrollBy(0, {scroll_step});")
                    no_progress_count = 0
                
                time.sleep(0.6)  # Wait for items to render
            
            # Final collection pass - scroll through one more time slowly
            print(f"[CastlerockCambridgeNowScraper] Performing final collection pass...")
            if scroll_container:
                driver.execute_script("arguments[0].scrollTop = 0", scroll_container)
                time.sleep(1)
                
                # Scroll through slowly one more time
                for i in range(30):
                    current_scroll = driver.execute_script("return arguments[0].scrollTop", scroll_container)
                    scroll_height = driver.execute_script("return arguments[0].scrollHeight", scroll_container)
                    client_height = driver.execute_script("return arguments[0].clientHeight", scroll_container)
                    max_scroll = scroll_height - client_height
                    
                    if current_scroll >= max_scroll - 10:
                        break
                    
                    # Collect items at this position
                    current_items_html = driver.execute_script("""
                        var items = [];
                        var cards = document.querySelectorAll('[class*="_itemWrapper"], [class*="_cardRoot"]');
                        for (var i = 0; i < cards.length; i++) {
                            items.push(cards[i].outerHTML);
                        }
                        return items;
                    """)
                    
                    for item_html in current_items_html:
                        try:
                            item_soup = BeautifulSoup(item_html, 'html.parser')
                            card = item_soup.find('div')
                            if card:
                                subtitle_elem = card.find('p', class_=lambda x: x and '_subtitle' in x if x else False)
                                if subtitle_elem:
                                    address_text = subtitle_elem.get_text(strip=True)
                                    address_lines = [line.strip() for line in address_text.split('\n') if line.strip()]
                                    if address_lines:
                                        address = address_lines[0]
                                        if address and address not in collected_listing_data:
                                            collected_listing_data[address] = item_html
                        except:
                            pass
                    
                    # Scroll down
                    new_scroll = min(current_scroll + 300, max_scroll)
                    driver.execute_script("arguments[0].scrollTop = arguments[1]", scroll_container, new_scroll)
                    time.sleep(0.5)
            
            print(f"[CastlerockCambridgeNowScraper] Total collected: {len(collected_listing_data)} unique listings")
            
            # Convert collected HTML to list for processing
            listing_cards = []
            for address, html in collected_listing_data.items():
                try:
                    card_soup = BeautifulSoup(html, 'html.parser')
                    card = card_soup.find('div')
                    if card:
                        listing_cards.append(card)
                except Exception as e:
                    print(f"[CastlerockCambridgeNowScraper] Error parsing collected HTML for {address}: {e}")
                    continue
            
            print(f"[CastlerockCambridgeNowScraper] Found {len(listing_cards)} listing cards from incremental collection")
            
            listings = []
            seen_addresses = set()  # Track addresses to prevent duplicates
            
            for idx, card in enumerate(listing_cards):
                try:
                    print(f"[CastlerockCambridgeNowScraper] Processing card {idx+1}")
                    
                    # Extract plan name from h2 with class containing "_title"
                    plan_name_elem = card.find('h2', class_=lambda x: x and '_title' in x if x else False)
                    if not plan_name_elem:
                        plan_name_elem = card.find('h2')
                    
                    plan_name = plan_name_elem.get_text(strip=True) if plan_name_elem else ""
                    
                    # Extract address from subtitle
                    subtitle_elem = card.find('p', class_=lambda x: x and '_subtitle' in x if x else False)
                    if not subtitle_elem:
                        print(f"[CastlerockCambridgeNowScraper] Skipping card {idx+1}: No address found")
                        continue
                    
                    address_text = subtitle_elem.get_text(strip=True)
                    address_lines = [line.strip() for line in address_text.split('\n') if line.strip()]
                    if not address_lines:
                        print(f"[CastlerockCambridgeNowScraper] Skipping card {idx+1}: Empty address")
                        continue
                    
                    address = address_lines[0]  # Street address
                    full_address = "\n".join(address_lines)  # Full address with city/state
                    
                    # Check for duplicate addresses
                    if address in seen_addresses:
                        print(f"[CastlerockCambridgeNowScraper] Skipping card {idx+1}: Duplicate address '{address}'")
                        continue
                    
                    seen_addresses.add(address)
                    
                    # Extract status from status banner
                    status = ""
                    status_banner = card.find('div', class_=lambda x: x and '_statusBanner' in x if x else False)
                    if status_banner:
                        status = status_banner.get_text(strip=True)
                    
                    # Extract price, beds, baths, sqft, garage, stories from the grid
                    stats_grid = card.find('div', class_=lambda x: x and 'SimpleGrid' in x if x else False)
                    
                    price = None
                    beds = ""
                    baths = ""
                    sqft = None
                    garage = ""
                    stories = "1"
                    
                    if stats_grid:
                        # Find all icon-text root elements
                        stat_items = stats_grid.find_all('div', class_=lambda x: x and '_iconTextRoot' in x if x else False)
                        
                        for stat_item in stat_items:
                            # Get the text content
                            text_elem = stat_item.find('p', class_=lambda x: x and '_text' in x if x else False)
                            if not text_elem:
                                text_elem = stat_item.find('p')
                            
                            if text_elem:
                                text = text_elem.get_text(strip=True)
                                
                                # Check for price (contains $)
                                if '$' in text:
                                    price = self.parse_price(text)
                                
                                # Check for beds
                                elif 'Bed' in text or 'bed' in text:
                                    beds = self.parse_beds(text)
                                
                                # Check for baths
                                elif 'Bath' in text or 'bath' in text:
                                    baths = self.parse_baths(text)
                                
                                # Check for square footage
                                elif 'Square Feet' in text or 'sqft' in text.lower() or 'sq ft' in text.lower():
                                    sqft = self.parse_sqft(text)
                                
                                # Check for garage
                                elif 'Garage' in text or 'garage' in text:
                                    garage = self.parse_garage(text)
                                
                                # Check for stories
                                elif 'Story' in text or 'story' in text:
                                    stories = self.parse_stories(text)
                    
                    # If we didn't find price in the grid, try alternative locations
                    if not price:
                        price_elem = card.find(string=re.compile(r'\$[\d,]+'))
                        if price_elem:
                            price = self.parse_price(price_elem)
                    
                    if not price:
                        print(f"[CastlerockCambridgeNowScraper] Skipping card {idx+1}: No price found for '{address}'")
                        continue
                    
                    if not sqft:
                        print(f"[CastlerockCambridgeNowScraper] Skipping card {idx+1}: No square footage found for '{address}'")
                        continue
                    
                    # Extract image URL
                    image_url = ""
                    img_tag = card.find('img', class_=lambda x: x and '_image' in x if x else False)
                    if not img_tag:
                        img_tag = card.find('img')
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag['src']
                    
                    # Extract detail link
                    detail_link = ""
                    link_tag = card.find('a', href=True)
                    if link_tag:
                        href = link_tag['href']
                        if href.startswith('/'):
                            detail_link = f"https://www.c-rock.com{href}"
                        elif href.startswith('http'):
                            detail_link = href
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                    
                    listing_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,  # Plan name (e.g., "Hayden", "San Marcos")
                        "company": "Castlerock",
                        "community": "Cambridge",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": full_address,  # Full address with city/state
                        "original_price": None,
                        "price_cut": "",
                        "status": status,  # e.g., "Move-In Ready", "Under Construction"
                        "mls": "",
                        "sub_community": "Green Meadows",
                        "image_url": image_url,
                        "detail_link": detail_link,
                        "garage": garage
                    }
                    
                    print(f"[CastlerockCambridgeNowScraper] Listing {idx+1}: {plan_name} - {address} - ${price:,} - {sqft} sqft - {beds} beds - {baths} baths - {stories} story - {status}")
                    listings.append(listing_data)
                    
                except Exception as e:
                    print(f"[CastlerockCambridgeNowScraper] Error processing card {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[CastlerockCambridgeNowScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[CastlerockCambridgeNowScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                driver.quit()

