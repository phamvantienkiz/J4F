from src.services.margin import calculate_margin


class MarginAgent:
    def calculate(self, selling_price, base_cost, shipping_fee=0.0, platform="generic"):
        return calculate_margin(selling_price, base_cost, shipping_fee, platform)
