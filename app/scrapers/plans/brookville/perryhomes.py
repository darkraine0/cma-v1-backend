import requests
import re
from bs4 import BeautifulSoup
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
        try:
            print(f"[PerryHomesBrookvillePlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[PerryHomesBrookvillePlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[PerryHomesBrookvillePlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            plans = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all home listings to extract floor plan information
            home_listings = soup.find_all('li', class_=lambda x: x and 'id' in x)
            print(f"[PerryHomesBrookvillePlanScraper] Found {len(home_listings)} home listings")
            
            for idx, listing in enumerate(home_listings):
                try:
                    print(f"[PerryHomesBrookvillePlanScraper] Processing listing {idx+1}")
                    
                    # Extract plan name from the community link
                    plan_name = ""
                    community_link = listing.find('a', href=re.compile(r'/devonshire-reserve'))
                    if community_link:
                        plan_name = community_link.get_text(strip=True)
                    else:
                        # Try to extract from design information
                        design_div = listing.find('div', string=re.compile(r'Design.*'))
                        if design_div:
                            plan_name = design_div.get_text(strip=True)
                        else:
                            print(f"[PerryHomesBrookvillePlanScraper] Skipping listing {idx+1}: No plan name found")
                            continue
                    
                    if not plan_name:
                        print(f"[PerryHomesBrookvillePlanScraper] Skipping listing {idx+1}: Empty plan name")
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
            return []
