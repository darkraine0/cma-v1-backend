import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class PacesetterMilranyPlanScraper(BaseScraper):
    URL = "https://www.pacesetterhomestexas.com/new-homes-for-sale-dallas/melissa-tx/meadow-run?community=39"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        # Handle ranges like "2,125 - 2,129" or single values like "1,949"
        if ' - ' in text:
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
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "3" and "3.5" formats
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        # Default to 2 stories for these homes based on the data
        return "2"

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[PacesetterMilranyPlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[PacesetterMilranyPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[PacesetterMilranyPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Look for the qmi-carousel element that contains embedded JSON data
            qmi_carousel = soup.find('qmi-carousel')
            if qmi_carousel:
                print("[PacesetterMilranyPlanScraper] Found qmi-carousel element")
                
                # Extract the JSON data from the qmi-list attribute (Vue.js syntax)
                qmi_list_attr = qmi_carousel.get(':qmi-list', '')
                if not qmi_list_attr:
                    # Try without colon as fallback
                    qmi_list_attr = qmi_carousel.get('qmi-list', '')
                if qmi_list_attr:
                    try:
                        import json
                        # Parse the JSON data
                        plans_data = json.loads(qmi_list_attr)
                        print(f"[PacesetterMilranyPlanScraper] Found {len(plans_data)} plans in JSON data")
                        
                        for idx, plan in enumerate(plans_data):
                            try:
                                print(f"[PacesetterMilranyPlanScraper] Processing plan {idx+1}")
                                
                                # Extract plan name from address (e.g., "3519 Sunflower Street" -> "Sunflower 3519")
                                address = plan.get('address', '')
                                plan_name_match = re.search(r'(\d+)\s+([A-Za-z]+)', address)
                                if plan_name_match:
                                    plan_name = f"{plan_name_match.group(2)} {plan_name_match.group(1)}"
                                else:
                                    plan_name = address
                                
                                # Check for duplicate plan names
                                if plan_name in seen_plan_names:
                                    print(f"[PacesetterMilranyPlanScraper] Skipping plan {idx+1}: Duplicate plan name '{plan_name}'")
                                    continue
                                
                                seen_plan_names.add(plan_name)
                                
                                # Extract price
                                formatted_price = plan.get('formattedPrice', '')
                                # Parse price directly from JSON format (e.g., "$604,990")
                                price_match = re.search(r'\$([\d,]+)', formatted_price)
                                if not price_match:
                                    print(f"[PacesetterMilranyPlanScraper] Skipping plan {idx+1}: No starting price found in '{formatted_price}'")
                                    continue
                                
                                starting_price = int(price_match.group(1).replace(',', ''))
                                
                                # Extract beds, baths, and sqft
                                beds = str(plan.get('beds', ''))
                                baths = str(plan.get('baths', ''))
                                sqft_str = plan.get('sqft', '')
                                
                                if not sqft_str:
                                    print(f"[PacesetterMilranyPlanScraper] Skipping plan {idx+1}: No square footage found")
                                    continue
                                
                                # Parse sqft (remove commas and convert to int)
                                try:
                                    sqft = int(sqft_str.replace(',', ''))
                                except ValueError:
                                    print(f"[PacesetterMilranyPlanScraper] Skipping plan {idx+1}: Invalid square footage '{sqft_str}'")
                                    continue
                                
                                # Calculate price per sqft
                                price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                                
                                # Extract image URL if available
                                image_url = ""
                                if 'hero' in plan and 'image' in plan['hero']:
                                    image_url = plan['hero']['image'].get('medium', '')
                                elif 'images' in plan and 'resource' in plan['images']:
                                    image_url = plan['images']['resource'].get('medium', '')
                                
                                plan_data = {
                                    "price": starting_price,
                                    "sqft": sqft,
                                    "stories": self.parse_stories(""),
                                    "price_per_sqft": price_per_sqft,
                                    "plan_name": plan_name,
                                    "company": "Pacesetter Homes",
                                    "community": "Milrany",
                                    "type": "plan",
                                    "beds": beds,
                                    "baths": baths,
                                    "address": address,
                                    "original_price": None,
                                    "price_cut": "",
                                    "image_url": image_url,
                                    "plan_detail_url": ""
                                }
                                
                                print(f"[PacesetterMilranyPlanScraper] Plan {idx+1}: {plan_data}")
                                listings.append(plan_data)
                                
                            except Exception as e:
                                print(f"[PacesetterMilranyPlanScraper] Error processing plan {idx+1}: {e}")
                                continue
                    except json.JSONDecodeError as e:
                        print(f"[PacesetterMilranyPlanScraper] Error parsing JSON data: {e}")
                        return []
                else:
                    print("[PacesetterMilranyPlanScraper] No qmi-list attribute found in qmi-carousel")
            else:
                print("[PacesetterMilranyPlanScraper] No qmi-carousel element found")
                
                # Fallback: try to find plan cards in the communities grid
                plan_cards = soup.find_all('a', class_='plan-card')
                print(f"[PacesetterMilranyPlanScraper] Fallback: Found {len(plan_cards)} plan cards")
                
                for idx, card in enumerate(plan_cards):
                    try:
                        print(f"[PacesetterMilranyPlanScraper] Processing plan card {idx+1}")
                        
                        # Extract plan name
                        name_div = card.find('div', class_='plan-card__name')
                        if not name_div:
                            print(f"[PacesetterMilranyPlanScraper] Skipping card {idx+1}: No plan name found")
                            continue
                        
                        plan_name = name_div.get_text(strip=True)
                        if not plan_name:
                            print(f"[PacesetterMilranyPlanScraper] Skipping card {idx+1}: Empty plan name")
                            continue
                        
                        # Check for duplicate plan names
                        if plan_name in seen_plan_names:
                            print(f"[PacesetterMilranyPlanScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                            continue
                        
                        seen_plan_names.add(plan_name)
                        
                        # Extract starting price
                        price_div = card.find('div', class_='plan-card__price')
                        if not price_div:
                            print(f"[PacesetterMilranyPlanScraper] Skipping card {idx+1}: No price found")
                            continue
                        
                        starting_price = self.parse_price(price_div.get_text())
                        if not starting_price:
                            print(f"[PacesetterMilranyPlanScraper] Skipping card {idx+1}: No starting price found")
                            continue
                        
                        # Extract beds, baths, and sqft from snapshot section
                        snapshot_section = card.find('div', class_='plan-card__snapshot')
                        beds = ""
                        baths = ""
                        sqft = None
                        
                        if snapshot_section:
                            attribute_items = snapshot_section.find_all('div', class_='plan-card__attribute')
                            for item in attribute_items:
                                attribute_text = item.find('div', class_='plan-card__attribute-text')
                                if attribute_text:
                                    text_content = attribute_text.get_text(strip=True)
                                    if 'Beds' in text_content:
                                        # Extract beds from span content
                                        span = attribute_text.find('span')
                                        if span:
                                            beds = self.parse_beds(span.get_text())
                                    elif 'Baths' in text_content:
                                        # Extract baths from span content
                                        span = attribute_text.find('span')
                                        if span:
                                            baths = self.parse_baths(span.get_text())
                                    elif 'Sq. Ft.' in text_content:
                                        # Extract square footage from span content
                                        span = attribute_text.find('span')
                                        if span:
                                            sqft = self.parse_sqft(span.get_text())
                        
                        if not sqft:
                            print(f"[PacesetterMilranyPlanScraper] Skipping card {idx+1}: No square footage found")
                            continue
                        
                        # Calculate price per sqft
                        price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                        
                        # Extract image URL if available
                        image_div = card.find('div', class_='plan-card__image')
                        image_url = ""
                        if image_div:
                            img_tag = image_div.find('img')
                            if img_tag:
                                image_url = img_tag.get('src', '')
                        
                        # Extract plan detail URL
                        plan_detail_url = card.get('href', '')
                        
                        plan_data = {
                            "price": starting_price,
                            "sqft": sqft,
                            "stories": self.parse_stories(""),
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name,
                            "company": "Pacesetter Homes",
                            "community": "Milrany",
                            "type": "plan",
                            "beds": beds,
                            "baths": baths,
                            "address": "",
                            "original_price": None,
                            "price_cut": "",
                            "image_url": image_url,
                            "plan_detail_url": plan_detail_url
                        }
                        
                        print(f"[PacesetterMilranyPlanScraper] Plan {idx+1}: {plan_data}")
                        listings.append(plan_data)
                        
                    except Exception as e:
                        print(f"[PacesetterMilranyPlanScraper] Error processing card {idx+1}: {e}")
                        continue
            
            print(f"[PacesetterMilranyPlanScraper] Successfully processed {len(listings)} floor plans")
            return listings
            
        except Exception as e:
            print(f"[PacesetterMilranyPlanScraper] Error: {e}")
            return []
