import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class CoventryCambridgePlanScraper(BaseScraper):
    URL = "https://www.coventryhomes.com/new-homes/tx/celina/cambridge-crossing/"
    
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

    def is_floor_plan(self, article):
        """Check if this article represents a floor plan (has model name, not address)."""
        # Floor plans have model names in the description, not addresses
        # Quick move-in homes have addresses
        address_elem = article.find('address')
        if address_elem:
            return False  # Has address, so it's a quick move-in
        
        # Check if there's a model name/plan name mentioned
        # Look for text like "Kenedy in Cambridge Crossing 40'" or similar
        card_body = article.find('div', class_='card-body')
        if card_body:
            # Look for the last paragraph which often contains model name
            paragraphs = card_body.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                # Model names are typically mentioned like "Kenedy in Cambridge Crossing 40'"
                if 'in Cambridge Crossing' in text and not text.startswith('$'):
                    return True
        
        return False

    def fetch_plans(self) -> List[Dict]:
        try:
            print(f"[CoventryCambridgePlanScraper] Fetching URL: {self.URL}")
            
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = requests.get(self.URL, headers=headers, timeout=15)
            print(f"[CoventryCambridgePlanScraper] Response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[CoventryCambridgePlanScraper] Request failed with status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            plans = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            # Find all article cards - look for floor plans (not quick move-ins)
            articles = soup.find_all('article', class_='card-spec')
            print(f"[CoventryCambridgePlanScraper] Found {len(articles)} total article cards")
            
            for idx, article in enumerate(articles):
                try:
                    print(f"[CoventryCambridgePlanScraper] Processing article {idx+1}")
                    
                    # Check if this is a floor plan (has model name, not address)
                    if not self.is_floor_plan(article):
                        print(f"[CoventryCambridgePlanScraper] Skipping article {idx+1}: Not a floor plan (likely quick move-in)")
                        continue
                    
                    # Extract model/plan name from the description
                    card_body = article.find('div', class_='card-body')
                    if not card_body:
                        print(f"[CoventryCambridgePlanScraper] Skipping article {idx+1}: No card body found")
                        continue
                    
                    # Look for model name in paragraphs (usually the last paragraph)
                    paragraphs = card_body.find_all('p')
                    plan_name = None
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        # Model names are typically mentioned like "Kenedy in Cambridge Crossing 40'"
                        if 'in Cambridge Crossing' in text and not text.startswith('$'):
                            # Extract just the model name (before "in")
                            plan_name = text.split(' in ')[0].strip()
                            break
                    
                    if not plan_name:
                        print(f"[CoventryCambridgePlanScraper] Skipping article {idx+1}: No model name found")
                        continue
                    
                    # Check for duplicate plan names
                    if plan_name in seen_plan_names:
                        print(f"[CoventryCambridgePlanScraper] Skipping article {idx+1}: Duplicate plan name '{plan_name}'")
                        continue
                    
                    seen_plan_names.add(plan_name)
                    
                    # Extract base price - try data attribute first, then fall back to text
                    base_price = None
                    if article.get('data-price'):
                        base_price = int(article.get('data-price'))
                    else:
                        price_elem = article.find('p', class_='display-6')
                        if price_elem:
                            base_price = self.parse_price(price_elem.get_text(strip=True))
                    
                    if not base_price:
                        print(f"[CoventryCambridgePlanScraper] Skipping article {idx+1}: Could not parse price")
                        continue
                    
                    # Extract square footage - try data attribute first, then fall back to text
                    sqft = None
                    if article.get('data-square-feet'):
                        sqft = int(article.get('data-square-feet'))
                    else:
                        # Try to extract from the info text
                        info_elem = article.find('p', class_='mb-2')
                        if info_elem:
                            info_text = info_elem.get_text(strip=True)
                            # Look for pattern like "2,994 sqft"
                            sqft_match = re.search(r'([\d,]+)\s*sqft', info_text, re.IGNORECASE)
                            if sqft_match:
                                sqft = int(sqft_match.group(1).replace(",", ""))
                    
                    if not sqft:
                        print(f"[CoventryCambridgePlanScraper] Skipping article {idx+1}: No square footage found")
                        continue
                    
                    # Extract beds and baths from the info text
                    beds = ""
                    baths = ""
                    info_elem = article.find('p', class_='mb-2')
                    if info_elem:
                        info_text = info_elem.get_text(strip=True)
                        # Parse format like "4 bed · 3 bath · 2,994 sqft"
                        bed_match = re.search(r'(\d+)\s*bed', info_text, re.IGNORECASE)
                        if bed_match:
                            beds = bed_match.group(1)
                        
                        bath_match = re.search(r'(\d+(?:/\d+)?)\s*bath', info_text, re.IGNORECASE)
                        if bath_match:
                            baths = bath_match.group(1)
                    
                    # Calculate price per sqft
                    price_per_sqft = round(base_price / sqft, 2) if sqft > 0 else None
                    
                    # Determine stories based on plan name or size (some plans are 2-story)
                    stories = "2" if sqft > 2500 else "1"  # Larger plans tend to be 2-story
                    
                    plan_data = {
                        "price": base_price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": plan_name,
                        "company": "Coventry Homes",
                        "community": "Cambridge",
                        "type": "plan",  # This is for floor plans, not quick move-ins
                        "beds": beds,
                        "baths": baths,
                        "address": plan_name  # Use plan name as address for floor plans
                    }
                    
                    print(f"[CoventryCambridgePlanScraper] Floor Plan: {plan_data}")
                    plans.append(plan_data)
                    
                except Exception as e:
                    print(f"[CoventryCambridgePlanScraper] Error processing article {idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[CoventryCambridgePlanScraper] Successfully processed {len(plans)} unique floor plans")
            return plans
            
        except Exception as e:
            print(f"[CoventryCambridgePlanScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
