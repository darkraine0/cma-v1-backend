import requests
import json
from ...base import BaseScraper
from typing import List, Dict

class PerryHomesEdgewaterNowScraper(BaseScraper):
    # Algolia API endpoints for the two different sections
    ALGOLIA_URL = "https://puet3rs3pk-1.algolianet.com/1/indexes/*/queries"
    ALGOLIA_API_KEY = "7671b9eb91d30b9bcaf2d3b48bb13973"
    ALGOLIA_APP_ID = "PUET3RS3PK"
    
    def __init__(self):
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Origin": "https://www.perryhomes.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "content-type": "application/x-www-form-urlencoded",
            "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        }

    def parse_price(self, price_value):
        """Extract price from the listing price field."""
        if not price_value:
            return None
        # Remove any non-numeric characters except decimal points
        price_str = str(price_value).replace(",", "").replace("$", "")
        try:
            return int(float(price_str))
        except (ValueError, TypeError):
            return None

    def parse_sqft(self, sqft_value):
        """Extract square footage from the sqFt field."""
        if not sqft_value:
            return None
        try:
            return int(sqft_value)
        except (ValueError, TypeError):
            return None

    def parse_stories(self, stories_value):
        """Extract number of stories."""
        if not stories_value:
            return "1"  # Default to 1 story
        return str(stories_value)

    def make_algolia_request(self, section_name: str) -> Dict:
        """Make a request to Algolia API for a specific section."""
        params = {
            "x-algolia-agent": "Algolia for JavaScript (4.24.0); Browser (lite); instantsearch.js (4.72.2); react (18.3.0-canary-14898b6a9-20240318); react-instantsearch (7.11.4); react-instantsearch-core (7.11.4); next.js (14.2.3); JS Helper (3.22.1)",
            "x-algolia-api-key": self.ALGOLIA_API_KEY,
            "x-algolia-application-id": self.ALGOLIA_APP_ID
        }
        
        # Build the request body
        request_body = {
            "requests": [{
                "indexName": "production-inventory-sections-page",
                "params": f"facets=%5B%22baths%22%2C%22bedrooms%22%2C%22designNumber%22%2C%22garages%22%2C%22homeOptions%22%2C%22listingPrice%22%2C%22productionPhase%22%2C%22sqFt%22%2C%22stories%22%2C%22virtualAssets.name%22%5D&filters=%22perry_homes%22%20AND%20market%3A%22Dallas%20-%20Fort%20Worth%22%20AND%20section.name%3A%22{section_name}%22%20AND%20NOT%20productionPhase%3ASold%20AND%20NOT%20productionPhase%3A%22Model%20Home%22&highlightPostTag=__%2Fais-highlight__&highlightPreTag=__ais-highlight__&hitsPerPage=100&maxValuesPerFacet=200&page=0"
            }]
        }
        
        try:
            response = requests.post(
                self.ALGOLIA_URL,
                headers=self.headers,
                params=params,
                json=request_body,
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[PerryHomesEdgewaterNowScraper] Request failed for {section_name} with status {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"[PerryHomesEdgewaterNowScraper] Error making request for {section_name}: {e}")
            return {}

    def process_hit(self, hit: Dict, section_name: str) -> Dict:
        """Process a single hit from the Algolia response."""
        try:
            # Extract basic information
            address_data = hit.get('address', {})
            address = ""
            if address_data:
                address_parts = []
                if address_data.get('address1'):
                    address_parts.append(address_data['address1'])
                if address_data.get('city'):
                    address_parts.append(address_data['city'])
                if address_data.get('state'):
                    address_parts.append(address_data['state'])
                if address_data.get('zip'):
                    address_parts.append(address_data['zip'])
                address = ", ".join(address_parts)
            
            # Determine if this is a "now" or "plan" item
            item_type = "now" if address else "plan"
            
            # Extract other fields
            price = self.parse_price(hit.get('price'))
            sqft = self.parse_sqft(hit.get('sqFt'))
            stories = self.parse_stories(hit.get('stories'))
            beds = str(hit.get('bedrooms', '')) if hit.get('bedrooms') else ""
            baths = str(hit.get('baths', '')) if hit.get('baths') else ""
            design_number = hit.get('designNumber', '')
            
            # Calculate price per sqft
            price_per_sqft = None
            if price and sqft and sqft > 0:
                price_per_sqft = round(price / sqft, 2)
            
            # Create plan name - use design number if available, otherwise use address
            plan_name = design_number if design_number else address
            
            plan_data = {
                "price": price,
                "sqft": sqft,
                "stories": stories,
                "price_per_sqft": price_per_sqft,
                "plan_name": plan_name,
                "company": "PerryHomes",
                "community": "Edgewater",
                "type": item_type,
                "beds": beds,
                "baths": baths,
                "address": address if address else "",
                "design_number": design_number
            }
            
            return plan_data
            
        except Exception as e:
            print(f"[PerryHomesEdgewaterNowScraper] Error processing hit: {e}")
            return None

    def fetch_plans(self) -> List[Dict]:
        """Fetch plans from both Algolia endpoints and combine results."""
        try:
            print("[PerryHomesEdgewaterNowScraper] Starting to fetch PerryHomes data for Edgewater")
            
            all_listings = []
            
            # Fetch data from both sections
            sections = ["Avondale 40'", "Avondale 45'"]
            
            for section in sections:
                print(f"[PerryHomesEdgewaterNowScraper] Fetching data for section: {section}")
                
                response_data = self.make_algolia_request(section)
                
                if not response_data or 'results' not in response_data:
                    print(f"[PerryHomesEdgewaterNowScraper] No results found for section {section}")
                    continue
                
                results = response_data['results']
                if not results or len(results) == 0:
                    print(f"[PerryHomesEdgewaterNowScraper] No results array found for section {section}")
                    continue
                
                first_result = results[0]
                hits = first_result.get('hits', [])
                
                print(f"[PerryHomesEdgewaterNowScraper] Found {len(hits)} hits for section {section}")
                
                for idx, hit in enumerate(hits):
                    try:
                        plan_data = self.process_hit(hit, section)
                        if plan_data:
                            print(f"[PerryHomesEdgewaterNowScraper] Processed {plan_data['type']} item {idx+1}: {plan_data['plan_name']}")
                            all_listings.append(plan_data)
                    except Exception as e:
                        print(f"[PerryHomesEdgewaterNowScraper] Error processing hit {idx+1} in section {section}: {e}")
                        continue
            
            print(f"[PerryHomesEdgewaterNowScraper] Successfully processed {len(all_listings)} total items")
            return all_listings
            
        except Exception as e:
            print(f"[PerryHomesEdgewaterNowScraper] Error: {e}")
            return []
