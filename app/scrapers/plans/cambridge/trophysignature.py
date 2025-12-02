import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class TrophySignatureCambridgePlanScraper(BaseScraper):
    # URLs with different series parameters
    URLS = [
        "https://trophysignaturehomes.com/communities/dallas-ft-worth/celina/cross-creek-meadows/plans?series=ba00150dddf9db23",
        "https://trophysignaturehomes.com/communities/dallas-ft-worth/celina/cross-creek-meadows/plans?series=b9ce9fb3c2fcf462"
    ]
    
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
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text (handles 3, 3.5, 4, etc.)."""
        # Handle both "3" and "3.5" formats
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def fetch_plans(self) -> List[Dict]:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            listings = []
            seen_plan_names = set()  # Track plan names to prevent duplicates
            
            for url_idx, url in enumerate(self.URLS):
                try:
                    print(f"[TrophySignatureCambridgePlanScraper] Fetching URL {url_idx+1}/{len(self.URLS)}: {url}")
                    
                    resp = requests.get(url, headers=headers, timeout=15)
                    print(f"[TrophySignatureCambridgePlanScraper] Response status: {resp.status_code}")
                    
                    if resp.status_code != 200:
                        print(f"[TrophySignatureCambridgePlanScraper] Request failed with status {resp.status_code}")
                        continue
                    
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    
                    # Find all plan card wrappers
                    plan_cards = soup.find_all('div', class_='Results_cardWrapper')
                    print(f"[TrophySignatureCambridgePlanScraper] Found {len(plan_cards)} plan cards in URL {url_idx+1}")
                    
                    for idx, card in enumerate(plan_cards):
                        try:
                            print(f"[TrophySignatureCambridgePlanScraper] Processing card {idx+1} from URL {url_idx+1}")
                            
                            # Extract plan name from PlanCardAlt_title link
                            title_link = card.find('a', class_='PlanCardAlt_title')
                            if not title_link:
                                print(f"[TrophySignatureCambridgePlanScraper] Skipping card {idx+1}: No title link found")
                                continue
                            
                            # Get plan name - it's in the text after "The" subtitle
                            # The structure is: <a><span>The</span>Plan Name</a>
                            full_text = title_link.get_text(strip=True)
                            # Remove "The" prefix if present (case-insensitive)
                            plan_name = re.sub(r'^the\s+', '', full_text, flags=re.IGNORECASE).strip()
                            
                            if not plan_name:
                                print(f"[TrophySignatureCambridgePlanScraper] Skipping card {idx+1}: Empty plan name")
                                continue
                            
                            # Check for duplicate plan names
                            if plan_name in seen_plan_names:
                                print(f"[TrophySignatureCambridgePlanScraper] Skipping card {idx+1}: Duplicate plan name '{plan_name}'")
                                continue
                            
                            seen_plan_names.add(plan_name)
                            
                            # Extract details from PlanCardAlt_list
                            detail_list = card.find('ul', class_='PlanCardAlt_list')
                            beds = ""
                            baths = ""
                            sqft = None
                            price = None
                            
                            if detail_list:
                                detail_items = detail_list.find_all('li')
                                for item in detail_items:
                                    item_text = item.get_text(strip=True)
                                    b_tag = item.find('b')
                                    
                                    if 'Beds' in item_text and b_tag:
                                        beds = self.parse_beds(b_tag.get_text(strip=True))
                                    elif 'Baths' in item_text and b_tag:
                                        baths = self.parse_baths(b_tag.get_text(strip=True))
                                    elif 'SQ FT' in item_text and b_tag:
                                        sqft = self.parse_sqft(b_tag.get_text(strip=True))
                                    elif 'From' in item_text and b_tag:
                                        price = self.parse_price(b_tag.get_text(strip=True))
                            
                            if not price:
                                print(f"[TrophySignatureCambridgePlanScraper] Skipping card {idx+1}: No price found")
                                continue
                            
                            if not sqft:
                                print(f"[TrophySignatureCambridgePlanScraper] Skipping card {idx+1}: No square footage found")
                                continue
                            
                            # Calculate price per sqft
                            price_per_sqft = round(price / sqft, 2) if sqft > 0 else None
                            
                            # Extract image URL
                            image_url = ""
                            img_tag = card.find('img', class_='PlanCardAlt_image')
                            if img_tag and img_tag.get('src'):
                                image_url = img_tag['src']
                            
                            # Extract detail link
                            detail_link = ""
                            detail_btn = card.find('a', class_='PlanCardAlt_detailsBtn')
                            if detail_btn and detail_btn.get('href'):
                                href = detail_btn['href']
                                if href.startswith('/'):
                                    detail_link = f"https://trophysignaturehomes.com{href}"
                                else:
                                    detail_link = href
                            
                            plan_data = {
                                "price": price,
                                "sqft": sqft,
                                "stories": "1",  # Default to 1 story for Trophy Signature
                                "price_per_sqft": price_per_sqft,
                                "plan_name": plan_name,
                                "company": "Trophy Signature Homes",
                                "community": "Cambridge",
                                "type": "plan",
                                "beds": beds,
                                "baths": baths,
                                "address": "",
                                "original_price": None,
                                "price_cut": "",
                                "status": "",
                                "mls": "",
                                "sub_community": "Cross Creek Meadows",
                                "image_url": image_url,
                                "detail_link": detail_link
                            }
                            
                            print(f"[TrophySignatureCambridgePlanScraper] Plan {idx+1}: {plan_name} - ${price:,} - {sqft} sqft - {beds} beds - {baths} baths")
                            listings.append(plan_data)
                            
                        except Exception as e:
                            print(f"[TrophySignatureCambridgePlanScraper] Error processing card {idx+1} from URL {url_idx+1}: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
                
                except Exception as e:
                    print(f"[TrophySignatureCambridgePlanScraper] Error fetching URL {url_idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[TrophySignatureCambridgePlanScraper] Successfully processed {len(listings)} plans")
            return listings
            
        except Exception as e:
            print(f"[TrophySignatureCambridgePlanScraper] Error: {e}")
            import traceback
            traceback.print_exc()
            return []

