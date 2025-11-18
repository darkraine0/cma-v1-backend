import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class WatersideTownhomesEchoParkPlanScraper(BaseScraper):
    URL = "https://theprovidencegroup.com/new-homes/ga/peachtree-corners/waterside-townhomes/13809/"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        if not text:
            return None
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract price from text."""
        if not text:
            return None
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        if not text:
            return ""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        if not text:
            return ""
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        return "3"

    def parse_collection_name(self, text):
        """Extract collection name from text."""
        if not text:
            return ""
        match = re.search(r'([A-Za-z\s]+)', text)
        return match.group(1).strip() if match else ""

    def extract_plan_data(self, plan_card, community_name, city):
        """Extract data from a plan card."""
        try:
            plan_name = None
            title_elem = plan_card.find('a', class_='card-title')
            if title_elem:
                plan_name = title_elem.get_text(strip=True)

            address_elem = plan_card.find('div', class_='card-address')
            city_state = address_elem.get_text(strip=True) if address_elem else f"{city}, GA"
            address = f"{plan_name}, {city_state}"

            price = None
            price_elem = plan_card.find('div', class_='card-price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self.parse_price(price_text)

            sqft = None
            beds = ""
            baths = ""
            
            stats_section = plan_card.find('div', class_='card-stats')
            if stats_section:
                spans = stats_section.find_all('span')
                for span in spans:
                    img = span.find('img')
                    if img and img.get('alt'):
                        alt_text = img.get('alt')
                        span_text = span.get_text(strip=True)
                        
                        if 'Square Feet' in alt_text:
                            sqft = self.parse_sqft(span_text)
                        elif 'Bedrooms' in alt_text:
                            beds = self.parse_beds(span_text)
                        elif 'Baths' in alt_text:
                            baths = self.parse_baths(span_text)

            stories = self.parse_stories("")
            price_per_sqft = round(price / sqft, 2) if price and sqft and sqft > 0 else None

            collection_name = ""
            county_elem = plan_card.find('div', class_='card-county')
            if county_elem:
                strong_elem = county_elem.find('strong')
                if strong_elem:
                    collection_name = self.parse_collection_name(strong_elem.get_text())

            plan_data = {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "price_per_sqft": price_per_sqft,
                "plan_name": plan_name,
                "company": "Waterside Townhomes",
                "community": "Echo Park",
                "type": "plan",
                "beds": beds,
                "baths": baths,
                "address": address,
                "original_price": None,
                "price_cut": ""
            }

            if collection_name:
                plan_data["collection_name"] = collection_name

            return plan_data

        except Exception as e:
            print(f"[WatersideTownhomesEchoParkPlanScraper] Error extracting plan data: {e}")
            return None

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[WatersideTownhomesEchoParkPlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[WatersideTownhomesEchoParkPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[WatersideTownhomesEchoParkPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()
            
            swiper_slides = soup.find_all('div', class_='swiper-slide')
            print(f"[WatersideTownhomesEchoParkPlanScraper] Found {len(swiper_slides)} swiper slides")
            
            for idx, slide in enumerate(swiper_slides):
                try:
                    print(f"[WatersideTownhomesEchoParkPlanScraper] Processing slide {idx+1}")
                    
                    plan_card = slide.find('div', class_='plan-card')
                    if not plan_card:
                        print(f"[WatersideTownhomesEchoParkPlanScraper] Slide {idx+1}: Not a plan-card, skipping")
                        continue
                    
                    print(f"[WatersideTownhomesEchoParkPlanScraper] Slide {idx+1}: Processing plan card")
                    
                    plan_data = self.extract_plan_data(plan_card, "Echo Park", "Peachtree Corners")
                    
                    if not plan_data:
                        print(f"[WatersideTownhomesEchoParkPlanScraper] Slide {idx+1}: Failed to extract plan data")
                        continue
                    
                    if plan_data['plan_name'] in seen_plan_names:
                        print(f"[WatersideTownhomesEchoParkPlanScraper] Slide {idx+1}: Duplicate plan name '{plan_data['plan_name']}', skipping")
                        continue
                    
                    seen_plan_names.add(plan_data['plan_name'])
                    
                    if not plan_data.get('plan_name') or not plan_data.get('price'):
                        print(f"[WatersideTownhomesEchoParkPlanScraper] Slide {idx+1}: Missing required fields")
                        continue
                    
                    print(f"[WatersideTownhomesEchoParkPlanScraper] Slide {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[WatersideTownhomesEchoParkPlanScraper] Error processing slide {idx+1}: {e}")
                    continue
            
            print(f"[WatersideTownhomesEchoParkPlanScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[WatersideTownhomesEchoParkPlanScraper] Error: {e}")
            return []
