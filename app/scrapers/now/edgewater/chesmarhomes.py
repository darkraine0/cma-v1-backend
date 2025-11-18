import requests
import re
from ...base import BaseScraper
from typing import List, Dict

class ChesmarHomesEdgewaterNowScraper(BaseScraper):
    def __init__(self):
        self.base_url = "https://chesmar.com/wp-json/chesmar/search/"
        self.headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://chesmar.com",
            "referer": "https://chesmar.com/communities/avondale/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest"
        }
        self.community_id = "59907"  # Avondale community ID

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
        # Extract numbers from text like "1,653 sqft" or just "1653"
        match = re.search(r'(\d+(?:,\d+)?)', str(sqft_text))
        if match:
            sqft_str = match.group(1).replace(",", "")
            try:
                return int(sqft_str)
            except (ValueError, TypeError):
                return None
        return None

    def parse_beds_baths(self, beds_text, baths_text):
        """Extract beds and baths from separate text fields."""
        beds = str(beds_text) if beds_text else ""
        baths = str(baths_text) if baths_text else ""
        return beds, baths

    def fetch_plans(self) -> List[Dict]:
        """Fetch plans and now items from Chesmar Homes Edgewater community."""
        try:
            print("[ChesmarHomesEdgewaterNowScraper] Starting to fetch Chesmar Homes data for Edgewater")
            
            # Prepare the form data for the API request
            form_data = {
                "city": "",
                "state": "",
                "zip": "",
                "lat": "",
                "lng": "",
                "search": "",
                "bedrooms": "",
                "bathrooms": "",
                "price": "",
                "footage": "",
                "community": "",
                "home_type": "",
                "featured": "false",
                "ready": "false",
                "amenities[pool]": "false",
                "amenities[playground]": "false",
                "amenities[fishing]": "false",
                "amenities[fitness_center]": "false",
                "amenities[lake]": "false",
                "amenities[park]": "false",
                "amenities[trails]": "false",
                "amenities[dog_park]": "false",
                "amenities[school_zone]": "false",
                "mode": "community",
                "community_id": self.community_id
            }
            
            response = requests.post(self.base_url, headers=self.headers, data=form_data, timeout=15)
            
            if response.status_code != 200:
                print(f"[ChesmarHomesEdgewaterNowScraper] Request failed with status {response.status_code}")
                return []
            
            data = response.json()
            
            if not data.get("successes"):
                print("[ChesmarHomesEdgewaterNowScraper] No successful responses in API data")
                return []
            
            all_listings = []
            
            # Process the first successful response
            success_data = data["successes"][0]
            
            # Process floorplans (plans)
            floorplans = success_data.get("floorplans", [])
            print(f"[ChesmarHomesEdgewaterNowScraper] Found {len(floorplans)} floorplans")
            
            for floorplan in floorplans:
                try:
                    price = self.parse_price(floorplan.get("price"))
                    sqft = self.parse_sqft(floorplan.get("sq_footage"))
                    beds, baths = self.parse_beds_baths(floorplan.get("bedrooms"), floorplan.get("bathrooms"))
                    
                    # Calculate price per sqft
                    price_per_sqft = None
                    if price and sqft and sqft > 0:
                        price_per_sqft = round(price / sqft, 2)
                    
                    # Determine stories
                    stories = floorplan.get("stories", "1")
                    
                    # Create plan data
                    plan_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": stories,
                        "price_per_sqft": price_per_sqft,
                        "plan_name": floorplan.get("name", ""),
                        "company": "ChesmarHomes",
                        "community": "Edgewater",
                        "type": "plan",
                        "beds": beds,
                        "baths": baths,
                        "address": "",  # Plans don't have specific addresses
                        "design_number": floorplan.get("plan_number", ""),
                        "description": floorplan.get("description", "")
                    }
                    
                    # Only include plans with essential data
                    if price and sqft and plan_data["plan_name"]:
                        print(f"[ChesmarHomesEdgewaterNowScraper] Processed plan: {plan_data['plan_name']} - ${price:,}")
                        all_listings.append(plan_data)
                    else:
                        print(f"[ChesmarHomesEdgewaterNowScraper] Skipping plan {plan_data['plan_name']} due to missing essential data")
                        
                except Exception as e:
                    print(f"[ChesmarHomesEdgewaterNowScraper] Error processing floorplan: {e}")
                    continue
            
            # Process movins (now items)
            movins = success_data.get("movins", [])
            print(f"[ChesmarHomesEdgewaterNowScraper] Found {len(movins)} move-in ready homes")
            
            for movin in movins:
                try:
                    price = self.parse_price(movin.get("price"))
                    beds, baths = self.parse_beds_baths(movin.get("bedrooms"), movin.get("bathrooms_override") or movin.get("bathrooms"))
                    
                    # For movins, we don't have sqft in the main data, so we'll need to estimate or skip
                    sqft = None
                    # Try to extract sqft from description if available
                    description = movin.get("description", "")
                    if description:
                        sqft_match = re.search(r'(\d+(?:,\d+)?)\s*sq\.?\s*ft', description, re.IGNORECASE)
                        if sqft_match:
                            sqft = self.parse_sqft(sqft_match.group(1))
                    
                    # Calculate price per sqft
                    price_per_sqft = None
                    if price and sqft and sqft > 0:
                        price_per_sqft = round(price / sqft, 2)
                    
                    # Create movin data
                    movin_data = {
                        "price": price,
                        "sqft": sqft,
                        "stories": "1",  # Default to 1 story for single-family homes
                        "price_per_sqft": price_per_sqft,
                        "plan_name": movin.get("name", ""),  # Use name as plan_name for now items
                        "company": "ChesmarHomes",
                        "community": "Edgewater",
                        "type": "now",
                        "beds": beds,
                        "baths": baths,
                        "address": movin.get("name", ""),  # Use name as address for now items
                        "design_number": movin.get("mls", ""),  # Use MLS as design number
                        "description": movin.get("description", ""),
                        "status": movin.get("available", "Available")
                    }
                    
                    # Only include movins with essential data
                    if price and movin_data["plan_name"]:
                        print(f"[ChesmarHomesEdgewaterNowScraper] Processed movin: {movin_data['plan_name']} - ${price:,}")
                        all_listings.append(movin_data)
                    else:
                        print(f"[ChesmarHomesEdgewaterNowScraper] Skipping movin {movin_data['plan_name']} due to missing essential data")
                        
                except Exception as e:
                    print(f"[ChesmarHomesEdgewaterNowScraper] Error processing movin: {e}")
                    continue
            
            print(f"[ChesmarHomesEdgewaterNowScraper] Successfully processed {len(all_listings)} total listings")
            return all_listings
            
        except Exception as e:
            print(f"[ChesmarHomesEdgewaterNowScraper] Error: {e}")
            return []
