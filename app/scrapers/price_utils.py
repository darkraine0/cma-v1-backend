"""
Utility functions for price parsing across all scrapers.
Handles common price formatting issues like thousands notation.
"""

import re
from typing import Optional

def parse_price_with_thousands(text: str) -> Optional[int]:
    """
    Parse price from text, handling thousands notation.
    
    Examples:
    - "$363s" -> 363000
    - "$363" -> 363000 (if < 1000)
    - "$363,000" -> 363000
    - "$1,500" -> 1500 (if >= 1000, treat as actual price)
    
    Args:
        text: The text containing the price
        
    Returns:
        The parsed price as an integer, or None if no price found
    """
    if not text:
        return None
    
    # Look for price patterns with optional 's' suffix
    match = re.search(r'\$([\d,]+)s?', text)
    if not match:
        return None
    
    price_str = match.group(1).replace(",", "")
    try:
        price = int(price_str)
        
        # If price is less than 1000, it's likely in thousands notation
        # This handles cases like "363" meaning "$363,000"
        if price < 1000:
            price = price * 1000
            
        return price
    except ValueError:
        return None

def parse_price_standard(text: str) -> Optional[int]:
    """
    Parse price from text using standard format (no thousands assumption).
    
    Examples:
    - "$363,000" -> 363000
    - "$1,500" -> 1500
    
    Args:
        text: The text containing the price
        
    Returns:
        The parsed price as an integer, or None if no price found
    """
    if not text:
        return None
    
    match = re.search(r'\$([\d,]+)', text)
    if not match:
        return None
    
    price_str = match.group(1).replace(",", "")
    try:
        return int(price_str)
    except ValueError:
        return None
