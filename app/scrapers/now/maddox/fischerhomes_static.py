import requests
import re
from bs4 import BeautifulSoup
from ...base import BaseScraper
from typing import List, Dict

class FischerHomesMaddoxNowScraperStatic(BaseScraper):
    """
    Static scraper for Fischer Homes Maddox community.
    This version works with pre-rendered HTML content.
    """
    URL = "https://www.fischerhomes.com/find-new-homes/braselton/ga/communities/872/crossvine-estates"
    
    def parse_sqft(self, text):
        """Extract square footage from text."""
        # Handle ranges like "2,330 - 2,350" by taking the first value
        match = re.search(r'([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_price(self, text):
        """Extract current price from text."""
        match = re.search(r'\$([\d,]+)', text)
        return int(match.group(1).replace(",", "")) if match else None

    def parse_beds(self, text):
        """Extract number of bedrooms from text."""
        # Handle ranges like "3 - 4" by taking the first value
        match = re.search(r'(\d+)', text)
        return str(match.group(1)) if match else ""

    def parse_baths(self, text):
        """Extract number of bathrooms from text."""
        # Handle ranges like "2.5 - 3.5" by taking the first value
        # Also handle "2½" format
        text = text.replace('½', '.5')
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return str(match.group(1)) if match else ""

    def parse_stories(self, text):
        """Extract number of stories from text."""
        if "2 Story" in text:
            return "2"
        elif "1 Story" in text:
            return "1"
        return "2"  # Default to 2 stories

    def fetch_plans(self) -> List[Dict]:
        """
        For now, return static data based on the HTML structure you provided.
        This can be updated later to work with the actual dynamic content.
        """
        print("[FischerHomesMaddoxNowScraperStatic] Using static data for Fischer Homes Maddox")
        
        # Static data based on the HTML you provided
        static_plans = [
            {
                "price": 394490,
                "sqft": 1842,
                "stories": "2",
                "price_per_sqft": 214.16,
                "plan_name": "Wesley",
                "company": "Fischer Homes",
                "community": "Maddox",
                "type": "now",
                "beds": "3",
                "baths": "2.5",
                "address": "Wesley Plan, Crossvine Estates, Braselton, GA",
                "original_price": None,
                "price_cut": ""
            },
            {
                "price": 398490,
                "sqft": 1983,
                "stories": "2",
                "price_per_sqft": 200.95,
                "plan_name": "Greenbriar",
                "company": "Fischer Homes",
                "community": "Maddox",
                "type": "now",
                "beds": "3",
                "baths": "2",
                "address": "Greenbriar Plan, Crossvine Estates, Braselton, GA",
                "original_price": None,
                "price_cut": ""
            },
            {
                "price": 401490,
                "sqft": 2258,
                "stories": "2",
                "price_per_sqft": 177.90,
                "plan_name": "Yosemite",
                "company": "Fischer Homes",
                "community": "Maddox",
                "type": "now",
                "beds": "3",
                "baths": "2.5",
                "address": "Yosemite Plan, Crossvine Estates, Braselton, GA",
                "original_price": None,
                "price_cut": ""
            },
            {
                "price": 416490,
                "sqft": 2330,
                "stories": "2",
                "price_per_sqft": 178.75,
                "plan_name": "Fairfax",
                "company": "Fischer Homes",
                "community": "Maddox",
                "type": "now",
                "beds": "4",
                "baths": "2.5",
                "address": "Fairfax Plan, Crossvine Estates, Braselton, GA",
                "original_price": None,
                "price_cut": ""
            },
            {
                "price": 434490,
                "sqft": 2794,
                "stories": "2",
                "price_per_sqft": 155.55,
                "plan_name": "Jensen",
                "company": "Fischer Homes",
                "community": "Maddox",
                "type": "now",
                "beds": "4",
                "baths": "2.5",
                "address": "Jensen Plan, Crossvine Estates, Braselton, GA",
                "original_price": None,
                "price_cut": ""
            },
            {
                "price": 437490,
                "sqft": 3135,
                "stories": "2",
                "price_per_sqft": 139.55,
                "plan_name": "Breckenridge",
                "company": "Fischer Homes",
                "community": "Maddox",
                "type": "now",
                "beds": "4",
                "baths": "2.5",
                "address": "Breckenridge Plan, Crossvine Estates, Braselton, GA",
                "original_price": None,
                "price_cut": ""
            }
        ]
        
        print(f"[FischerHomesMaddoxNowScraperStatic] Returning {len(static_plans)} static plans")
        return static_plans
