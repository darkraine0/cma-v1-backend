import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class AmericanLegendHomesCambridgePlanScraper(BaseScraper):
    URL = "https://www.amlegendhomes.com/communities/texas/celina/ten-mile-creek"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+(?:-\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "3" and "3.5" formats
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[AmericanLegendHomesCambridgePlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[AmericanLegendHomesCambridgePlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[AmericanLegendHomesCambridgePlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all plan cards - they have the class "css-zxy9ty" and contain plan information
            plan_cards = soup.find_all('div', class_='css-zxy9ty')
            print(f"[AmericanLegendHomesCambridgePlanScraper] Found {len(plan_cards)} plan cards")
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[AmericanLegendHomesCambridgePlanScraper] Processing plan card {idx+1}")
                    
                    # Extract plan name and number
                    title_link = card.find('a', class_='PlanCard_title')
                    if not title_link:
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Skipping card {idx+1}: No title link found")
                        continue
                    
                    plan_name = title_link.get_text(strip=True)
                    if not plan_name:
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Skipping card {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract price - look for the strong tag with price
                    price_strong = card.find('strong')
                    if not price_strong:
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Skipping card {idx+1}: No price found")
                        continue
                    
                    current_price = self.parse_price(price_strong.get_text())
                    if not current_price:
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Skipping card {idx+1}: No current price found")
                        continue
                    
                    # Extract plan details (stories, beds, baths, sqft) from the PlanCard_list
                    detail_list = card.find('ul', class_='PlanCard_list')
                    beds = ""
                    baths = ""
                    stories = ""
                    sqft = None
                    
                    if detail_list:
                        detail_items = detail_list.find_all('li', class_='PlanCard_listItem')
                        for item in detail_items:
                            item_text = item.get_text(strip=True)
                            if 'Stories' in item_text:
                                stories = self.parse_stories(item_text)
                            elif 'Beds' in item_text:
                                beds = self.parse_beds(item_text)
                            elif 'Baths' in item_text:
                                baths = self.parse_baths(item_text)
                            elif 'Sqft' in item_text:
                                sqft = self.parse_sqft(item_text)
                    
                    if not sqft:
                        print(f"[AmericanLegendHomesCambridgePlanScraper] Skipping card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                    
                    # Extract image URL if available
                    image_wrapper = card.find('a', class_='PlanCard_imageWrapper')
                    image_url = ""
                    if image_wrapper:
                        img_tag = image_wrapper.find('img')
                        if img_tag and img_tag.get('src'):
                            image_url = img_tag['src']
                    
                    # Extract plan detail link
                    detail_link = ""
                    detail_link_tag = card.find('a', class_='PlanCard_linkDetail')
                    if detail_link_tag and detail_link_tag.get('href'):
                        detail_link = detail_link_tag['href']
                        # Make it absolute URL if it's relative
                        if detail_link.startswith('/'):
                            detail_link = f"https://www.amlegendhomes.com{detail_link}"
                    
                    plan_data = {
                        "price": current_price,
                        "sqft": sqft,
                        "stories": stories or "1",
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "American Legend Homes",
                        "community": "Cambridge",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",
                        "original_price": None,
                        "price_cut": "",
                        "image_url": image_url,
                        "detail_link": detail_link
                    }
                    
                    print(f"[AmericanLegendHomesCambridgePlanScraper] Plan {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[AmericanLegendHomesCambridgePlanScraper] Error processing plan card {idx+1}: {e}")
                    continue
            
            print(f"[AmericanLegendHomesCambridgePlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[AmericanLegendHomesCambridgePlanScraper] Error: {e}")
            return []
