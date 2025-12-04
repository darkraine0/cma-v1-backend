import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class BeazerHomesReunionPlanScraper(BaseScraper):
    URL = "https://www.beazer.com/dallas-tx/wildflower-ranch"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        # Handle ranges like "2,253-2,442" or "2,253 - 2,442" or single values like "1,531"
        if '-' in text:
            # Take the first number for ranges
            match = re.search(r'([\d,]+)', text)
        else:
            match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract starting price from text."""
        match = re.search(r'From \$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        # Handle ranges like "3-4" or "3 - 4" or single values like "3"
        if '-' in text:
            match = re.search(r'(\d+)\s*-\s*(\d+)', text)
            if match:
                return f"{match.group(1)}-{match.group(2)}"
        else:
            match = re.search(r'(\d+)', text)
            if match:
                return match.group(1)
        return ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle ranges like "2.5-3" or "2.5 - 3" or single values like "2"
        if '-' in text:
            match = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', text)
            if match:
                return f"{match.group(1)}-{match.group(2)}"
        else:
            match = re.search(r'(\d+(?:\.\d+)?)', text)
            if match:
                return match.group(1)
        return ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        # Default to 1 story for these homes based on the data
        return "1"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[BeazerHomesReunionPlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[BeazerHomesReunionPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[BeazerHomesReunionPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all plan cards - these are in div elements with class 'swiper-slide'
            # We need to find the active tab panel for "Home plans" (tab-0)
            # Try finding by id first, then fall back to data-state="active"
            tab_panel = soup.find('div', {'id': 'tab-0', 'role': 'tabpanel'})
            if not tab_panel:
                # Fallback: find active tab panel
                tab_panel = soup.find('div', {'role': 'tabpanel', 'data-state': 'active'})
            if not tab_panel:
                print(f"[BeazerHomesReunionPlanScraper] Could not find Home plans tab panel")
                return []
            
            plan_cards = tab_panel.find_all('div', class_='swiper-slide')
            print(f"[BeazerHomesReunionPlanScraper] Found {len(plan_cards)} plan cards")
            
            for idx, card in enumerate(plan_cards):
                try:
                    print(f"[BeazerHomesReunionPlanScraper] Processing plan card {idx+1}")
                    
                    # Extract plan name from h3 > a element
                    plan_name_elem = card.find('h3')
                    if plan_name_elem:
                        plan_name_link = plan_name_elem.find('a')
                        if plan_name_link:
                            plan_name = plan_name_link.get_text(strip=True)
                        else:
                            plan_name = plan_name_elem.get_text(strip=True)
                    else:
                        print(f"[BeazerHomesReunionPlanScraper] Skipping plan card {idx+1}: No plan name found")
                        continue
                    
                    if not plan_name:
                        print(f"[BeazerHomesReunionPlanScraper] Skipping plan card {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[BeazerHomesReunionPlanScraper] Skipping plan card {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract starting price from p element with specific classes
                    # Look for p with class containing 'text-numeric-xs' and 'font-numeric-bold'
                    price_elem = None
                    for p in card.find_all('p'):
                        classes = p.get('class', [])
                        if 'text-numeric-xs' in classes and 'font-numeric-bold' in classes:
                            price_text = p.get_text(strip=True)
                            if 'From $' in price_text:
                                price_elem = p
                                break
                    
                    if not price_elem:
                        print(f"[BeazerHomesReunionPlanScraper] Skipping plan card {idx+1}: No price found")
                        continue
                    
                    starting_price = self.parse_price(price_elem.get_text())
                    if not starting_price:
                        print(f"[BeazerHomesReunionPlanScraper] Skipping plan card {idx+1}: No starting price found")
                        continue
                    
                    # Extract specs from ul with aria-label="Feature Specifications"
                    specs_ul = card.find('ul', {'aria-label': 'Feature Specifications'})
                    if not specs_ul:
                        print(f"[BeazerHomesReunionPlanScraper] Skipping plan card {idx+1}: No specs found")
                        continue
                    
                    sqft = None
                    beds = ""
                    baths = ""
                    stories = "1"
                    
                    # Extract specs from li elements
                    spec_items = specs_ul.find_all('li')
                    for item in spec_items:
                        # Each li has two p elements: label and value
                        p_elements = item.find_all('p')
                        if len(p_elements) >= 2:
                            label = p_elements[0].get_text(strip=True)
                            value = p_elements[1].get_text(strip=True)
                            
                            if 'Size' in label or 'sq ft' in label.lower():
                                sqft = self.parse_sqft(value)
                            elif 'Bedroom' in label:
                                beds = self.parse_beds(value)
                            elif 'Bathroom' in label:
                                baths = self.parse_baths(value)
                    
                    if not sqft:
                        print(f"[BeazerHomesReunionPlanScraper] Skipping plan card {idx+1}: No square footage found")
                        continue
                    
                    # Calculate price per sqft
                    price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                    
                    plan_data = {
                        "price": starting_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Beazer Homes",
                        "community": "Reunion",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "status": "Plan",
                        "address": "",
                        "floor_plan": plan_name
                    }
                    
                    print(f"[BeazerHomesReunionPlanScraper] Plan card {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[BeazerHomesReunionPlanScraper] Error processing plan card {idx+1}: {e}")
                    continue
            
            print(f"[BeazerHomesReunionPlanScraper] Successfully processed {len(listings)} plan cards")
            return listings
            
        except Exception as e:
            print(f"[BeazerHomesReunionPlanScraper] Error: {e}")
            return []
