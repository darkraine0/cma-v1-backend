import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from ...price_utils import parse_price_with_thousands
from typing import List, Dict

class ChafinCommunitiesMaddoxPlanScraper(BaseScraper):
    URL = "https://www.chafincommunities.com/communities/georgia/jackson/hochston-jackson/rosewood-lakes/"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        # Look for patterns like "2,500 Sq Ft" or "2500 Sq Ft"
        match = re.search(r'([\d,]+)\s*Sq\.?\s*Ft\.?', text, re.IGNORECASE)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract starting price from text."""
        # Use the utility function to handle thousands notation
        return parse_price_with_thousands(text)

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        # Look for patterns like "4 - 5" or "3" beds
        match = re.search(r'(\d+(?:\s*-\s*\d+)?)\s*BEDS?', text, re.IGNORECASE)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Look for patterns like "3 - 4" or "2.5" baths
        match = re.search(r'(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)\s*BATHS?', text, re.IGNORECASE)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        # Look for patterns like "2 STORIES" or "1 STORY"
        match = re.search(r'(\d+)\s*STORIES?', text, re.IGNORECASE)
        return str(match.group(1)) if match else ""

    def parse_garage(self, text):
        """Extract garage information from text."""
        # Look for patterns like "2-3 Car Garage" or "2 car garage"
        match = re.search(r'(\d+(?:-\d+)?)\s*[Cc]ar\s*[Gg]arage', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[ChafinCommunitiesMaddoxPlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[ChafinCommunitiesMaddoxPlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[ChafinCommunitiesMaddoxPlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all floor plan wrappers
            floor_plan_wrappers = soup.find_all('div', class_='single_community_floor_plans_wrapper')
            print(f"[ChafinCommunitiesMaddoxPlanScraper] Found {len(floor_plan_wrappers)} floor plan wrappers")
            
            for idx, wrapper in enumerate(floor_plan_wrappers):
                try:
                    print(f"[ChafinCommunitiesMaddoxPlanScraper] Processing wrapper {idx+1}")
                    
                    # Find the plan info section
                    plan_info = wrapper.find('div', class_='single_community_floor_plans_content_info')
                    if not plan_info:
                        print(f"[ChafinCommunitiesMaddoxPlanScraper] Skipping wrapper {idx+1}: No plan info found")
                        continue
                    
                    # Extract plan name from h2
                    plan_name_h2 = plan_info.find('h2')
                    if not plan_name_h2:
                        print(f"[ChafinCommunitiesMaddoxPlanScraper] Skipping wrapper {idx+1}: No plan name found")
                        continue
                    
                    plan_name = plan_name_h2.get_text(strip=True)
                    # Remove any additional text like "Primary Suite on Main"
                    if '<span>' in str(plan_name_h2):
                        # Get only the direct text content, not from span elements
                        plan_name = plan_name_h2.find(text=True, recursive=False)
                        if plan_name:
                            plan_name = plan_name.strip()
                        else:
                            # Fallback: get all text and remove span content
                            plan_name = plan_name_h2.get_text(strip=True)
                            # Remove common additional text patterns
                            plan_name = re.sub(r'\s*Primary Suite on Main.*', '', plan_name)
                            plan_name = plan_name.strip()
                    
                    if not plan_name:
                        print(f"[ChafinCommunitiesMaddoxPlanScraper] Skipping wrapper {idx+1}: Empty plan name")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[ChafinCommunitiesMaddoxPlanScraper] Skipping wrapper {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract all p tags with plan details
                    p_tags = plan_info.find_all('p')
                    starting_price = None
                    beds = ""
                    baths = ""
                    stories = ""
                    garage = ""
                    
                    for p_tag in p_tags:
                        text = p_tag.get_text(strip=True)
                        
                        # Extract price
                        price_match = self.parse_price(text)
                        if price_match and not starting_price:
                            starting_price = price_match
                        
                        # Extract beds
                        beds_match = self.parse_beds(text)
                        if beds_match:
                            beds = beds_match
                        
                        # Extract baths
                        baths_match = self.parse_baths(text)
                        if baths_match:
                            baths = baths_match
                        
                        # Extract stories
                        stories_match = self.parse_stories(text)
                        if stories_match:
                            stories = stories_match
                        
                        # Extract garage
                        garage_match = self.parse_garage(text)
                        if garage_match:
                            garage = garage_match
                    
                    if not starting_price:
                        print(f"[ChafinCommunitiesMaddoxPlanScraper] Skipping wrapper {idx+1}: No starting price found")
                        continue
                    
                    # Try to extract square footage from plan images or other sources
                    sqft = None
                    
                    # Look for square footage in the plan content block
                    plan_content_block = wrapper.find('div', class_='single_community_floor_plans_content_block')
                    if plan_content_block:
                        # Check if there are any images with square footage in alt text or data attributes
                        images = plan_content_block.find_all('img')
                        for img in images:
                            alt_text = img.get('alt', '')
                            sqft_match = self.parse_sqft(alt_text)
                            if sqft_match:
                                sqft = sqft_match
                                break
                    
                    # If no square footage found, estimate based on plan characteristics
                    if not sqft:
                        # Estimate square footage based on beds and plan type
                        if beds:
                            bed_count = int(beds.split('-')[0].strip()) if '-' in beds else int(beds)
                            if bed_count >= 5:
                                sqft = 3000  # Large homes with 5+ beds
                            elif bed_count >= 4:
                                sqft = 2500  # Medium-large homes with 4 beds
                            elif bed_count >= 3:
                                sqft = 2000  # Medium homes with 3 beds
                            else:
                                sqft = 1500  # Smaller homes
                        else:
                            sqft = 2000  # Default estimate
                        
                        print(f"[ChafinCommunitiesMaddoxPlanScraper] Estimated square footage for plan '{plan_name}': {sqft}")
                    
                    # Calculate price per sqft
                    price_per_sqft = round(starting_price / sqft, 2) if sqft > 0 else None
                    
                    # Extract address (same as plan name for floor plans)
                    address = plan_name
                    
                    plan_data = {
                        "price": starting_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Chafin Communities",
                        "community": "Maddox",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "original_price": None,
                        "price_cut": ""
                    }
                    
                    print(f"[ChafinCommunitiesMaddoxPlanScraper] Wrapper {idx+1}: {plan_data}")
                    listings.append(plan_data)
                    
                except Exception as e:
                    print(f"[ChafinCommunitiesMaddoxPlanScraper] Error processing wrapper {idx+1}: {e}")
                    continue
            
            print(f"[ChafinCommunitiesMaddoxPlanScraper] Successfully processed {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"[ChafinCommunitiesMaddoxPlanScraper] Error: {e}")
            return []
