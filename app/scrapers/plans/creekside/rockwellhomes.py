#!/usr/bin/env python3
"""
Rockwell Homes Creekside Floor Plans Scraper
"""

import requests
from bs4 import BeautifulSoup
import re
from app.scrapers.base import BaseScraper

class RockwellHomesCreeksidePlanScraper(BaseScraper):
    URL = "https://www.rockwell-homes.com/new-homes/tx/royse-city/creekside/14633/"
    
    def parse_price(self, text):
        """Parse price from text like 'From $376,900'"""
        if not text:
            return None
        
        # Remove any non-numeric characters except commas and dots
        price_text = re.sub(r'[^\d,.]', '', text)
        
        try:
            # Remove commas and convert to integer
            price = int(price_text.replace(',', ''))
            return price
        except (ValueError, AttributeError):
            return None
    
    def parse_sqft(self, text):
        """Parse square footage from text like '2,781 - 2,837' or '1,658'"""
        if not text:
            return None
        
        # Remove any non-numeric characters except commas, dots, and hyphens
        sqft_text = re.sub(r'[^\d,.\-]', '', text)
        
        try:
            # Handle ranges like "2,781 - 2,837"
            if '-' in sqft_text:
                parts = sqft_text.split('-')
                # Take the first number as the base square footage
                base_sqft = parts[0].strip().replace(',', '')
                return int(base_sqft)
            else:
                # Single number
                sqft = int(sqft_text.replace(',', ''))
                return sqft
        except (ValueError, AttributeError):
            return None
    
    def parse_beds_baths_garages(self, text):
        """Parse beds, baths, or garages from text like '5' or '2.5 - 4'"""
        if not text:
            return None
        
        # Extract the first number from the text
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        if match:
            try:
                value = float(match.group(1))
                return int(value) if value.is_integer() else value
            except (ValueError, AttributeError):
                return None
        return None
    
    def extract_plan_data(self, plan_card):
        """Extract data from a floor plan card"""
        try:
            # Plan name - look for the card-small-title class
            plan_name_elem = plan_card.find('div', class_='card-small-title')
            if not plan_name_elem:
                return None
            
            plan_name = plan_name_elem.get_text(strip=True)
            
            if not plan_name:
                return None
            
            # Square footage - look for the sqft-stat class
            sqft_elem = plan_card.find('span', class_='sqft-stat')
            sqft = None
            if sqft_elem:
                sqft_text = sqft_elem.get_text(strip=True)
                # Extract just the square footage part (remove "SQ" prefix)
                sqft_text = re.sub(r'^SQ\s*', '', sqft_text)
                sqft = self.parse_sqft(sqft_text)
            
            # Bedrooms - look for the bed-stat class
            beds_elem = plan_card.find('span', class_='bed-stat')
            beds = None
            if beds_elem:
                beds_text = beds_elem.get_text(strip=True)
                # Extract just the number part (remove "BD" prefix)
                beds_text = re.sub(r'^BD\s*', '', beds_text)
                beds = self.parse_beds_baths_garages(beds_text)
            
            # Bathrooms - look for the bath-stat class
            baths_elem = plan_card.find('span', class_='bath-stat')
            baths = None
            if baths_elem:
                baths_text = baths_elem.get_text(strip=True)
                # Extract just the number part (remove "BA" prefix)
                baths_text = re.sub(r'^BA\s*', '', baths_text)
                baths = self.parse_beds_baths_garages(baths_text)
            
            # Garages - look for the garage-stat class
            garages_elem = plan_card.find('span', class_='garage-stat')
            garages = None
            if garages_elem:
                garages_text = garages_elem.get_text(strip=True)
                # Extract just the number part (remove "GA" prefix)
                garages_text = re.sub(r'^GA\s*', '', garages_text)
                garages = self.parse_beds_baths_garages(garages_text)
            
            # Price - look for the card-price class
            price_elem = plan_card.find('div', class_='card-price')
            price = None
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self.parse_price(price_text)
            
            # Elevation count - look for the elevation-count class
            elevation_elem = plan_card.find('div', class_='elevation-count')
            elevation_count = None
            if elevation_elem:
                elevation_text = elevation_elem.get_text(strip=True)
                # Extract the number from "8 Elevations"
                match = re.search(r'(\d+)', elevation_text)
                if match:
                    elevation_count = int(match.group(1))
            
            # Image URL - look for the img tag
            image_url = None
            img_elem = plan_card.find('img')
            if img_elem and img_elem.get('src'):
                image_url = img_elem.get('src')
            
            # Plan URL - look for the first link in the card
            plan_url = None
            link_elem = plan_card.find('a')
            if link_elem and link_elem.get('href'):
                plan_url = link_elem.get('href')
                # Make sure it's a full URL
                if plan_url.startswith('/'):
                    plan_url = f"https://www.rockwell-homes.com{plan_url}"
            
            # Check if it's a model home
            is_model_home = False
            model_elem = plan_card.find('div', class_='spec-status')
            if model_elem:
                model_text = model_elem.get_text(strip=True)
                if 'model' in model_text.lower():
                    is_model_home = True
            
            # Calculate price per square foot
            price_per_sqft = None
            if price and sqft:
                price_per_sqft = price / sqft
            
            return {
                'plan_name': plan_name,
                'square_feet': sqft,
                'sqft': sqft,  # Add both for compatibility
                'bedrooms': beds,
                'bathrooms': baths,
                'garages': garages,
                'price': price,
                'stories': '1',  # Default to 1 story for single-family homes
                'price_per_sqft': price_per_sqft,
                'elevation_count': elevation_count,
                'image_url': image_url,
                'plan_url': plan_url,
                'is_model_home': is_model_home,
                'company': 'Rockwell Homes',
                'community': 'Creekside',
                'type': 'plan'
            }
            
        except Exception as e:
            print(f"Error extracting plan data: {e}")
            return None
    
    def fetch_plans(self):
        """Fetch all floor plans from the Rockwell Homes Creekside page"""
        try:
            print(f"Fetching plans from: {self.URL}")
            
            # Send GET request to the page
            response = requests.get(self.URL, timeout=30)
            response.raise_for_status()
            
            # Parse the HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all plan cards
            plan_cards = soup.find_all('div', class_='plan-card')
            
            if not plan_cards:
                print("No plan cards found on the page")
                return []
            
            print(f"Found {len(plan_cards)} plan cards")
            
            # Extract data from each plan card
            plans = []
            for card in plan_cards:
                plan_data = self.extract_plan_data(card)
                if plan_data:
                    plans.append(plan_data)
                    print(f"Extracted plan: {plan_data['plan_name']}")
            
            print(f"Successfully extracted {len(plans)} plans")
            return plans
            
        except requests.RequestException as e:
            print(f"Request error: {e}")
            return []
        except Exception as e:
            print(f"Error fetching plans: {e}")
            return []
