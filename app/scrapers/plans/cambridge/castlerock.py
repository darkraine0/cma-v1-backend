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


class CastlerockCambridgePlanScraper(BaseScraper):
    URL = "https://www.c-rock.com/community/texas/dallas/green_meadows?splitPageTabBar=1"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract base price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        match = re.search(r'(\d+)', text)
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
            print(f"[CastlerockCambridgePlanScraper] Fetching URL: {self.URL}")
            
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
            print(f"[CastlerockCambridgePlanScraper] Waiting for page to load...")
            time.sleep(10)
            
            # Wait for the Floorplans tab content to be visible
            try:
                wait = WebDriverWait(driver, 20)
                # Wait for the tabpanel-fp (Floorplans tab panel) to be visible
                wait.until(EC.presence_of_element_located((By.ID, "tabpanel-fp")))
                print(f"[CastlerockCambridgePlanScraper] Floorplans tab loaded")
                
                # Make sure the Floorplans tab is active (click it if needed)
                try:
                    fp_tab = driver.find_element(By.ID, "fp")
                    if fp_tab.get_attribute("aria-selected") != "true":
                        driver.execute_script("arguments[0].click();", fp_tab)
                        time.sleep(2)
                        print(f"[CastlerockCambridgePlanScraper] Clicked Floorplans tab")
                except:
                    pass
            except Exception as e:
                print(f"[CastlerockCambridgePlanScraper] Warning: Could not find Floorplans tab panel: {e}")
            
            # Scroll within the virtual scrolling container to load all items
            print(f"[CastlerockCambridgePlanScraper] Scrolling to load all floorplans...")
            
            # Find the scrollable container (the ScrollArea viewport)
            scroll_container = None
            try:
                # Try multiple selectors to find the scrollable container
                # The ScrollArea viewport has data-scrollbars attribute
                scroll_container = driver.find_element(By.CSS_SELECTOR, "[data-scrollbars='y']")
                print(f"[CastlerockCambridgePlanScraper] Found scrollable container")
            except:
                try:
                    # Alternative: find by class containing ScrollArea-viewport
                    scroll_container = driver.find_element(By.CSS_SELECTOR, "[class*='ScrollArea-viewport']")
                    print(f"[CastlerockCambridgePlanScraper] Found scrollable container (alternative)")
                except:
                    try:
                        # Try finding the scrollable content area
                        scroll_container = driver.find_element(By.CSS_SELECTOR, "[class*='ScrollArea-content']")
                        print(f"[CastlerockCambridgePlanScraper] Found scrollable container (content)")
                    except:
                        print(f"[CastlerockCambridgePlanScraper] No scrollable container found, using window scroll")
                        scroll_container = None
            
            # Collect items incrementally as we scroll (virtual scrolling removes items from DOM)
            # We need to collect items at each scroll position before they're removed
            collected_plan_data = {}  # Use dict to avoid duplicates by plan name
            scroll_step = 400  # Scroll increment
            max_scrolls = 100  # Increased max scrolls
            
            print(f"[CastlerockCambridgePlanScraper] Starting incremental collection of plans...")
            
            # Start from top
            if scroll_container:
                driver.execute_script("arguments[0].scrollTop = 0", scroll_container)
            else:
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
                    // Also try finding by h2 titles
                    if (items.length === 0) {
                        var titles = document.querySelectorAll('h2[class*="_title"]');
                        for (var i = 0; i < titles.length; i++) {
                            var card = titles[i].closest('[class*="_cardRoot"], [class*="_itemWrapper"]');
                            if (card) {
                                items.push(card.outerHTML);
                            }
                        }
                    }
                    return items;
                """)
                
                # Parse and collect plan data from current visible items
                for item_html in current_items_html:
                    try:
                        item_soup = BeautifulSoup(item_html, 'html.parser')
                        card = item_soup.find('div')
                        if not card:
                            continue
                        
                        # Extract plan name
                        plan_name_elem = card.find('h2', class_=lambda x: x and '_title' in x if x else False)
                        if not plan_name_elem:
                            plan_name_elem = card.find('h2')
                        
                        if plan_name_elem:
                            plan_name = plan_name_elem.get_text(strip=True)
                            if plan_name and plan_name not in collected_plan_data:
                                # Store the HTML for later processing
                                collected_plan_data[plan_name] = item_html
                    except:
                        pass
                
                print(f"[CastlerockCambridgePlanScraper] Scroll attempt {scroll_attempt + 1}: Collected {len(collected_plan_data)} unique plans")
                
                # Scroll down
                if scroll_container:
                    try:
                        current_scroll = driver.execute_script("return arguments[0].scrollTop", scroll_container)
                        scroll_height = driver.execute_script("return arguments[0].scrollHeight", scroll_container)
                        client_height = driver.execute_script("return arguments[0].clientHeight", scroll_container)
                        max_scroll = scroll_height - client_height
                        
                        # Check if we've reached the bottom
                        if current_scroll >= max_scroll - 10:
                            print(f"[CastlerockCambridgePlanScraper] Reached bottom of scroll container")
                            break
                        
                        # Scroll down
                        new_scroll = min(current_scroll + scroll_step, max_scroll)
                        driver.execute_script("arguments[0].scrollTop = arguments[1]", scroll_container, new_scroll)
                        
                        # Check if scroll position changed
                        if abs(new_scroll - current_scroll) < 1:
                            no_progress_count += 1
                            if no_progress_count >= 3:
                                print(f"[CastlerockCambridgePlanScraper] No scroll progress, stopping")
                                break
                        else:
                            no_progress_count = 0
                            last_scroll_pos = new_scroll
                    except Exception as e:
                        print(f"[CastlerockCambridgePlanScraper] Error scrolling: {e}")
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
            print(f"[CastlerockCambridgePlanScraper] Performing final collection pass...")
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
                                plan_name_elem = card.find('h2')
                                if plan_name_elem:
                                    plan_name = plan_name_elem.get_text(strip=True)
                                    if plan_name and plan_name not in collected_plan_data:
                                        collected_plan_data[plan_name] = item_html
                        except:
                            pass
                    
                    # Scroll down
                    new_scroll = min(current_scroll + 300, max_scroll)
                    driver.execute_script("arguments[0].scrollTop = arguments[1]", scroll_container, new_scroll)
                    time.sleep(0.5)
            
            print(f"[CastlerockCambridgePlanScraper] Total collected: {len(collected_plan_data)} unique plans")
            
            # Convert collected HTML to list for processing
            plan_cards = []
            for plan_name, html in collected_plan_data.items():
                try:
                    card_soup = BeautifulSoup(html, 'html.parser')
                    card = card_soup.find('div')
                    if card:
                        plan_cards.append(card)
                except Exception as e:
                    print(f"[CastlerockCambridgePlanScraper] Error parsing collected HTML for {plan_name}: {e}")
                    continue
            
            print(f"[CastlerockCambridgePlanScraper] Found {len(plan_cards)} plan cards from incremental collection")
            
            plans = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[CastlerockCambridgePlanScraper] Processing card {idx+1}")
                    
                    # Extract plan name from h2 with class containing "_title"
                    plan_name_elem = card.find('h2', class_=lambda x: x and '_title' in x if x else False)
                    if not plan_name_elem:
                        # Try alternative: find h2 in the card
                        plan_name_elem = card.find('h2')
                    
                    if not plan_name_elem:
                        print(f"[CastlerockCambridgePlanScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    plan_name = plan_name_elem.get_text(strip=True)
                    if not plan_name:
                        print(f"[CastlerockCambridgePlanScraper] Skipping card {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plans
                    if plan_name in seen_plan_names:
                        print(f"[CastlerockCambridgePlanScraper] Skipping card {idx+1}: Duplicate plan '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract price, beds, baths, sqft, garage, stories from the grid
                    # Look for the SimpleGrid that contains the stats
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
                        # Look for price in any element with $ symbol
                        price_elem = card.find(string=re.compile(r'\$[\d,]+'))
                        if price_elem:
                            price = self.parse_price(price_elem)
                    
                    if not price:
                        print(f"[CastlerockCambridgePlanScraper] Skipping card {idx+1}: No price found for '{plan_name}'")
                        continue
                    
                    if not sqft:
                        print(f"[CastlerockCambridgePlanScraper] Skipping card {idx+1}: No square footage found for '{plan_name}'")
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
                    
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Castlerock",
                        "community": "Cambridge",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",
                        "original_price": None,
                        "price_cut": "",
                        "status": "",
                        "mls": "",
                        "sub_community": "Green Meadows",
                        "image_url": image_url,
                        "detail_link": detail_link,
                        "garage": garage
                    }
                    
                    print(f"[CastlerockCambridgePlanScraper] Plan {idx+1}: {plan_name} - ${price:,} - {sqft} sqft - {beds} beds - {baths} baths - {stories} story")
                    plans.append(plan_data)
                    
                except Exception as e:
                    print(f"[CastlerockCambridgePlanScraper] Error processing card {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[CastlerockCambridgePlanScraper] Successfully processed {len(plans)} plans")
            return plans
            
        except Exception as e:
            print(f"[CastlerockCambridgePlanScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if driver:
                driver.quit()

