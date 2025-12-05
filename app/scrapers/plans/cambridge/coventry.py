import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class CoventryCambridgePlanScraper(BaseScraper):
    # URLs for different community sections
    URLS = [
        "https://www.coventryhomes.com/new-homes/tx/celina/hillside-village-50/",
        "https://www.coventryhomes.com/new-homes/tx/celina/hillside-village-60/",
        "https://www.coventryhomes.com/new-homes/tx/celina/cambridge-crossing-40/",
        "https://www.coventryhomes.com/new-homes/tx/celina/cambridge-crossing-60/",
    ]
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract base price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle both "2" and "2/1" formats
        match = re.search(r'(\d+(?:/\d+)?)', text)
        return str(match.group(1)) if match else ""

    def extract_community_section(self, url: str) -> str:
        """Extract community section name from URL."""
        # Extract the last part of the URL path
        # e.g., "hillside-village-50" or "cambridge-crossing-40"
        parts = url.rstrip('/').split('/')
        return parts[-1] if parts else "cambridge"
    
    def extract_plan_name_from_card(self, article) -> str:
        """Extract plan name from card-plan article."""
        # Plan name is in <p class="card-title">
        card_title = article.find('p', class_='card-title')
        if card_title:
            return card_title.get_text(strip=True)
        return ""
    
    def extract_sqft_from_card(self, article) -> int:
        """Extract square footage from card-plan article."""
        card_body = article.find('div', class_='card-body')
        if card_body:
            # Look for the paragraph with beds/baths/sqft info
            info_paragraphs = card_body.find_all('p', class_='mb-2')
            for p in info_paragraphs:
                text = p.get_text(strip=True)
                # Look for pattern like "1,977" followed by square footage icon
                # The text contains numbers separated by icons
                # Format: "4 [bed icon] 2 [bath icon] 1,977 [sqft icon]"
                sqft_match = re.search(r'([\d,]+)\s*(?:sqft|Sq\.?\s*Ft\.?)?', text, re.IGNORECASE)
                if sqft_match:
                    # Check if this number is likely sqft (usually the largest number)
                    # But we need to be smarter - look for the number before sqft icon
                    # Actually, the format shows beds, baths, then sqft
                    # So we want the last number
                    numbers = re.findall(r'([\d,]+)', text)
                    if numbers:
                        # The last number is usually sqft
                        sqft_str = numbers[-1].replace(",", "")
                        return int(sqft_str)
        return None
    
    def extract_beds_baths_from_card(self, article) -> tuple:
        """Extract beds and baths from card-plan article."""
        beds = ""
        baths = ""
        card_body = article.find('div', class_='card-body')
        if card_body:
            # Look for the paragraph with beds/baths/sqft info
            info_paragraphs = card_body.find_all('p', class_='mb-2')
            for p in info_paragraphs:
                text = p.get_text(strip=True)
                # Format: "4 [bed icon] 2 [bath icon] 1,977 [sqft icon]"
                # Extract beds (first number)
                bed_match = re.search(r'(\d+)\s*(?:bed|Beds?)', text, re.IGNORECASE)
                if bed_match:
                    beds = bed_match.group(1)
                
                # Extract baths (second number, may have format like "2/1")
                bath_match = re.search(r'(\d+(?:/\d+)?)\s*(?:bath|Baths?)', text, re.IGNORECASE)
                if bath_match:
                    baths = bath_match.group(1)
                
                if beds or baths:
                    break
        
        return beds, baths

    def fetch_plans(self) -> List[Dict]:
        all_plans = []
        seen_plan_names = set()  # Track plan names across all URLs to prevent duplicates
        
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        for url in self.URLS:
            try:
                community_section = self.extract_community_section(url)
                print(f"[CoventryCambridgePlanScraper] Fetching URL: {url} (Community: {community_section})")
                
                resp = requests.get(url, headers=headers, timeout=15)
                print(f"[CoventryCambridgePlanScraper] Response status: {resp.status_code}")
                
                if resp.status_code != 200:
                    print(f"[CoventryCambridgePlanScraper] Request failed with status {resp.status_code} for {url}")
                    continue
                
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Find the Floor Plans section
                floorplans_section = soup.find('section', id='community-floorplans')
                if not floorplans_section:
                    print(f"[CoventryCambridgePlanScraper] No 'community-floorplans' section found for {url}")
                    continue
                
                # Find all article cards with class="card-plan" - these are floor plans
                articles = floorplans_section.find_all('article', class_='card-plan')
                print(f"[CoventryCambridgePlanScraper] Found {len(articles)} floor plan cards in {community_section}")
            
                for idx, article in enumerate(articles):
                    try:
                        print(f"[CoventryCambridgePlanScraper] Processing article {idx+1} from {community_section}")
                        
                        # Extract plan name from card-title
                        plan_name = self.extract_plan_name_from_card(article)
                        if not plan_name:
                            print(f"[CoventryCambridgePlanScraper] Skipping article {idx+1}: No plan name found")
                            continue
                        
                        # Create unique key combining plan name and community section to allow same plan in different sections
                        plan_key = f"{plan_name}_{community_section}"
                        if plan_key in seen_plan_names:
                            print(f"[CoventryCambridgePlanScraper] Skipping article {idx+1}: Duplicate plan '{plan_name}' in {community_section}")
                            continue
                        
                        seen_plan_names.add(plan_key)
                        
                        # Extract base price from "From $469,990" format
                        card_body = article.find('div', class_='card-body')
                        base_price = None
                        if card_body:
                            # Look for price paragraph (usually contains "From $...")
                            price_paragraphs = card_body.find_all('p', class_='mb-2')
                            for p in price_paragraphs:
                                text = p.get_text(strip=True)
                                if 'From' in text or '$' in text:
                                    base_price = self.parse_price(text)
                                    if base_price:
                                        break
                        
                        if not base_price:
                            print(f"[CoventryCambridgePlanScraper] Skipping article {idx+1}: Could not parse price")
                            continue
                        
                        # Extract square footage
                        sqft = self.extract_sqft_from_card(article)
                        if not sqft:
                            print(f"[CoventryCambridgePlanScraper] Skipping article {idx+1}: No square footage found")
                            continue
                        
                        # Extract beds and baths
                        beds, baths = self.extract_beds_baths_from_card(article)
                        
                        # Calculate price per sqft
                        price_per_sqft = round(base_price / sqft, 2) if sqft > 0 else None
                        
                        # Determine stories based on plan size (some plans are 2-story)
                        stories = "2" if sqft > 2500 else "1"  # Larger plans tend to be 2-story
                        
                        plan_data = {
                            "price": base_price,
                            "sqft": sqft,
                            "stories": stories,
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name,
                            "company": "Coventry Homes",
                            "community": "Cambridge",
                            "community_section": community_section,
                            "type": "plan",  # This is for floor plans, not quick move-ins
                            "beds": beds,
                            "baths": baths,
                            "address": plan_name  # Use plan name as address for floor plans
                        }
                        
                        print(f"[CoventryCambridgePlanScraper] Floor Plan: {plan_data}")
                        all_plans.append(plan_data)
                        
                    except Exception as e:
                        print(f"[CoventryCambridgePlanScraper] Error processing article {idx+1}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                print(f"[CoventryCambridgePlanScraper] Processed {len(articles)} floor plans from {community_section}")
                
            except Exception as e:
                print(f"[CoventryCambridgePlanScraper] Error processing URL {url}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"[CoventryCambridgePlanScraper] Successfully processed {len(all_plans)} unique floor plans across all URLs")
        return all_plans
