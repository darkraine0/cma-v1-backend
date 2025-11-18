#!/usr/bin/env python3
"""
Fischer Homes Laurel Farms Now Scraper
Scrapes "now" (available homes) information from Fischer Homes Laurel Farms community
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
from app.scrapers.base import BaseScraper


class FischerHomesLaurelFarmsNowScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.URL = "https://www.fischerhomes.com/find-new-homes/dallas/ga/communities/885/laurel-farms#/residences-homes"
        self.COMPANY = "Fischer Homes"
        self.COMMUNITY = "Pickens Bluff"
        self.TYPE = "now"

    def fetch_plans(self):
        """
        Fetch "now" (available homes) information from Fischer Homes Laurel Farms using Selenium
        """
        print(f"[FischerHomesLaurelFarmsNowScraper] Fetching URL: {self.URL}")
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(self.URL)
            
            # Wait for the page to load and content to be populated
            print(f"[FischerHomesLaurelFarmsNowScraper] Waiting for page to load...")
            time.sleep(10)
            
            # Scroll to trigger content loading
            print(f"[FischerHomesLaurelFarmsNowScraper] Scrolling to trigger content loading...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            
            # Wait for now cards to be loaded
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "card_mov-in-ready")))
            
            # Get the page source after JavaScript has loaded
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find "now" cards (card_mov-in-ready articles)
            now_cards = soup.find_all('article', class_='card_mov-in-ready')
            print(f"[FischerHomesLaurelFarmsNowScraper] Found {len(now_cards)} now cards")
            
            now_listings = []
            
            for card in now_cards:
                try:
                    # Extract plan name
                    plan_name_elem = card.find('h3', class_='reg__card-title')
                    if not plan_name_elem:
                        continue
                    plan_name = plan_name_elem.get_text(strip=True)
                    
                    # Extract address
                    address_elem = card.find('span', class_='reg__card-address')
                    address = None
                    if address_elem:
                        address = address_elem.get_text(strip=True)
                    
                    # Extract price
                    price_elem = card.find('span', class_='reg__card-price')
                    price = None
                    if price_elem:
                        price_span = price_elem.find('span', class_='ng-binding')
                        if price_span:
                            price_text = price_span.get_text(strip=True)
                            # Extract price from "$492,990"
                            price_match = re.search(r'\$([\d,]+)', price_text)
                            if price_match:
                                price = int(price_match.group(1).replace(',', ''))
                    
                    # Extract beds, baths, sqft from snapshot-info
                    snapshot_info = card.find('snapshot-info')
                    beds = None
                    baths = None
                    sqft = None
                    stories = None
                    
                    if snapshot_info:
                        # Get from attributes first
                        beds_attr = snapshot_info.get('beds')
                        baths_attr = snapshot_info.get('baths')
                        sqft_attr = snapshot_info.get('sqft')
                        levels_attr = snapshot_info.get('levels')
                        
                        if beds_attr:
                            beds = beds_attr
                        if baths_attr:
                            baths = baths_attr
                        if sqft_attr:
                            # Extract first number from range like "2,711 - 3,831"
                            sqft_match = re.search(r'([\d,]+)', sqft_attr)
                            if sqft_match:
                                sqft = int(sqft_match.group(1).replace(',', ''))
                        if levels_attr:
                            stories = f"{levels_attr} Story"
                    
                    # Extract URL
                    url = None
                    footer_link = card.find('div', class_='reg__card-footer')
                    if footer_link:
                        link_elem = footer_link.find('a', href=True)
                        if link_elem:
                            url = link_elem.get('href')
                            if url and not url.startswith('http'):
                                url = f"https://www.fischerhomes.com{url}"
                    
                    # Calculate price per sqft
                    price_per_sqft = None
                    if price and sqft:
                        price_per_sqft = round(price / sqft, 2)
                    
                    now_data = {
                        'plan_name': plan_name,
                        'price': price,
                        'sqft': sqft,
                        'stories': stories,
                        'price_per_sqft': price_per_sqft,
                        'company': self.COMPANY,
                        'community': self.COMMUNITY,
                        'type': self.TYPE,
                        'beds': beds,
                        'baths': baths,
                        'address': address,
                        'design_number': None,
                        'url': url,
                        'status': "available"  # Default to available
                    }
                    
                    now_listings.append(now_data)
                    print(f"[FischerHomesLaurelFarmsNowScraper] Now: {plan_name} - ${price:,} - {sqft} sqft - {beds} beds - {baths} baths - {address}")
                        
                except Exception as e:
                    print(f"[FischerHomesLaurelFarmsNowScraper] Error processing now card: {e}")
                    continue
            
            print(f"[FischerHomesLaurelFarmsNowScraper] Successfully processed {len(now_listings)} now listings")
            return now_listings
            
        except Exception as e:
            print(f"[FischerHomesLaurelFarmsNowScraper] Error fetching now listings: {e}")
            return []
        finally:
            if driver:
                driver.quit()
