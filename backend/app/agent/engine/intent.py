import re
from typing import Dict, Any, Tuple, Optional

def normalize_slots(slots: Dict[str, Any]) -> Dict[str, Any]:
    """Chuẩn hóa và đồng bộ hóa các tham số slots (ví dụ: country và target_market)."""
    new_slots = slots.copy()
    country = new_slots.get("country")
    target_market = new_slots.get("target_market")

    # 1. Nếu có country nhưng chưa có target_market hoặc target_market chưa đúng
    if country:
        country_upper = str(country).upper()
        new_slots["country"] = country_upper
        if country_upper in ["DE", "FR"]:
            new_slots["target_market"] = "EU"
        elif country_upper == "US":
            new_slots["target_market"] = "US"
        elif country_upper == "GB":
            new_slots["target_market"] = "GB"
        elif country_upper == "VN":
            new_slots["target_market"] = "VN"
        elif country_upper == "CA":
            new_slots["target_market"] = "CA"
        elif country_upper == "AU":
            new_slots["target_market"] = "AU"
    # 2. Nếu có target_market nhưng chưa có country
    elif target_market:
        market_upper = str(target_market).upper()
        new_slots["target_market"] = market_upper
        if market_upper == "EU":
            new_slots["country"] = "DE"
        elif market_upper in ["US", "GB", "VN", "CA", "AU"]:
            new_slots["country"] = market_upper

    # Đảm bảo target_market được đặt nếu country là DE/FR mà target_market chưa có
    if new_slots.get("country") in ["DE", "FR"] and not new_slots.get("target_market"):
        new_slots["target_market"] = "EU"

    # 3. Giá trị mặc định thông minh (Intelligent default) dựa trên active catalog metrics
    if not new_slots.get("country"):
        new_slots["country"] = "US"
    if not new_slots.get("target_market"):
        new_slots["target_market"] = "US"
    if not new_slots.get("month"):
        new_slots["month"] = 6  # Mặc định là tháng 6 năm 2026 theo hệ thống

    # Tránh trường hợp product_type là "T-Shirt" (số ít) trong khi catalog mong muốn "T-Shirts" (số nhiều)
    # Tương tự với "Hoodie" -> "Hoodies", "Sweatshirt" -> "Sweatshirts", "Mug" -> "Mugs"
    product_type = new_slots.get("product_type")
    if product_type:
        pt_lower = str(product_type).lower()
        if pt_lower in ["t-shirt", "tshirt", "t-shirts", "tshirts"]:
            new_slots["product_type"] = "T-Shirts"
        elif pt_lower in ["hoodie", "hoodies"]:
            new_slots["product_type"] = "Hoodies"
        elif pt_lower in ["sweatshirt", "sweatshirts", "sweater"]:
            new_slots["product_type"] = "Sweatshirts"
        elif pt_lower in ["mug", "mugs"]:
            new_slots["product_type"] = "Mugs"

    return new_slots

def detect_language(message: str) -> str:
    """Nhận dạng ngôn ngữ qua dấu tiếng Việt hoặc từ khóa đặc trưng."""
    normalized = message.lower()
    if re.search(r'[àáảãạăằắẳẵặâầấẩẫậèéẽẻẹêềếểễệđìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]', message) or \
       any(w in normalized for w in ["tìm", "gợi ý", "mùa", "nên", "bán", "ship", "đặt", "đơn", "xưởng", "lãi", "giá", "vận chuyển", "lợi nhuận", "biên"]):
        return "vi"
    return "en"

def parse_intent_and_slots(message: str, slots: Dict[str, Any], current_intent: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    """Heuristic parser bằng Regex trích xuất intent và slots từ câu hỏi."""
    msg = message.lower()
    new_slots = slots.copy()
    intent = current_intent or "general_chat"

    # Trích xuất dữ liệu dạng form key: value
    form_data = {}
    for line in message.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            form_data[k.strip().lower()] = v.strip()

    if form_data:
        if "catalog_sku" in form_data:
            new_slots["sku"] = form_data["catalog_sku"].upper()
        if "quantity" in form_data:
            try:
                new_slots["quantity"] = int(form_data["quantity"])
            except ValueError:
                pass
        if "print_sides" in form_data:
            new_slots["print_sides"] = form_data["print_sides"]

        if any(k in form_data for k in ["shipping_name", "shipping_address1", "shipping_city", "shipping_zip", "shipping_country"]):
            shipping_address = new_slots.get("shipping_address", {})
            if not isinstance(shipping_address, dict):
                shipping_address = {}
            if "shipping_name" in form_data:
                shipping_address["full_name"] = form_data["shipping_name"]
            if "shipping_address1" in form_data:
                shipping_address["address1"] = form_data["shipping_address1"]
            if "shipping_city" in form_data:
                shipping_address["city"] = form_data["shipping_city"]
            if "shipping_state" in form_data:
                shipping_address["state"] = form_data["shipping_state"]
            if "shipping_zip" in form_data:
                shipping_address["zip_code"] = form_data["shipping_zip"]
            if "shipping_country" in form_data:
                shipping_address["country"] = form_data["shipping_country"].upper()
                new_slots["country"] = form_data["shipping_country"].upper()
            new_slots["shipping_address"] = shipping_address
            intent = "create_order"

    # 1. Trích xuất Loại sản phẩm (product_type)
    if any(w in msg for w in ["tshirt", "t-shirt", "áo thun", "ao thun", "áo phông", "ao phong"]):
        new_slots["product_type"] = "T-Shirts"
        if intent == "general_chat":
            intent = "recommend"
    elif any(w in msg for w in ["hoodie", "áo nỉ có mũ", "ao ni co mu", "áo mũ"]):
        new_slots["product_type"] = "Hoodies"
        if intent == "general_chat":
            intent = "recommend"
    elif any(w in msg for w in ["sweatshirt", "áo nỉ", "ao ni", "sweater"]):
        new_slots["product_type"] = "Sweatshirts"
        if intent == "general_chat":
            intent = "recommend"
    elif any(w in msg for w in ["mug", "cốc", "coc", "ly sứ", "ly su"]):
        new_slots["product_type"] = "Mugs"
        if intent == "general_chat":
            intent = "recommend"

    # 1.1 Phát hiện ý định hệ thống (GET_SYSTEM_METADATA)
    if any(w in msg for w in ["system metadata", "system_metadata", "thông tin hệ thống", "metadata hệ thống", "trạng thái hệ thống", "api metadata", "database metadata"]):
        intent = "get_system_metadata"

    # 2. Trích xuất Quốc gia (country) và Thị trường đích (target_market)
    has_eu_keyword = any(w in msg for w in ["đức", "de", "germany", "deutschland", "eu", "pháp", "fr", "france"])
    if has_eu_keyword:
        new_slots["target_market"] = "EU"
        if any(w in msg for w in ["đức", "de", "germany", "deutschland"]):
            new_slots["country"] = "DE"
        elif any(w in msg for w in ["pháp", "fr", "france"]):
            new_slots["country"] = "FR"
        else:
            new_slots["country"] = "DE"
    elif any(w in msg for w in ["mỹ", "us", "usa", "united states", "america"]):
        new_slots["country"] = "US"
        new_slots["target_market"] = "US"
    elif any(w in msg for w in ["anh", "gb", "uk", "united kingdom", "england"]):
        new_slots["country"] = "GB"
        new_slots["target_market"] = "GB"
    elif any(w in msg for w in ["việt nam", "vietnam", "vn", "việt"]):
        new_slots["country"] = "VN"
        new_slots["target_market"] = "VN"
    elif any(w in msg for w in ["canada", " ca ", "ontario", "quebec", "alberta", "british columbia"]):
        new_slots["country"] = "CA"
        new_slots["target_market"] = "CA"
    elif any(w in msg for w in ["australia", "au", "úc", "uc"]):
        new_slots["country"] = "AU"
        new_slots["target_market"] = "AU"

    tax_sub_regions = {
        "california": "CA", "texas": "TX", "new york": "NY", "florida": "FL", "oregon": "OR",
        "ontario": "ON", "quebec": "QC", "alberta": "AB", "british columbia": "BC",
        "đức": "DE", "duc": "DE", "germany": "DE", "deutschland": "DE",
        "pháp": "FR", "phap": "FR", "france": "FR", "netherlands": "NL", "holland": "NL",
    }
    explicit_sub_region = re.search(r'(?:state|bang|province|tỉnh|tinh|country|nước|nuoc)\s+([a-z]{2})\b', msg)
    if explicit_sub_region:
        new_slots["tax_sub_region"] = explicit_sub_region.group(1).upper()
    else:
        for name, code in tax_sub_regions.items():
            if name in msg:
                new_slots["tax_sub_region"] = code
                break

    # 3. Trích xuất Ngân sách tối đa (max_base_cost)
    budget_match = re.search(r'(?:dưới|dưới\s*khoảng|dưới\s*mức|<|under)\s*(?:\$)?\s*(\d+(?:\.\d+)?)\s*(?:\$|đô|usd|eur|đ)?', msg)
    if budget_match:
        new_slots["max_base_cost"] = float(budget_match.group(1))
        if intent == "general_chat":
            intent = "recommend"

    # 4. Trích xuất Thời gian ship tối đa (max_shipping_days)
    ship_match = re.search(r'(?:ship\s*|giao\s*|vận\s*chuyển\s*)?(?:dưới|nhanh\s*hơn|<|under|within)\s*(\d+)\s*(?:ngày|day)', msg)
    if ship_match:
        new_slots["max_shipping_days"] = int(ship_match.group(1))

    # 5. Trích xuất Giá bán mong muốn (selling_price)
    sell_match = re.search(r'(?:bán\s*lẻ|giá\s*lẻ|giá\s*bán\s*lẻ|bán|giá\s*bán|selling\s*price|sell\s*price|selling|sell|retail\s*price|retail|giá)\s*(?:\$)?\s*(\d+(?:\.\d+)?)\s*(?:\$|đô|usd|eur|đ)?', msg)
    if sell_match and not budget_match:
        new_slots["selling_price"] = float(sell_match.group(1))
        if intent == "general_chat":
            intent = "calculate_margin"
    elif not sell_match and not budget_match:
        pure_price_match = re.search(r'(?:\$)\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:\$|đô|usd|eur|đ)', msg)
        if pure_price_match:
            val = pure_price_match.group(1) or pure_price_match.group(2)
            new_slots["selling_price"] = float(val)
            if intent == "general_chat":
                intent = "calculate_margin"

    # 6. Trích xuất Margin tối thiểu (min_margin)
    margin_match = re.search(r'(?:margin|lợi\s*nhuận)\s*(?:tối\s*thiểu|min|trên|hơn|lớn\s*hơn|>|>=|over|above|at\s*least)?\s*(\d+)\s*%', msg)
    if margin_match:
        new_slots["min_margin"] = float(margin_match.group(1))
        if intent == "general_chat":
            intent = "calculate_margin"

    # 7. Trích xuất SKU
    sku_match = re.search(r'([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)', msg)
    if not sku_match:
        sku_match = re.search(r'([a-z]{2,3}-[a-z]{3}-[a-z]{3,4}-[a-z0-9]+)', msg)
    if sku_match:
        new_slots["sku"] = sku_match.group(1).upper()
        if "tạo đơn" in msg or "tạo order" in msg or "order" in msg or "mua" in msg:
            intent = "create_order"
        elif intent == "general_chat":
            intent = "calculate_margin"

    # 8. Trích xuất số lượng (quantity)
    qty_match = re.search(r'(?:số\s*lượng|quantity|qty|mua|lấy)\s*(\d+)', msg)
    if qty_match:
        new_slots["quantity"] = int(qty_match.group(1))

    # 9. Trích xuất ý định so sánh
    if any(w in msg for w in ["so sánh", "so sanh", "compare", "khác nhau thế nào", "khác biệt"]):
        intent = "compare"

    # 10. Trích xuất ý định tạo đơn hàng và địa chỉ
    if any(w in msg for w in ["tạo đơn", "tạo order", "tạo đơn hàng", "order nháp", "draft order", "checkout"]):
        intent = "create_order"
        addr_parts = message.split(",")
        if len(addr_parts) >= 4:
            try:
                new_slots["shipping_address"] = {
                    "full_name": addr_parts[0].replace("Tạo đơn cho", "").replace("tạo đơn cho", "").strip(),
                    "address1": addr_parts[1].strip(),
                    "city": addr_parts[2].strip(),
                    "zip_code": addr_parts[3].strip(),
                    "country": addr_parts[4].strip() if len(addr_parts) > 4 else new_slots.get("country", "US")
                }
            except Exception:
                pass

    # 11. Trích xuất ý định in ấn (print_sides)
    if any(w in msg for w in ["2 mặt", "hai mặt", "cả hai mặt", "trước sau", "both sides", "two sides", "front and back", "print_sides: both"]):
        new_slots["print_sides"] = "both"
    elif any(w in msg for w in ["1 mặt", "một mặt", "mặt trước", "chỉ mặt trước", "front only", "print_sides: front"]):
        new_slots["print_sides"] = "front"
    elif any(w in msg for w in ["mặt sau", "chỉ mặt sau", "back only", "print_sides: back"]):
        new_slots["print_sides"] = "back"

    # 12. Trích xuất tháng (month)
    month_match = re.search(r'(?:tháng|month)\s*(\d+)', msg)
    if month_match:
        m = int(month_match.group(1))
        if 1 <= m <= 12:
            new_slots["month"] = m
    elif any(w in msg for w in ["tháng này", "this month", "tháng hiện tại", "current month"]):
        new_slots["month"] = 6
    elif any(w in msg for w in ["tháng sau", "next month", "tháng tới"]):
        new_slots["month"] = 7
    elif any(w in msg for w in ["tháng trước", "last month"]):
        new_slots["month"] = 5
    elif any(w in msg for w in ["mùa hè", "summer", "mùa nóng"]):
        new_slots["month"] = 6
    elif any(w in msg for w in ["mùa đông", "winter", "mùa lạnh"]):
        new_slots["month"] = 12
    elif any(w in msg for w in ["mùa thu", "autumn", "fall"]):
        new_slots["month"] = 9
    elif any(w in msg for w in ["mùa xuân", "spring"]):
        new_slots["month"] = 3
    else:
        months_map = {
            "tháng một": 1, "tháng hai": 2, "tháng ba": 3, "tháng tư": 4, "tháng năm": 5, "tháng sáu": 6,
            "tháng bảy": 7, "tháng tám": 8, "tháng chín": 9, "tháng mười": 10, "tháng mười một": 11, "tháng mười hai": 12,
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        for name, val in months_map.items():
            if name in msg:
                new_slots["month"] = val
                break

    # 13. Phát hiện ý định xu hướng/mùa vụ
    if any(w in msg for w in ["mùa", "xu hướng", "trend", "thời tiết", "lễ hội", "sự kiện", "bán gì", "gợi ý tháng", "seasonal", "weather", "holiday", "event"]):
        if intent == "general_chat":
            intent = "recommend"

    # 14. Phát hiện ý định câu hỏi kiến thức chung mở rộng (General Knowledge)
    if intent in ["general_chat", "recommend"]:
        if any(w in msg for w in ["tagline", "slogan"]):
            intent = "general_knowledge_conversation"
        elif intent == "general_chat":
            normalized_msg = msg.strip()
            is_simple_greeting = normalized_msg in ["chào", "chào bạn", "hello", "hi", "xin chào", "hey", "greetings"]
            if not is_simple_greeting:
                intent = "general_knowledge_conversation"

    return intent, normalize_slots(new_slots)
