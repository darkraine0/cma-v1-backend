from abc import ABC, abstractmethod
from typing import List, Dict

class BaseScraper(ABC):
    @abstractmethod
    def fetch_plans(self) -> List[Dict]:
        """Scrape and return a list of plan dicts."""
        pass 