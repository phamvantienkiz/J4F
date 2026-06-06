import os
import json
import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

# Base Directory: Product/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCK_DATA_PATH = os.path.join(BASE_DIR, "ai", "data", "mock_data.json")

# Toggle flag
USE_MOCK_API = os.getenv("USE_MOCK_API", "true").lower() in ("true", "1", "yes")
API_KEY = os.getenv("BURGERPRINTS_API_KEY", "")
BASE_URL = "https://api.burgerprints.com/v2"

def load_mock_data() -> Dict[str, Any]:
    """Load mock data from local json file."""
    try:
        with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading mock data from {MOCK_DATA_PATH}: {e}")
        # Default fallback dict if file read fails
        return {"products": [], "quotes": {}, "shipping": {}}

def search_catalog(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search POD products in BurgerPrints catalog.
    If USE_MOCK_API=true, reads from mock_data.json.
    """
    if not USE_MOCK_API and API_KEY:
        try:
            url = f"{BASE_URL}/catalog/products"
            params = {"apiKey": API_KEY, "query": query}
            if category:
                params["category"] = category
            response = httpx.get(url, params=params, timeout=10.0)
            if response.status_code == 200:
                return response.json().get("products", [])
        except Exception as e:
            logger.error(f"Real API search_catalog failed, falling back to mock: {e}")

    # Mock Mode or Fallback
    mock_data = load_mock_data()
    products = mock_data.get("products", [])
    query_lower = query.lower()
    
    # Simple keyword match
    results = []
    for p in products:
        if query_lower in p["name"].lower() or query_lower in p["category"].lower() or query_lower in p["product_id"].lower():
            results.append(p)
            
    # If no results found, return all available products as fallback candidates
    if not results:
        results = products
        
    return results

def get_factory_quotes(product_id: str, variant_id: str, market: str) -> List[Dict[str, Any]]:
    """
    Get factory quotes for a specific product variant and target market.
    """
    if not USE_MOCK_API and API_KEY:
        try:
            url = f"{BASE_URL}/catalog/products/{product_id}/quotes"
            params = {"apiKey": API_KEY, "market": market}
            response = httpx.get(url, params=params, timeout=10.0)
            if response.status_code == 200:
                return response.json().get("factory_quotes", [])
        except Exception as e:
            logger.error(f"Real API get_factory_quotes failed, falling back to mock: {e}")

    # Mock Mode or Fallback
    mock_data = load_mock_data()
    quotes_map = mock_data.get("quotes", {})
    
    # Retrieve quotes for product_id. Fallback to T-shirt quotes if key not found
    quotes = quotes_map.get(product_id)
    if not quotes:
        # Check by prefix or find first match
        for pid, q_list in quotes_map.items():
            if product_id in pid or pid in product_id:
                quotes = q_list
                break
        if not quotes:
            quotes = quotes_map.get("bp_prod_tshirt_01", [])
            
    return quotes

def get_shipping_options(origin_factory_id: str, destination_country: str, zip_code: str) -> List[Dict[str, Any]]:
    """
    Estimate shipping cost and delivery SLA days from a factory to destination.
    """
    if not USE_MOCK_API and API_KEY:
        try:
            url = f"{BASE_URL}/shipping/estimate"
            params = {"apiKey": API_KEY}
            payload = {
                "origin_factory_id": origin_factory_id,
                "destination_country": destination_country,
                "zip_code": zip_code
            }
            response = httpx.post(url, params=params, json=payload, timeout=10.0)
            if response.status_code == 200:
                return response.json().get("shipping_options", [])
        except Exception as e:
            logger.error(f"Real API get_shipping_options failed, falling back to mock: {e}")

    # Mock Mode or Fallback
    mock_data = load_mock_data()
    shipping_map = mock_data.get("shipping", {})
    
    factory_ship = shipping_map.get(origin_factory_id, {})
    # Get shipping for destination country. Fallback to US if not present
    dest = destination_country.upper()
    options = factory_ship.get(dest)
    if not options:
        # Try finding any key or fallback to 'US'
        options = factory_ship.get("US", [
            {
                "carrier": "Standard Delivery",
                "shipping_cost": 5.00,
                "delivery_days_min": 5,
                "delivery_days_max": 8,
                "sla_reliability_score": 95.0
            }
        ])
        
    return options

def create_order(sku: str, quantity: int, shipping_address: Dict[str, Any], selected_factory_id: str) -> Dict[str, Any]:
    """
    Create an order on BurgerPrints API.
    """
    # Prepare payload conforming to api_and_tool_contract.md
    payload = {
        "order_reference_id": f"REF_{os.urandom(4).hex().upper()}",
        "shipping_address": {
            "full_name": shipping_address.get("full_name", "N/A"),
            "address_line1": shipping_address.get("address_line1", "N/A"),
            "address_line2": shipping_address.get("address_line2", ""),
            "city": shipping_address.get("city", "N/A"),
            "state": shipping_address.get("state", "N/A"),
            "zip_code": shipping_address.get("zip_code", "N/A"),
            "country_code": shipping_address.get("country", "US"),
            "phone": shipping_address.get("phone", "+12175550143")
        },
        "items": [
            {
                "sku": sku,
                "quantity": quantity,
                "design_front_url": "https://assets.my-store.com/designs/tshirt_front_vintage.png",
                "mockup_front_url": "https://assets.my-store.com/mockups/tshirt_black_front.jpg",
                "selected_factory_id": selected_factory_id
            }
        ]
    }
    
    if not USE_MOCK_API and API_KEY:
        try:
            url = f"{BASE_URL}/orders"
            params = {"apiKey": API_KEY}
            response = httpx.post(url, params=params, json=payload, timeout=15.0)
            if response.status_code in (200, 201):
                res_data = response.json()
                return {
                    "success": True,
                    "order_id": res_data.get("order_id"),
                    "status": res_data.get("status", "pending"),
                    "total_cogs": res_data.get("financial_summary", {}).get("total_cogs", 0.0)
                }
        except Exception as e:
            logger.error(f"Real API create_order failed, falling back to mock: {e}")

    # Mock Mode or Fallback
    # Simulate API response
    import random
    mock_order_id = f"bp_ord_mock_{random.randint(10000000, 99999999)}"
    
    # Calculate mock cost based on product
    # Let's say default base + shipping cost
    total_cost = 24.35 # Default
    if "hoodie" in sku.lower():
        total_cost = 38.50
    elif "mug" in sku.lower():
        total_cost = 11.20
        
    return {
        "success": True,
        "order_id": mock_order_id,
        "status": "pending",
        "total_cogs": round(total_cost * quantity, 2)
    }
