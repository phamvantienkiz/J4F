import re
import unicodedata


ORDER_ID_PATTERN = re.compile(r"\bA\d{4,6}-[A-Z]{2}-\d+\b", re.IGNORECASE)
SKU_PATTERN = re.compile(r"\b[A-Z]{2}[A-Z0-9]+-[A-Z0-9]+(?:-[A-Z0-9]+)+\b", re.IGNORECASE)
PRODUCT_CODE_PATTERN = re.compile(r"\b[A-Z]{2,}[A-Z0-9]{2,}\b", re.IGNORECASE)


def strip_accents(value):
    value = value.replace("đ", "d").replace("Đ", "D")
    return "".join(
        char for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    )


def normalize_text(text):
    return strip_accents(text).lower()


def parse_limit(text, default=10):
    patterns = [
        r"\b(?:top|lay|xem|show|first)\s+(\d{1,3})\b",
        r"\b(\d{1,3})\s+(?:sku|san pham|product|order|don)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return max(1, min(int(match.group(1)), 100))
    return default


def parse_country(text):
    normalized = normalize_text(text)
    if re.search(r"\b(us|usa|united states|my)\b", normalized):
        return "US"
    if re.search(r"\b(vn|viet nam|vietnam)\b", normalized):
        return "VN"
    if re.search(r"\b(canada|ca)\b", normalized):
        return "CA"
    if re.search(r"\b(australia|au|uc)\b", normalized):
        return "AU"
    if re.search(r"\b(uk|gb|united kingdom|anh)\b", normalized):
        return "GB"
    if re.search(r"\b(eu|europe|chau au)\b", normalized):
        return "EU"
    return None


def parse_platform(text):
    if "etsy" in text:
        return "etsy"
    if "shopify" in text:
        return "shopify"
    if "amazon" in text:
        return "amazon"
    if "tiktok" in text or "tik tok" in text:
        return "tiktok"
    return "generic"


def parse_money_after(text, keywords):
    for keyword in keywords:
        pattern = rf"{keyword}[^0-9$]{{0,30}}\$?\s*(\d+(?:\.\d+)?)"
        match = re.search(pattern, text)
        if match:
            return float(match.group(1))
    return None


def parse_margin(text):
    match = re.search(r"(?:margin|bien loi nhuan|loi nhuan)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*%?", text)
    if match:
        value = float(match.group(1))
        return value / 100 if value > 1 else value
    return None


COLOR_ALIASES = {
    "den": "Black",
    "black": "Black",
    "trang": "White",
    "white": "White",
    "do": "Red",
    "red": "Red",
    "xanh": "Blue",
    "blue": "Blue",
    "navy": "Navy",
    "xam": "Gray",
    "gray": "Gray",
    "grey": "Gray",
    "hong": "Pink",
    "pink": "Pink",
    "green": "Green",
    "yellow": "Yellow",
    "purple": "Purple",
    "brown": "Brown",
    "ivory": "Ivory",
    "moss": "Moss",
    "pepper": "Pepper",
    "orchid": "Orchid",
}


SIZE_PATTERN = re.compile(r"\b(?:XS|S|M|L|XL|2XL|3XL|4XL|5XL|11OZ|15OZ|\d{2,3}X\d{2,3})\b", re.IGNORECASE)


def canonical_size(value):
    return value.upper().replace("X", "x") if re.fullmatch(r"\d{2,3}x\d{2,3}", value, re.IGNORECASE) else value.upper()


def parse_color(text):
    for pattern in [r"\b(?:mau|color)\s+([a-z]+)\b", r"\b([a-z]+)\s+color\b"]:
        match = re.search(pattern, text)
        if match and match.group(1) in COLOR_ALIASES:
            return COLOR_ALIASES[match.group(1)]
    for alias, color in COLOR_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return color
    return None


def parse_size(text):
    explicit = re.search(r"\b(?:size|co)\s+([a-z0-9]+(?:x[a-z0-9]+)?)\b", text, re.IGNORECASE)
    if explicit and SIZE_PATTERN.fullmatch(explicit.group(1)):
        return canonical_size(explicit.group(1))
    match = SIZE_PATTERN.search(text)
    return canonical_size(match.group(0)) if match else None


def parse_sort_by(text):
    if any(phrase in text for phrase in ["profit cao nhat", "highest profit", "best profit", "lai cao nhat", "loi nhuan cao nhat"]):
        return "profit"
    if any(phrase in text for phrase in ["margin cao nhat", "highest margin", "best margin"]):
        return "margin"
    if any(phrase in text for phrase in ["ship re nhat", "shipping re nhat", "phi ship re nhat", "cheapest shipping", "lowest shipping"]):
        return "shipping_fee"
    if re.search(r"\b(?:ship|shipping|phi ship)\b.{0,30}\bre nhat\b", text):
        return "shipping_fee"
    return None


def parse_compare_factories(text):
    return any(
        phrase in text
        for phrase in [
            "so sanh",
            "compare",
            "giua cac xuong",
            "cac xuong",
            "factory comparison",
            "compare factories",
            "compare suppliers",
        ]
    )


def parse_product_type(text):
    product_terms = [
        ("sweatshirt", "Sweatshirt"),
        ("hoodie", "Hoodie"),
        ("t-shirt", "T-shirt"),
        ("tshirt", "T-shirt"),
        ("tee", "T-shirt"),
        ("ao thun", "T-shirt"),
        ("mug", "Mug"),
        ("coc", "Mug"),
        ("tank top", "Tank top"),
        ("tank", "Tank top"),
    ]
    for term, product_type in product_terms:
        if re.search(rf"\b{re.escape(term)}\b", text):
            return product_type
    return None


def parse_delivery_days(text):
    match = re.search(r"(?:ship|delivery|giao|van chuyen)[^0-9]{0,30}(\d{1,2})\s*(?:ngay|days?|business days)\b", text)
    if match:
        return int(match.group(1))
    if any(word in text for word in ["ship", "delivery", "giao", "van chuyen"]):
        match = re.search(r"(?:duoi|under|below)\s+(\d{1,2})\s*(?:ngay|days?|business days)\b", text)
        if match:
            return int(match.group(1))
    return None


def parse_quantity(text):
    patterns = [
        r"\b(\d{1,3})\s*(?:ao|áo|item|items|cai|cái|chiec|chiếc)\b",
        r"\bquantity\s*(\d{1,3})\b",
        r"\bso luong\s*(\d{1,3})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return max(1, min(int(match.group(1)), 100))
    return 1


def parse_sku_code(text):
    match = SKU_PATTERN.search(text)
    return match.group(0) if match else None


def parse_product_code(text):
    ignored_words = {"GET", "POST", "PUT", "API", "SKU", "USD", "PRODUCT", "BASE", "CATALOG", "FIND", "CHECK", "SHOW", "XEM", "TIM", "LAY", "SHIP"}
    for match in PRODUCT_CODE_PATTERN.finditer(text):
        code = match.group(0)
        if code.upper() not in ignored_words and any(char.isdigit() for char in code):
            return code
    return None


def parse_selling_price(text):
    direct = parse_money_after(text, ["ban gia", "gia ban", "selling price", "sell price"])
    if direct is not None:
        return direct
    if "gia von" in text or "base cost" in text:
        return None

    currency_match = re.search(
        r"(?:\$|usd\s*)\s*(\d+(?:\.\d+)?)\b|\b(\d+(?:\.\d+)?)\s*(?:usd|us dollars?|dollars?|dollar|do(?:\s+la)?)\b",
        text,
    )
    if currency_match:
        return float(currency_match.group(1) or currency_match.group(2))

    if any(word in text for word in ["ban", "sell", "selling"]):
        match = re.search(r"gia[^0-9]{0,20}(\d+(?:\.\d+)?)", text)
        if match and "gia von" not in text:
            return float(match.group(1))
    return None


def parse_filters(text):
    normalized = normalize_text(text)
    return {
        "country": parse_country(text) or parse_country(normalized),
        "platform": parse_platform(normalized),
        "selling_price": parse_selling_price(normalized),
        "max_base_cost": parse_money_after(normalized, ["gia von", "base cost", "base", "cost"]),
        "max_shipping_fee": parse_money_after(normalized, ["phi ship", "shipping fee", "ship fee", "shipping cost"]),
        "max_delivery_days": parse_delivery_days(normalized),
        "min_margin": parse_margin(normalized),
        "quantity": parse_quantity(normalized),
        "color": parse_color(normalized),
        "size": parse_size(normalized),
        "product_type": parse_product_type(normalized),
        "sort_by": parse_sort_by(normalized),
        "compare_factories": parse_compare_factories(normalized),
    }


def detect_intent(text):
    normalized = normalize_text(text)
    order_id = ORDER_ID_PATTERN.search(text)
    filters = parse_filters(text)

    if any(word in normalized for word in ["balance", "so du", "tai khoan"]):
        return {"name": "get_balance"}

    if order_id and any(word in normalized for word in ["tracking", "track", "van don"]):
        return {"name": "tracking_unsupported", "order_id": order_id.group(0)}

    if order_id:
        return {"name": "get_order", "order_id": order_id.group(0)}

    sku_code = parse_sku_code(text)
    if sku_code and any(word in normalized for word in ["sku", "xem", "tim", "find", "check"]):
        return {"name": "get_sku", "sku": sku_code}

    product_code = parse_product_code(text)
    if product_code and any(word in normalized for word in ["product", "base", "san pham", "xem", "find", "check"]):
        return {"name": "get_product", "short_code": product_code}

    if any(word in normalized for word in ["sku", "san pham", "product", "catalog", "ao", "t-shirt", "hoodie", "sweatshirt", "mug", "tank"]):
        return {"name": "search_order_items", "limit": parse_limit(normalized), **filters}

    if filters["selling_price"] is not None or filters["min_margin"] is not None or filters["sort_by"] is not None:
        return {"name": "search_order_items", "limit": parse_limit(normalized), **filters}

    if any(word in normalized for word in ["order", "don", "don hang"]):
        return {"name": "list_orders", "limit": parse_limit(normalized)}

    return {"name": "unknown"}
