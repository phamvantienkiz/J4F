from src.agent.formatter import format_balance, format_order_detail, format_orders, format_product_detail, format_sku_detail, format_sku_search


class AnswerAgent:
    def run(self, core_result):
        intent = core_result.get("intent")
        result = core_result.get("result") or {}
        notes = core_result.get("notes") or []

        if intent == "get_balance":
            return format_balance(result)
        if intent == "list_orders":
            return format_orders(result)
        if intent == "get_order":
            return format_order_detail(result)
        if intent == "search_order_items":
            return format_sku_search(result, notes)
        if intent == "get_product":
            return format_product_detail(result, notes)
        if intent == "get_sku":
            return format_sku_detail(result, notes)
        if intent == "unknown":
            return "\n".join(notes) if notes else "Tôi chưa hiểu yêu cầu này."
        if intent == "tracking_unsupported":
            return "\n".join(notes) if notes else "Tracking chưa được bật trong core hiện tại."
        return "Tôi đã xử lý yêu cầu nhưng chưa có formatter cho intent này."
