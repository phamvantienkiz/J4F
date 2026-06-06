import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def calculate_landed_cost(
    base_cost: float,
    printing_cost: float,
    shipping_cost: float,
    market: str
) -> Dict[str, float]:
    """
    Calculate the landed cost and tax details based on market destination.
    Landed Cost = Base Cost + Printing Cost + Shipping Cost + Tax
    """
    # Simple tax rules based on destination market
    market_upper = market.upper()
    if market_upper == "US":
        tax_rate = 0.08  # 8% sales tax
    elif market_upper == "EU":
        tax_rate = 0.19  # 19% VAT
    elif market_upper == "VN":
        tax_rate = 0.10  # 10% VAT
    else:
        tax_rate = 0.05  # 5% default

    subtotal = base_cost + printing_cost
    tax = round(subtotal * tax_rate, 2)
    landed_cost = round(subtotal + shipping_cost + tax, 2)
    
    return {
        "subtotal": round(subtotal, 2),
        "tax": tax,
        "landed_cost": landed_cost
    }

def calculate_margin(landed_cost: float, selling_price: float) -> float:
    """
    Calculate margin percentage based on selling price and landed cost.
    """
    if selling_price <= 0:
        return 0.0
    margin = ((selling_price - landed_cost) / selling_price) * 100
    return round(margin, 2)

def suggest_retail_price(landed_cost: float, target_margin: float) -> float:
    """
    Suggest a selling price to achieve the target margin.
    """
    if target_margin >= 100.0 or target_margin < 0.0:
        # Fallback to double landed cost if target margin is invalid
        return round(landed_cost * 2.0, 2)
    
    suggested_price = landed_cost / (1.0 - (target_margin / 100.0))
    return round(suggested_price, 2)

def calculate_sla_risk(
    factory_reliability: float,
    origin_location: str,
    destination_market: str,
    delivery_days_max: int
) -> float:
    """
    Calculate SLA risk score (0 to 100, lower is better).
    """
    # Base risk is 100 - reliability
    base_risk = 100.0 - factory_reliability
    
    # Cross border penalty
    origin_country = origin_location.split(",")[-1].strip().upper()
    dest = destination_market.upper()
    
    penalty = 0.0
    if origin_country != dest:
        # Cross border shipping adds risk
        penalty += 15.0
        
    # Long delivery penalty
    if delivery_days_max > 10:
        penalty += 10.0
    elif delivery_days_max > 7:
        penalty += 5.0
        
    risk_score = min(base_risk + penalty, 100.0)
    return round(risk_score, 2)
