PLATFORM_FEES = {
    "generic": {"percent": 0.0, "fixed": 0.0},
    "etsy": {"percent": 0.095, "fixed": 0.25},
    "shopify": {"percent": 0.029, "fixed": 0.30},
    "amazon": {"percent": 0.15, "fixed": 0.0},
    "tiktok": {"percent": 0.06, "fixed": 0.0},
}


def calculate_platform_fee(selling_price, platform="generic"):
    fee = PLATFORM_FEES.get(platform or "generic", PLATFORM_FEES["generic"])
    return round(selling_price * fee["percent"] + fee["fixed"], 2)


def calculate_margin(selling_price, base_cost, shipping_fee=0.0, platform="generic", tax_fee=0.0):
    selling_price = float(selling_price)
    base_cost = float(base_cost or 0)
    shipping_fee = float(shipping_fee or 0)
    tax_fee = float(tax_fee or 0)
    platform_fee = calculate_platform_fee(selling_price, platform)
    total_cost = round(base_cost + shipping_fee + tax_fee + platform_fee, 2)
    profit = round(selling_price - total_cost, 2)
    margin_percent = round((profit / selling_price) * 100, 2) if selling_price else 0.0
    return {
        "selling_price": selling_price,
        "base_cost": base_cost,
        "shipping_fee": shipping_fee,
        "tax_fee": tax_fee,
        "platform": platform or "generic",
        "platform_fee": platform_fee,
        "total_cost": total_cost,
        "landed_cost": total_cost,
        "profit": profit,
        "margin_percent": margin_percent,
    }
