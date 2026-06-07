from datetime import date

from src.agent.agents.market_suggestion_agent import MarketSuggestionAgent
from src.core.text_parser import parse_country


EVENT_DESCRIPTIONS = {
    "july 4 prep": "July 4 prep là giai đoạn chuẩn bị design trước Independence Day 4/7 ở US. Seller thường làm chủ đề cờ Mỹ, fireworks, BBQ, family gathering, patriotic quote và nên chuẩn bị listing trước event vài tuần.",
    "independence day": "Independence Day là ngày Quốc khánh Mỹ 4/7. Với POD, event này hợp với design patriotic, fireworks, BBQ, family, veteran/USA pride và apparel mùa hè.",
    "father's day": "Father's Day là Ngày của Cha. Với POD, event này hợp với áo/cốc quà tặng cho dad, grandpa, husband, funny dad quote và family matching.",
    "mother's day": "Mother's Day là Ngày của Mẹ. Với POD, event này hợp với gift design cho mom, grandma, wife, floral typography và family quote.",
    "black friday": "Black Friday là mùa sale lớn cuối tháng 11. Với POD, nên chuẩn bị deal design, giftable products, holiday prep và campaign giảm giá rõ ràng.",
    "thanksgiving": "Thanksgiving là lễ Tạ ơn ở US vào tháng 11. Design thường xoay quanh family gathering, gratitude, turkey, fall colors và cozy apparel.",
    "christmas": "Christmas là mùa quà tặng lớn nhất cuối năm. POD phù hợp với hoodie, sweatshirt, mug, family matching, ornament-style graphics và funny holiday quotes.",
}


class MarketAdviceAgent:
    def __init__(self, suggestion_agent=None):
        self.suggestion_agent = suggestion_agent or MarketSuggestionAgent()

    def run(self, route: dict, message: str, last_market_advice: dict | None = None) -> dict:
        kind = route.get("kind") or "design_advice"
        country = route.get("country") or parse_country(message) or (last_market_advice or {}).get("country") or "US"
        month = route.get("month") or self._month_from_season(route.get("season"), country) or (last_market_advice or {}).get("month") or date.today().month
        suggestion = self.suggestion_agent.run(country, month)
        event = route.get("event") or self._first_matching_event(suggestion, last_market_advice) or suggestion["events"][0]
        product_type = route.get("product_type") or suggestion["product_types"][0]
        answer = self._format_answer(kind, country, suggestion, event, product_type, last_market_advice)
        params = {
            "kind": kind,
            "country": country,
            "month": suggestion["month"],
            "event": event,
            "product_type": product_type,
        }
        if route.get("season"):
            params["season"] = route["season"]
        data = {"source": "market_suggestion", "router": "llm_semantic", "kind": kind, **suggestion}
        data["event"] = event
        data["product_type"] = product_type
        return {
            "answer": answer,
            "intent": "market_advice",
            "tool_calls": [],
            "api": None,
            "params": params,
            "data": data,
            "notes": ["Semantic market routing selected advice; market grounding is deterministic."],
        }

    def _format_answer(self, kind, country, suggestion, event, product_type, last_market_advice):
        products = ", ".join(suggestion["product_types"][:3])
        if kind == "event_advice":
            events = suggestion["events"][:4]
            return (
                f"Sắp tới ở {country} có các event nên làm design:\n"
                + "\n".join(f"- {item}" for item in events)
                + f"\n\nSản phẩm nên ưu tiên: {products}. Nếu muốn chuyển event thành SKU cụ thể, hãy hỏi: Tìm T-shirt ship {country} cho {events[0]}."
            )
        if kind == "niche_advice":
            niches = [
                f"{event} gift buyer / local holiday",
                f"{country} local pride with bold readable quote",
                "family matching / couple gift",
                f"funny occupation or hobby quote on {product_type}",
                f"minimal {suggestion['season']} icon pattern",
            ]
            return (
                f"Gợi ý niche {product_type} cho {country}:\n"
                + "\n".join(f"- {item}" for item in niches)
                + f"\n\nNếu muốn tìm SKU phù hợp để lên đơn, hãy hỏi: Tìm SKU {product_type} ship {country}."
            )
        if kind == "season_product_advice":
            return (
                f"Mùa {suggestion['season']} ở {country}: nên ưu tiên {products}.\n\n"
                f"Lý do: {suggestion['weather_context']}. Event gần nhất có thể khai thác: {', '.join(suggestion['events'][:3])}.\n\n"
                f"Nếu muốn chọn SKU để bán ngay, hãy hỏi: Tìm SKU {suggestion['product_types'][0]} ship {country}."
            )
        if kind in {"event_explanation", "market_follow_up"}:
            explanation = self._event_explanation(event, last_market_advice)
            if explanation:
                return explanation
            return f"Đây là event/seasonal keyword trong market vừa gợi ý. Với {country}, bạn có thể khai thác các event: {', '.join(suggestion['events'][:4])}."

        design_ideas = [
            f"{event} deal countdown typography",
            f"{country} local gift buyer theme",
            f"{suggestion['season']} minimal icon pattern",
            "family matching / couple gift angle",
            "funny niche quote with bold readable text",
        ]
        return (
            f"Gợi ý design cho {event} ở {country}: nên ưu tiên các sản phẩm {products}.\n\n"
            "Ý tưởng design có thể làm:\n"
            + "\n".join(f"- {idea}" for idea in design_ideas)
            + f"\n\nNếu bạn muốn biến một ý tưởng thành SKU cụ thể, hãy hỏi thêm market + product, ví dụ: Tìm {suggestion['product_types'][0]} ship {country} cho {event}."
        )

    def _month_from_season(self, season, country):
        if not season:
            return None
        season = str(season).lower()
        southern = (country or "").upper() == "AU"
        months = {
            "summer": 1 if southern else 7,
            "fall": 4 if southern else 10,
            "autumn": 4 if southern else 10,
            "winter": 7 if southern else 12,
            "spring": 10 if southern else 4,
            "hot/rainy": 6,
        }
        return months.get(season)

    def _first_matching_event(self, suggestion, last_market_advice):
        last_events = (last_market_advice or {}).get("events") or []
        for event in suggestion["events"]:
            if event in last_events:
                return event
        return None

    def _event_explanation(self, event, last_market_advice):
        normalized = str(event or "").lower()
        for term, description in EVENT_DESCRIPTIONS.items():
            if term in normalized:
                return description
        for event_name in (last_market_advice or {}).get("events") or []:
            event_text = str(event_name).lower()
            for term, description in EVENT_DESCRIPTIONS.items():
                if term in event_text:
                    return description
        return None
