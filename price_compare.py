import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import aiohttp

logger = logging.getLogger(__name__)

COMPETITORS = {
    "amazon": "https://www.amazon.com",
    "ebay": "https://www.ebay.com",
    "yourbooksky": "https://www.yourbooksky.com",
    "yourbookstop": "https://www.yourbookstop.com",
    "fairbookdeals": "https://www.fairbookdeals.com"
}

LOCATION_CURRENCY = {
    "US": "USD",
    "UK": "GBP",
    "CA": "CAD",
    "AU": "AUD",
    "IN": "INR",
    "EU": "EUR",
    "JP": "JPY",
    "BR": "BRL"
}

class PriceComparator:
    """Compare product prices across multiple competitors."""
    
    def __init__(self):
        self.competitors = COMPETITORS
        self.location_currency = LOCATION_CURRENCY
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    def get_competitors(self) -> List[Dict[str, str]]:
        """Get list of available competitors."""
        return [
            {"name": name, "url": url}
            for name, url in self.competitors.items()
        ]
    
    async def compare_prices(
        self, 
        product_name: str, 
        location: str = "US"
    ) -> Dict:
        """Compare product prices across competitors."""
        try:
            currency = self.location_currency.get(location.upper(), "USD")
            prices = await self._fetch_all_prices(product_name, location)
            comparison = self._analyze_prices(prices, product_name, currency)
            return comparison
        
        except Exception as e:
            logger.error(f"Error comparing prices: {e}")
            return {
                "error": str(e),
                "product": product_name,
                "location": location
            }
    
    async def _fetch_all_prices(
        self, 
        product_name: str, 
        location: str
    ) -> Dict[str, Optional[Dict]]:
        """Fetch prices from all competitors concurrently."""
        tasks = {
            name: self._fetch_competitor_price(name, product_name, location)
            for name in self.competitors.keys()
        }
        
        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                logger.warning(f"Failed to fetch from {name}: {e}")
                results[name] = None
        
        return results
    
    async def _fetch_competitor_price(
        self, 
        competitor_name: str, 
        product_name: str, 
        location: str
    ) -> Optional[Dict]:
        """Fetch price from a specific competitor."""
        try:
            await asyncio.sleep(0.5)
            return await self._get_mock_price(competitor_name, product_name, location)
        except Exception as e:
            logger.error(f"Error fetching from {competitor_name}: {e}")
            return None
    
    async def _get_mock_price(
        self, 
        competitor_name: str, 
        product_name: str,
        location: str
    ) -> Dict:
        """Get mock price data for demonstration."""
        base_prices = {
            "amazon": 14.99,
            "ebay": 15.99,
            "yourbooksky": 13.99,
            "yourbookstop": 12.99,
            "fairbookdeals": 11.99
        }
        
        location_multiplier = {
            "US": 1.0, "UK": 0.73, "CA": 1.35, "AU": 1.53,
            "IN": 82.5, "EU": 0.92, "JP": 149.5, "BR": 5.1
        }
        
        multiplier = location_multiplier.get(location.upper(), 1.0)
        base_price = base_prices.get(competitor_name, 15.99)
        
        return {
            "competitor": competitor_name,
            "product": product_name,
            "price": round(base_price * multiplier, 2),
            "currency": self.location_currency.get(location.upper(), "USD"),
            "availability": "In Stock",
            "url": f"{self.competitors[competitor_name]}/search?q={product_name}",
            "last_updated": datetime.now().isoformat(),
            "shipping": "Free" if base_price > 10 else "Paid"
        }
    
    def _analyze_prices(
        self, 
        prices: Dict[str, Optional[Dict]], 
        product_name: str,
        currency: str
    ) -> Dict:
        """Analyze and compare prices across competitors."""
        
        valid_prices = {
            name: data for name, data in prices.items() 
            if data is not None
        }
        
        if not valid_prices:
            return {
                "error": "No prices found",
                "product": product_name,
                "competitors_checked": len(prices)
            }
        
        price_list = [data["price"] for data in valid_prices.values()]
        min_price = min(price_list)
        max_price = max(price_list)
        avg_price = sum(price_list) / len(price_list)
        
        cheapest = min(valid_prices.items(), key=lambda x: x[1]["price"])
        most_expensive = max(valid_prices.items(), key=lambda x: x[1]["price"])
        
        max_savings = max_price - min_price
        savings_percentage = (max_savings / max_price) * 100 if max_price > 0 else 0
        
        return {
            "product": product_name,
            "currency": currency,
            "summary": {
                "cheapest": {
                    "competitor": cheapest[0],
                    "price": cheapest[1]["price"],
                    "availability": cheapest[1].get("availability"),
                    "shipping": cheapest[1].get("shipping"),
                    "url": cheapest[1].get("url")
                },
                "most_expensive": {
                    "competitor": most_expensive[0],
                    "price": most_expensive[1]["price"],
                    "availability": most_expensive[1].get("availability"),
                    "shipping": most_expensive[1].get("shipping"),
                    "url": most_expensive[1].get("url")
                },
                "average_price": round(avg_price, 2),
                "price_range": {
                    "min": min_price,
                    "max": max_price
                },
                "potential_savings": {
                    "amount": round(max_savings, 2),
                    "percentage": round(savings_percentage, 2)
                }
            },
            "detailed_prices": [
                {
                    "rank": i + 1,
                    "competitor": name,
                    "price": data["price"],
                    "availability": data.get("availability"),
                    "shipping": data.get("shipping"),
                    "url": data.get("url"),
                    "last_updated": data.get("last_updated")
                }
                for i, (name, data) in enumerate(
                    sorted(valid_prices.items(), key=lambda x: x[1]["price"])
                )
            ],
            "competitors_checked": len(valid_prices),
            "timestamp": datetime.now().isoformat()
        }
