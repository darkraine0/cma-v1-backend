import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class DavidHomesMaddoxNowScraper(BaseScraper):
    URL = "https://www.davidsonhomes.com/states/georgia/atlanta-market-area/hoschton/wehunt-meadows"
    
    def parse_price(self, price_text):
        """Extract price from price text."""
        if not price_text:
            return None
        # Look for patterns like "$488,990" or "$488,990 BASE PRICE"
        match = re.search(r'\$([\d,]+)', str(price_text))
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except (ValueError, TypeError):
                return None
        return None
    
    def parse_beds(self, beds_text):
        """Extract number of bedrooms from text."""
        if not beds_text:
            return ""
        # Look for patterns like "4 - 5" or "5"
        match = re.search(r'(\d+(?:\s*-\s*\d+)?)', str(beds_text))
        if match:
            return match.group(1).strip()
        return ""
    
    def parse_baths(self, baths_text):
        """Extract number of bathrooms from text."""
        if not baths_text:
            return ""
        # Look for patterns like "3 - 4" or "2.5 - 3"
        match = re.search(r'(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)', str(baths_text))
        if match:
            return match.group(1).strip()
        return ""
    
    def parse_stories(self, stories_text):
        """Extract number of stories from text."""
        if not stories_text:
            return ""
        # Look for patterns like "2" or "1"
        match = re.search(r'(\d+)', str(stories_text))
        if match:
            return match.group(1).strip()
        return ""
    
    def parse_garage(self, garage_text):
        """Extract garage information from text."""
        if not garage_text:
            return ""
        # Look for patterns like "2-3 Car Garage" or "2 car garage"
        match = re.search(r'(\d+(?:-\d+)?)\s*[Cc]ar\s*[Gg]arage', str(garage_text))
        if match:
            return match.group(1).strip()
        return ""
    
    def extract_plan_data(self, plan_wrapper):
        """Extract plan data from a single plan wrapper element."""
        try:
            # Find the content info div that contains the plan details
            content_info = plan_wrapper.find('div', class_='single_community_floor_plans_content_info')
            if not content_info:
                return None
            
            # Get the plan name from h2 tag
            name_element = content_info.find('h2')
            if not name_element:
                return None
            
            # Extract the main plan name (text not in span)
            plan_name = ""
            for text in name_element.stripped_strings:
                if text not in [span.get_text(strip=True) for span in name_element.find_all('span')]:
                    plan_name = text
                    break
            
            if not plan_name:
                # Fallback: get all text and clean it up
                plan_name = name_element.get_text(strip=True)
            
            # Extract additional info from span if present (like "Primary Suite on Main")
            span_element = name_element.find('span')
            if span_element:
                span_text = span_element.get_text(strip=True)
                if span_text and span_text not in plan_name:
                    plan_name += f" - {span_text}"
            
            # Get all paragraph elements for price, stories, beds, baths, garage
            paragraphs = content_info.find_all('p')
            
            price = None
            stories = ""
            beds = ""
            baths = ""
            garage = ""
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if 'BASE PRICE' in text:
                    price = self.parse_price(text)
                elif 'STORIES' in text:
                    stories = self.parse_stories(text)
                elif 'BEDS' in text:
                    beds = self.parse_beds(text)
                elif 'BATHS' in text:
                    baths = self.parse_baths(text)
                elif 'garage' in text.lower():
                    garage = self.parse_garage(text)
            
            # Skip if no price found
            if not price:
                return None
            
            # Estimate square footage based on beds if not available
            sqft = None
            if beds:
                try:
                    # Extract first number from beds range (e.g., "4 - 5" -> 4)
                    bed_count = int(re.search(r'(\d+)', beds).group(1))
                    if bed_count >= 5:
                        sqft = 3000  # Large homes with 5+ beds
                    elif bed_count >= 4:
                        sqft = 2500  # Medium-large homes with 4 beds
                    elif bed_count >= 3:
                        sqft = 2000  # Medium homes with 3 beds
                    else:
                        sqft = 1500  # Smaller homes
                except (ValueError, AttributeError):
                    sqft = 2000  # Default estimate
            
            # Calculate price per sqft
            price_per_sqft = round(price / sqft, 2) if sqft and sqft > 0 else None
            
            # For "now" type, we'll use the plan name as the address since these are floor plans
            address = plan_name
            
            plan_data = {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "price_per_sqft": price_per_sqft,
                "plan_name": plan_name,
                "company": "David Homes",
                "community": "Maddox",  # Updated to use Maddox as community name
                "type": "now",
                "beds": beds,
                "baths": baths,
                "address": address,
                "garage": garage
            }
            
            return plan_data
            
        except Exception as e:
            print(f"[DavidHomesMaddoxNowScraper] Error extracting plan data: {e}")
            return None
    
    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[DavidHomesMaddoxNowScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "identity",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[DavidHomesMaddoxNowScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[DavidHomesMaddoxNowScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Look for the specific wrapper class from the HTML structure provided
            plan_wrappers = soup.find_all('div', class_='single_community_floor_plans_wrapper')
            print(f"[DavidHomesMaddoxNowScraper] Found {len(plan_wrappers)} plan wrappers")
            
            if len(plan_wrappers) == 0:
                print(f"[DavidHomesMaddoxNowScraper] No plan wrappers found")
                return []
            
            return self.process_plans(plan_wrappers)
            
        except Exception as e:
            print(f"[DavidHomesMaddoxNowScraper] Error: {e}")
            return []
    
    def process_plans(self, plan_wrappers) -> List[Dict]:
        plans = []
        seen_plan_names = set()  # Track plan names to prevent duplicates
        
        for idx, wrapper in enumerate(plan_wrappers):
            try:
                print(f"[DavidHomesMaddoxNowScraper] Processing plan {idx+1}")
                
                plan_data = self.extract_plan_data(wrapper)
                if not plan_data:
                    print(f"[DavidHomesMaddoxNowScraper] Skipping plan {idx+1}: No valid data extracted")
                    continue
                
                # Check for duplicate plan names
                if plan_data['plan_name'] in seen_plan_names:
                    print(f"[DavidHomesMaddoxNowScraper] Skipping plan {idx+1}: Duplicate plan name '{plan_data['plan_name']}'")
                    continue
                
                seen_plan_names.add(plan_data['plan_name'])
                
                print(f"[DavidHomesMaddoxNowScraper] Plan {idx+1}: {plan_data}")
                plans.append(plan_data)
                
            except Exception as e:
                print(f"[DavidHomesMaddoxNowScraper] Error processing plan {idx+1}: {e}")
                continue
        
        print(f"[DavidHomesMaddoxNowScraper] Successfully processed {len(plans)} plans")
        return plans