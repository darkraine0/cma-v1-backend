import requests
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict
import re
import json

class CoventryHomesEdgewaterPlanScraper(BaseScraper):
    def __init__(self):
        self.base_url = "https://www.coventryhomes.com/new-homes/tx/fate/avondale/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

    def parse_price(self, price_text):
        """Extract price from price text."""
        if not price_text:
            return None
        # Remove $ and commas, then convert to integer
        price_str = str(price_text).replace("$", "").replace(",", "")
        try:
            return int(float(price_str))
        except (ValueError, TypeError):
            return None

    def parse_sqft(self, sqft_text):
        """Extract square footage from text."""
        if not sqft_text:
            return None
        # Extract numbers from text like "1,649" or "1,649 AREA (SQFT)"
        match = re.search(r'([\d,]+)', str(sqft_text))
        if match:
            sqft_str = match.group(1).replace(",", "")
            try:
                return int(sqft_str)
            except (ValueError, TypeError):
                return None
        return None

    def parse_beds_baths(self, text):
        """Extract beds and baths from text."""
        if not text:
            return "", ""
        
        text_str = str(text).strip()
        beds = ""
        baths = ""
        
        # Extract beds (first number in the list)
        beds_match = re.search(r'(\d+)', text_str)
        if beds_match:
            beds = beds_match.group(1)
        
        # Extract baths (second number in the list)
        # Look for the second number in the list
        numbers = re.findall(r'(\d+(?:\.\d+)?)', text_str)
        if len(numbers) >= 2:
            baths = numbers[1]
        elif len(numbers) == 1:
            baths = numbers[0]
        
        return beds, baths

    def parse_stories(self, description):
        """Extract number of stories from description."""
        if not description:
            return "1"
        
        description_lower = description.lower()
        if "two-story" in description_lower or "2-story" in description_lower:
            return "2"
        elif "one-story" in description_lower or "1-story" in description_lower:
            return "1"
        else:
            # Default based on common patterns
            return "1"

    def fetch_plans(self) -> List[Dict]:
        """Fetch plans from CoventryHomes Edgewater community."""
        try:
            print("[CoventryHomesEdgewaterPlanScraper] Starting to fetch CoventryHomes plans for Edgewater")
            
            response = requests.get(self.base_url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                print(f"[CoventryHomesEdgewaterPlanScraper] Request failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all model cards anywhere on the page
            model_cards = soup.find_all('div', class_='model-card')
            if not model_cards:
                print("[CoventryHomesEdgewaterPlanScraper] Could not find any model cards")
                return []
            print(f"[CoventryHomesEdgewaterPlanScraper] Found {len(model_cards)} model cards")
            
            all_plans = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            for idx, card in enumerate(model_cards):
                try:
                    # Extract plan name
                    plan_name_element = card.find('div', class_='model-name')
                    if not plan_name_element:
                        print(f"[CoventryHomesEdgewaterPlanScraper] Skipping card {idx+1}: No plan name found")
                        continue
                    
                    plan_name = plan_name_element.get_text(strip=True)
                    if not plan_name:
                        print(f"[CoventryHomesEdgewaterPlanScraper] Skipping card {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[CoventryHomesEdgewaterPlanScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract price
                    price_element = card.find('a', class_='price-bar')
                    if not price_element:
                        print(f"[CoventryHomesEdgewaterPlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    price_text = price_element.find('span')
                    if not price_text:
                        print(f"[CoventryHomesEdgewaterPlanScraper] Skipping card {idx+1}: No price span found")
                        continue
                    
                    price = self.parse_price(price_text.get_text())
                    if not price:
                        print(f"[CoventryHomesEdgewaterPlanScraper] Skipping card {idx+1}: Could not parse price")
                        continue
                    
                    # Extract beds, baths, and sqft from model info bar
                    info_bar = card.find('ul', class_='model-info-bar')
                    beds = ""
                    baths = ""
                    sqft = None
                    
                    if info_bar:
                        info_items = info_bar.find_all('li')
                        for i, item in enumerate(info_items):
                            item_text = item.get_text(strip=True)
                            if i == 0:  # First item is sqft
                                sqft = self.parse_sqft(item_text)
                            elif i == 1:  # Second item is beds
                                # Extract just the number from "3Beds" or "3 Beds"
                                beds_match = re.search(r'(\d+)', item_text)
                                beds = beds_match.group(1) if beds_match else item_text
                            elif i == 2:  # Third item is baths
                                # Extract just the number from "2Baths" or "2/1Baths"
                                baths_match = re.search(r'(\d+(?:/\d+)?)', item_text)
                                baths = baths_match.group(1) if baths_match else item_text
                    
                    if not sqft:
                        print(f"[CoventryHomesEdgewaterPlanScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Extract image URL
                    image_url = ""
                    image_element = card.find('img', class_='oi-aspect-img')
                    if image_element:
                        image_url = image_element.get('src', '')
                    
                    # Extract description from JSON-LD script
                    description = ""
                    script_element = card.find('script', type='application/ld+json')
                    if script_element:
                        try:
                            json_data = json.loads(script_element.get_text())
                            description = json_data.get('description', '')
                        except json.JSONDecodeError:
                            pass
                    
                    # Determine stories from description
                    stories = self.parse_stories(description)
                    
                    # Calculate price per sqft
                    price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                    
                    # Create plan data
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "CoventryHomes",
                        "community": "Edgewater",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": plan_name,  # Use plan name as address for plans
                        "image_url": image_url,
                        "description": description
                    }
                    
                    print(f"[CoventryHomesEdgewaterPlanScraper] Processed plan {idx+1}: {plan_name} - ${price:,} - {sqft} sqft")
                    all_plans.append(plan_data)
                    
                except Exception as e:
                    print(f"[CoventryHomesEdgewaterPlanScraper] Error processing card {idx+1}: {e}")
                    continue
            
            print(f"[CoventryHomesEdgewaterPlanScraper] Successfully processed {len(all_plans)} plans")
            return all_plans
            
        except Exception as e:
            print(f"[CoventryHomesEdgewaterPlanScraper] Error: {e}")
            return []
