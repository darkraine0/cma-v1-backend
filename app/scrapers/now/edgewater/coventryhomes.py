import requests
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict
import re

class CoventryHomesEdgewaterNowScraper(BaseScraper):
    def __init__(self):
        self.base_url = "https://www.coventryhomes.com/new-homes/tx/fate/avondale/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

    def parse_price(self, price_text):
        """Extract price from price text."""
        if not price_text:
            return None
        # Remove $ and commas, then convert to integer
        price_str = str(price_text).replace("$", "").replace(",", "")
        try:
            return int(float(price_str))
        except (ValueError, TypeError):
            return None

    def parse_sqft(self, sqft_text):
        """Extract square footage from text."""
        if not sqft_text:
            return None
        # Extract numbers from text like "1,653 sqft"
        match = re.search(r'(\d+(?:,\d+)?)', str(sqft_text))
        if match:
            sqft_str = match.group(1).replace(",", "")
            try:
                return int(sqft_str)
            except (ValueError, TypeError):
                return None
        return None

    def parse_beds_baths(self, text):
        """Extract beds and baths from text like '3 bed · 2 bath'."""
        if not text:
            return "", ""
        
        text_str = str(text)
        beds = ""
        baths = ""
        
        # Extract beds
        beds_match = re.search(r'(\d+)\s*bed', text_str)
        if beds_match:
            beds = beds_match.group(1)
        
        # Extract baths
        baths_match = re.search(r'(\d+)\s*bath', text_str)
        if baths_match:
            baths = baths_match.group(1)
        
        return beds, baths

    def parse_address(self, address_element):
        """Extract address from address element."""
        if not address_element:
            return ""
        
        # Get all text content and clean it up
        address_text = address_element.get_text(strip=True)
        
        # Remove extra whitespace, newlines, and clean up the formatting
        # Replace multiple whitespace with single space
        address_text = re.sub(r'\s+', ' ', address_text)
        
        # Remove trailing commas and clean up
        address_text = address_text.strip()
        address_text = re.sub(r',\s*$', '', address_text)  # Remove trailing comma
        
        # Clean up any remaining formatting issues
        address_text = re.sub(r'\s+', ' ', address_text).strip()
        
        return address_text

    def parse_status(self, status_element):
        """Extract status from status element."""
        if not status_element:
            return "Available"
        
        status_text = status_element.get_text(strip=True)
        if "Under Construction" in status_text:
            return "Under Construction"
        elif "Move-In Ready" in status_text:
            return "Move-In Ready"
        else:
            return "Available"

    def fetch_plans(self) -> List[Dict]:
        """Fetch plans from CoventryHomes Edgewater community."""
        try:
            print("[CoventryHomesEdgewaterNowScraper] Starting to fetch CoventryHomes data for Edgewater")
            
            response = requests.get(self.base_url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                print(f"[CoventryHomesEdgewaterNowScraper] Request failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find the container div first
            container = soup.find('div', class_='row justify-content-center mt-4 d-none d-md-flex')
            if container:
                # Find all home listings within the container
                home_listings = container.find_all('article', class_='card-spec')
            else:
                # Fallback: search entire page
                home_listings = soup.find_all('article', class_='card-spec')
            
            # Fallback: if no articles found, try using elements with data-price attribute
            if len(home_listings) == 0:
                price_elements = soup.find_all(attrs={'data-price': True})
                if len(price_elements) > 0:
                    home_listings = price_elements
            
            print(f"[CoventryHomesEdgewaterNowScraper] Found {len(home_listings)} home listings")
            
            all_listings = []
            
            for idx, listing in enumerate(home_listings):
                try:
                    # Extract price from data attribute or display text
                    price = None
                    price_data = listing.get('data-price')
                    if price_data:
                        price = self.parse_price(price_data)
                    
                    if not price:
                        # Try to find price in display text
                        price_element = listing.find('p', class_='display-6')
                        if price_element:
                            price = self.parse_price(price_element.get_text())
                    
                    # Extract square footage from data attribute or text
                    sqft = None
                    sqft_data = listing.get('data-square-feet')
                    if sqft_data:
                        sqft = self.parse_sqft(sqft_data)
                    
                    if not sqft:
                        # Try to find sqft in text
                        sqft_text = listing.find(text=re.compile(r'\d+,\d+\s*sqft'))
                        if sqft_text:
                            sqft = self.parse_sqft(sqft_text)
                        else:
                            # Try to find sqft in any paragraph
                            all_paragraphs = listing.find_all('p')
                            for p in all_paragraphs:
                                p_text = p.get_text()
                                if 'sqft' in p_text.lower():
                                    sqft = self.parse_sqft(p_text)
                                    break
                    
                    # Extract beds and baths
                    beds = ""
                    baths = ""
                    # Look for the paragraph that contains beds/baths info
                    beds_baths_element = listing.find('p')
                    if beds_baths_element:
                        # Check if this paragraph contains bed/bath info
                        text = beds_baths_element.get_text()
                        if 'bed' in text.lower() or 'bath' in text.lower():
                            beds, baths = self.parse_beds_baths(text)
                        else:
                            # Try to find the correct paragraph
                            all_paragraphs = listing.find_all('p')
                            for p in all_paragraphs:
                                p_text = p.get_text()
                                if 'bed' in p_text.lower() or 'bath' in p_text.lower():
                                    beds, baths = self.parse_beds_baths(p_text)
                                    break
                    
                    # Extract address
                    address = ""
                    address_element = listing.find('address')
                    if address_element:
                        address = self.parse_address(address_element)
                    
                    # Extract status
                    status = "Available"
                    status_element = listing.find('p', class_='status')
                    if status_element:
                        status = self.parse_status(status_element)
                    
                    # Extract plan name (from the text after address)
                    plan_name = ""
                    plan_element = listing.find('p', class_='text-primary')
                    if plan_element:
                        plan_name = plan_element.get_text(strip=True)
                    
                    # Extract community/section name
                    community_name = ""
                    all_paragraphs = listing.find_all('p')
                    for p in all_paragraphs:
                        p_text = p.get_text(strip=True)
                        if "in Avondale" in p_text:
                            community_name = p_text
                            break
                    
                    # Calculate price per sqft
                    price_per_sqft = None
                    if price and sqft and sqft > 0:
                        price_per_sqft = round(price / sqft, 2)
                    
                    # Create listing data
                    listing_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": "1",  # Default to 1 story for single-family homes
                        "price_per_sqft": price_per_sqft,
                        "plan_name": address,  # For "now" type, use address as plan name
                        "company": "CoventryHomes",
                        "community": "Edgewater",
                        "type": "now",  # These are all "now" items since they have addresses
                        "beds": beds,
                        "baths": baths,
                        "address": address,
                        "status": status,
                        "community_section": community_name
                    }
                    
                    # Only include listings with essential data
                    if price and sqft and address:
                        print(f"[CoventryHomesEdgewaterNowScraper] Processed listing {idx+1}: {listing_data['plan_name']} - ${price:,}")
                        all_listings.append(listing_data)
                    else:
                        print(f"[CoventryHomesEdgewaterNowScraper] Skipping listing {idx+1} due to missing essential data")
                        
                except Exception as e:
                    print(f"[CoventryHomesEdgewaterNowScraper] Error processing listing {idx+1}: {e}")
                    continue
            
            print(f"[CoventryHomesEdgewaterNowScraper] Successfully processed {len(all_listings)} listings")
            return all_listings
            
        except Exception as e:
            print(f"[CoventryHomesEdgewaterNowScraper] Error: {e}")
            return []
