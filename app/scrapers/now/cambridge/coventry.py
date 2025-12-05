import requests
import re
import json
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class CoventryCambridgeNowScraper(BaseScraper):
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
        """Extract current price from text."""
        # Look for the current price (not the strikethrough price)
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_original_price(self, text):
        """Extract original price from strikethrough text."""
        # Look for the strikethrough price (was price)
        match = re.search(r'Was \$([\d,]+)', text)
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

    def parse_savings(self, text):
        """Extract savings amount from text like '$65K'."""
        # Handle formats like "$65K", "$65,000", etc.
        match = re.search(r'\$([\d,]+)K?', text)
        if match:
            value = match.group(1).replace(",", "")
            # If it ends with K (implicit), multiply by 1000
            if 'K' in text.upper():
                return int(value) * 1000
            return int(value)
        return None

    def is_quick_move_in(self, article):
        """Check if this article represents a quick move-in home (has address)."""
        # Quick move-in homes have addresses, floor plans have model names
        address_elem = article.find('address')
        return address_elem is not None

    def extract_community_section(self, url: str) -> str:
        """Extract community section name from URL."""
        # Extract the last part of the URL path
        # e.g., "hillside-village-50" or "cambridge-crossing-40"
        parts = url.rstrip('/').split('/')
        return parts[-1] if parts else "cambridge"
    
    def extract_status(self, article) -> str:
        """Extract status (Move-In Ready, Under Construction, etc.)"""
        status_elem = article.find('p', class_='status')
        if status_elem:
            status_text = status_elem.get_text(strip=True)
            # Remove badge span content (badge-status-1, badge-status-2, etc.), keep the text after it
            badge = status_elem.find('span', class_=re.compile(r'badge-status'))
            if badge:
                status_text = status_text.replace(badge.get_text(strip=True), '').strip()
            return status_text
        return ""
    
    def extract_homesite(self, article) -> str:
        """Extract homesite number."""
        homesite_elem = article.find('p', class_='text-primary')
        if homesite_elem:
            homesite_text = homesite_elem.get_text(strip=True)
            # Format: "Homesite #C-24-1A"
            if homesite_text.startswith('Homesite'):
                return homesite_text.replace('Homesite', '').strip()
            return homesite_text
        return ""
    
    def extract_plan_name(self, article) -> str:
        """Extract plan name from the article."""
        card_body = article.find('div', class_='card-body')
        if card_body:
            # Look for the last paragraph which contains plan name like "Easton in Hillside Village 50'"
            paragraphs = card_body.find_all('p')
            for p in reversed(paragraphs):  # Start from the end
                text = p.get_text(strip=True)
                # Plan names are typically mentioned like "Easton in Hillside Village 50'"
                if ' in ' in text and not text.startswith('$') and 'Homesite' not in text:
                    # Extract just the plan name (before "in")
                    plan_name = text.split(' in ')[0].strip()
                    return plan_name
        return ""
    
    def fetch_plans(self) -> List[Dict]:
        all_listings = []
        seen_addresses = set()  # Track addresses across all URLs to prevent duplicates
        
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
                print(f"[CoventryCambridgeNowScraper] Fetching URL: {url} (Community: {community_section})")
                
                resp = requests.get(url, headers=headers, timeout=15)
                print(f"[CoventryCambridgeNowScraper] Response status: {resp.status_code}")
                
                if resp.status_code != 200:
                    print(f"[CoventryCambridgeNowScraper] Request failed with status {resp.status_code} for {url}")
                    continue
                
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Find the Quick Move-In Homes section
                available_homes_section = soup.find('section', id='community-available-homes')
                if not available_homes_section:
                    print(f"[CoventryCambridgeNowScraper] No 'community-available-homes' section found for {url}")
                    continue
                
                # Find all article cards in the Quick Move-In Homes section
                articles = available_homes_section.find_all('article', class_='card-spec')
                print(f"[CoventryCambridgeNowScraper] Found {len(articles)} quick move-in home cards in {community_section}")
            
                for idx, article in enumerate(articles):
                    try:
                        print(f"[CoventryCambridgeNowScraper] Processing article {idx+1} from {community_section}")
                        
                        # Extract address
                        address_elem = article.find('address')
                        if not address_elem:
                            print(f"[CoventryCambridgeNowScraper] Skipping article {idx+1}: No address found")
                            continue
                        
                        address = address_elem.get_text(strip=True)
                        if not address:
                            print(f"[CoventryCambridgeNowScraper] Skipping article {idx+1}: Empty address")
                            continue
                        
                        # Check for duplicate addresses across all URLs
                        if address in seen_addresses:
                            print(f"[CoventryCambridgeNowScraper] Skipping article {idx+1}: Duplicate address '{address}'")
                            continue
                        
                        seen_addresses.add(address)
                        
                        # Extract price - try data attribute first, then fall back to text
                        current_price = None
                        if article.get('data-price'):
                            current_price = int(article.get('data-price'))
                        else:
                            price_elem = article.find('p', class_='display-6')
                            if price_elem:
                                current_price = self.parse_price(price_elem.get_text(strip=True))
                        
                        if not current_price:
                            print(f"[CoventryCambridgeNowScraper] Skipping article {idx+1}: No current price found")
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
                            print(f"[CoventryCambridgeNowScraper] Skipping article {idx+1}: No square footage found")
                            continue
                        
                        # Extract beds and baths from the info text
                        beds = ""
                        baths = ""
                        info_elem = article.find('p', class_='mb-2')
                        if info_elem:
                            info_text = info_elem.get_text(strip=True)
                            # Parse format like "4 bed · 3/1 bath · 2,994 sqft"
                            bed_match = re.search(r'(\d+)\s*bed', info_text, re.IGNORECASE)
                            if bed_match:
                                beds = bed_match.group(1)
                            
                            bath_match = re.search(r'(\d+(?:/\d+)?)\s*bath', info_text, re.IGNORECASE)
                            if bath_match:
                                baths = bath_match.group(1)
                        
                        # Extract status
                        status = self.extract_status(article)
                        
                        # Extract homesite number
                        homesite = self.extract_homesite(article)
                        
                        # Extract plan name
                        plan_name = self.extract_plan_name(article)
                        
                        # Extract savings/price reduction if present
                        savings_badge = article.find('span', class_='badge')
                        price_reduction = None
                        original_price = None
                        if savings_badge and 'bg-red' in savings_badge.get('class', []):
                            savings_text = savings_badge.get_text(strip=True)
                            price_reduction = self.parse_savings(savings_text)
                            if price_reduction:
                                original_price = current_price + price_reduction
                        
                        # Calculate price per sqft
                        price_per_sqft = round(current_price / sqft, 2) if sqft > 0 else None
                        
                        # Determine if it's a price cut
                        price_cut_text = ""
                        if price_reduction:
                            price_cut_text = f"Price cut: ${price_reduction:,}"
                        
                        plan_data = {
                            "price": current_price,
                            "sqft": sqft,
                            "stories": "1",  # Default to 1 story for single-family homes
                            "price_per_sqft": price_per_sqft,
                            "plan_name": plan_name or address,  # Use plan name if available, otherwise address
                            "company": "Coventry Homes",
                            "community": "Cambridge",
                            "community_section": community_section,
                            "type": "now",
                            "beds": beds,
                            "baths": baths,
                            "address": address,
                            "status": status,
                            "homesite": homesite,
                            "original_price": original_price,
                            "price_cut": price_cut_text
                        }
                        
                        print(f"[CoventryCambridgeNowScraper] Article {idx+1}: {plan_data}")
                        all_listings.append(plan_data)
                        
                    except Exception as e:
                        print(f"[CoventryCambridgeNowScraper] Error processing article {idx+1}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                print(f"[CoventryCambridgeNowScraper] Processed {len(articles)} articles from {community_section}")
                
            except Exception as e:
                print(f"[CoventryCambridgeNowScraper] Error processing URL {url}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"[CoventryCambridgeNowScraper] Successfully processed {len(all_listings)} unique quick move-in homes across all URLs")
        return all_listings
