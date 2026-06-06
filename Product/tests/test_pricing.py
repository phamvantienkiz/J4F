from ai.pricing_engine import calculate_landed_cost, calculate_margin, suggest_retail_price, calculate_sla_risk

def test_calculate_landed_cost_us():
    # US tax = 8%
    # subtotal = 5.50 + 2.00 = 7.50
    # tax = 7.50 * 0.08 = 0.60
    # shipping = 4.00
    # landed = 7.50 + 4.00 + 0.60 = 12.10
    result = calculate_landed_cost(5.50, 2.00, 4.00, "US")
    assert result["subtotal"] == 7.50
    assert result["tax"] == 0.60
    assert result["landed_cost"] == 12.10

def test_calculate_landed_cost_eu():
    # EU tax = 19%
    # subtotal = 6.00 + 2.50 = 8.50
    # tax = 8.50 * 0.19 = 1.62
    # shipping = 4.50
    # landed = 8.50 + 4.50 + 1.62 = 14.62
    result = calculate_landed_cost(6.00, 2.50, 4.50, "EU")
    assert result["subtotal"] == 8.50
    assert result["tax"] == 1.61
    assert result["landed_cost"] == 14.61

def test_calculate_margin():
    assert calculate_margin(12.10, 20.00) == 39.5  # ((20 - 12.1) / 20) * 100 = 39.5%
    assert calculate_margin(10.00, 10.00) == 0.0

def test_suggest_retail_price():
    # landed = 12.00, target margin = 40% -> suggested = 12.00 / 0.60 = 20.00
    assert suggest_retail_price(12.00, 40.0) == 20.00
    # target margin = 50% -> suggested = 12.00 / 0.50 = 24.00
    assert suggest_retail_price(12.00, 50.0) == 24.00

def test_calculate_sla_risk():
    # Same country: Chicago (US) to US, reliability = 98.0%, max delivery = 5 days -> no penalties
    # risk = 100 - 98 = 2.0
    risk = calculate_sla_risk(98.0, "IL, US", "US", 5)
    assert risk == 2.0
    
    # Cross border: Hanoi (VN) to US, reliability = 93.0%, max delivery = 9 days -> +15 penalty (cross border), +5 penalty (delivery > 7)
    # risk = (100 - 93) + 15 + 5 = 27.0
    risk = calculate_sla_risk(93.0, "Hanoi, VN", "US", 9)
    assert risk == 27.0
