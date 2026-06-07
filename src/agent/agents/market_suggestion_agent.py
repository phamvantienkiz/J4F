from datetime import date


SEASON_BY_MONTH_NORTH = {
    12: "winter",
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "fall",
    10: "fall",
    11: "fall",
}

SEASON_BY_MONTH_SOUTH = {
    12: "summer",
    1: "summer",
    2: "summer",
    3: "fall",
    4: "fall",
    5: "fall",
    6: "winter",
    7: "winter",
    8: "winter",
    9: "spring",
    10: "spring",
    11: "spring",
}

PRODUCT_TYPES_BY_SEASON = {
    "spring": ["T-shirt", "Sweatshirt", "Mug"],
    "summer": ["T-shirt", "Tank top", "Lightweight apparel"],
    "fall": ["Sweatshirt", "Hoodie", "Long sleeve"],
    "winter": ["Hoodie", "Sweatshirt", "Mug"],
    "hot/rainy": ["T-shirt", "Tank top", "Mug"],
}

WEATHER_BY_SEASON = {
    "spring": "mild weather and spring refresh themes",
    "summer": "hot weather, outdoor activities, and vacation themes",
    "fall": "cooler weather, layered apparel, and cozy themes",
    "winter": "cold weather, gifting, and warm apparel themes",
    "hot/rainy": "hot/rainy weather, lightweight apparel, and daily-use gift themes",
}

US_EVENTS_BY_MONTH = {
    1: ["New Year", "winter themes"],
    2: ["Valentine's Day"],
    3: ["St. Patrick's Day", "spring themes"],
    4: ["Easter", "Earth Day"],
    5: ["Mother's Day", "Memorial Day"],
    6: ["Father's Day", "summer", "July 4 prep"],
    7: ["Independence Day", "summer vacation"],
    8: ["Back to school prep"],
    9: ["Labor Day", "fall prep"],
    10: ["Halloween"],
    11: ["Thanksgiving", "Black Friday", "Christmas prep"],
    12: ["Christmas", "New Year"],
}

GENERIC_EVENTS_BY_MONTH = {
    1: ["New Year"],
    2: ["Valentine's Day"],
    3: ["spring refresh"],
    4: ["Easter", "Earth Day"],
    5: ["Mother's Day"],
    6: ["Father's Day", "summer themes"],
    7: ["summer vacation"],
    8: ["back to school prep"],
    9: ["fall prep"],
    10: ["Halloween"],
    11: ["Black Friday", "holiday prep"],
    12: ["Christmas", "New Year"],
}


class MarketSuggestionAgent:
    def run(self, country: str, month: int | None = None) -> dict:
        normalized_country = (country or "US").upper()
        resolved_month = month or date.today().month
        season = self._season(normalized_country, resolved_month)
        events = self._events(normalized_country, resolved_month)
        product_types = PRODUCT_TYPES_BY_SEASON[season]
        weather_context = WEATHER_BY_SEASON[season]
        return {
            "country": normalized_country,
            "month": resolved_month,
            "season": season,
            "weather_context": weather_context,
            "events": events,
            "product_types": product_types,
            "suggestions": self._suggestions(normalized_country, season, events, product_types),
        }

    def _season(self, country: str, month: int) -> str:
        if country == "VN":
            return "hot/rainy"
        if country == "AU":
            return SEASON_BY_MONTH_SOUTH[month]
        return SEASON_BY_MONTH_NORTH[month]

    def _events(self, country: str, month: int) -> list[str]:
        if country == "US":
            return US_EVENTS_BY_MONTH[month]
        return GENERIC_EVENTS_BY_MONTH[month]

    def _suggestions(self, country: str, season: str, events: list[str], product_types: list[str]) -> list[str]:
        primary_product = product_types[0]
        primary_event = events[0]
        return [
            f"Mùa {season} ở {country} nên bán sản phẩm POD nào?",
            f"Gợi ý niche {primary_product} cho {country} tháng này",
            f"Sắp tới ở {country} có event nào nên làm design?",
            f"Gợi ý design cho {primary_event} ở {country}",
            f"Tìm SKU {primary_product} phù hợp bán ở {country} mùa {season}",
        ]
