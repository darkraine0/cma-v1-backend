#!/usr/bin/env python3
"""
Fischer Homes Sage Woods Plan Scraper
Scrapes plan information from Fischer Homes Sage Woods community
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


class FischerHomesSageWoodsPlanScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.URL = "https://www.fischerhomes.com/find-new-homes/dallas/ga/communities/887/sage-woods#/residences-homes"
        self.COMPANY = "Fischer Homes"
        self.COMMUNITY = "Pickens Bluff"
        self.TYPE = "plan"

    def fetch_plans(self):
        """
        Fetch plan information from Fischer Homes Sage Woods using Selenium
        """
        print(f"[FischerHomesSageWoodsPlanScraper] Fetching URL: {self.URL}")
        
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
            print(f"[FischerHomesSageWoodsPlanScraper] Waiting for page to load...")
            time.sleep(10)
            
            # Scroll to trigger content loading
            print(f"[FischerHomesSageWoodsPlanScraper] Scrolling to trigger content loading...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            
            # Wait for plan cards to be loaded
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "floorplan-card")))
            
            # Get the page source after JavaScript has loaded
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find plan cards (floorplan-card articles)
            plan_cards = soup.find_all('article', class_='floorplan-card')
            print(f"[FischerHomesSageWoodsPlanScraper] Found {len(plan_cards)} plan cards")
            
            plans = []
            
            for card in plan_cards:
                try:
                    # Extract plan name
                    plan_name_elem = card.find('h3', class_='reg__card-title')
                    if not plan_name_elem:
                        continue
                    plan_name = plan_name_elem.get_text(strip=True)
                    
                    # Extract price - look for "Starting at" text
                    price_elem = card.find('span', class_='reg__card-price')
                    price = None
                    if price_elem:
                        price_span = price_elem.find('span', class_='ng-binding')
                        if price_span:
                            price_text = price_span.get_text(strip=True)
                            # Extract price from "Starting at $492,990"
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
                    
                    plan_data = {
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
                        'address': None,  # Plans don't have specific addresses
                        'design_number': None,
                        'url': url
                    }
                    
                    plans.append(plan_data)
                    print(f"[FischerHomesSageWoodsPlanScraper] Plan: {plan_name} - ${price:,} - {sqft} sqft - {beds} beds - {baths} baths")
                        
                except Exception as e:
                    print(f"[FischerHomesSageWoodsPlanScraper] Error processing plan card: {e}")
                    continue
            
            print(f"[FischerHomesSageWoodsPlanScraper] Successfully processed {len(plans)} plans")
            return plans
            
        except Exception as e:
            print(f"[FischerHomesSageWoodsPlanScraper] Error fetching plans: {e}")
            return []
        finally:
            if driver:
                driver.quit()
