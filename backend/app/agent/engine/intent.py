import re
from typing import Dict, Any, Tuple, Optional, List

ACTIVE_MARKETS = [
    {"target_market": "US", "countries": ["US"]},
    {"target_market": "EU", "countries": ["DE", "FR", "GB"]},
    {"target_market": "VN", "countries": ["VN"]},
    {"target_market": "AU_NZ", "countries": ["AU", "NZ"]},
    {"target_market": "ZA", "countries": ["ZA"]},
]

COUNTRY_TO_MARKET = {
    country: market["target_market"]
    for market in ACTIVE_MARKETS
    for country in market["countries"]
}



# CATEGORY_MAP ordered by priority: Specific (P1) → Demographic (P2) → Functional (P3) → Decor (P4) → Catch-all (P5)
# Accessories (catch-all) MUST be last to avoid premature matching on shared triggers like "ornament", "trang trí"
CATEGORY_MAP = {
    # === PRIORITY 1: SPECIFIC PRODUCT TYPES ===
    "T-Shirts": ["tshirt", "t-shirt", "tshirts", "t-shirts", "áo thun", "ao thun", "áo phông", "ao phong", "tee", "tees", "hawaii shirt", "jersey shirt"],
    "Mugs": ["mug", "mugs", "cốc", "coc", "ly", "ly sứ", "ly su", "tách", "tach", "ceramic mug", "latte mug"],
    "Tank Tops": ["tank top", "tank tops", "ba lỗ", "áo ba lỗ", "ao ba lo", "muscle tank", "racerback tank"],
    "Hoodies": ["hoodie", "hoodies", "áo mũ", "ao mu", "áo nỉ có mũ", "ao ni co mu", "zip hoodie"],
    "Sweatshirts": ["sweatshirt", "sweatshirts", "sweater", "áo nỉ", "ao ni", "crewneck", "ugly sweater"],
    "Blankets": ["blanket", "blankets", "chăn", "chan", "fleece blanket", "sherpa blanket", "minky blanket"],
    "Polo Shirts": ["polo", "polo shirt", "polo shirts", "áo polo", "ao polo", "bowling jersey", "pmp", "pwp", "zpbj"],
    # === PRIORITY 2: DEMOGRAPHIC CATEGORIES ===
    "Baby & Kids": ["baby", "kids", "kid", "toddler", "youth", "trẻ em", "tre em", "em bé", "em be", "onesie", "sơ sinh"],
    # === PRIORITY 3: FUNCTIONAL CATEGORIES ===
    "Pajamas & Sleepwear": ["pajama", "pajamas", "pijama", "sleepwear", "đồ ngủ", "do ngu", "quần ngủ", "quan ngu", "satin pajama"],
    "Bottoms & Shorts": ["bottoms", "quần", "quan", "pants", "shorts", "basketball shorts", "hawaiian shorts", "sweatpant", "leggings"],
    "Sportswear": ["sportswear", "thể thao", "the thao", "football jersey", "soccer jersey", "sports bra", "leggings"],
    # === PRIORITY 4: DECOR CATEGORIES ===
    "Ornaments & Gifts": ["ornament", "ornaments", "trang trí", "quà tặng", "acrylic ornament"],
    "Home Decor & Flags": ["home decor", "flags", "cờ", "garden flag", "house flag", "wood sign", "doormat", "đồng hồ", "thảm"],
    # === PRIORITY 5: CATCH-ALL (MUST BE LAST) ===
    "Accessories": ["accessories", "phụ kiện", "phu kien", "tất", "vớ", "socks", "sticker", "keychain", "móc khóa", "moc khoa", "canvas", "poster", "tumbler", "bottle", "clock", "towel", "pillow", "sneaker", "shoes", "mouse pad", "suncatcher", "candle holder", "night light", "plaque", "acrylic plaque", "acrylic block", "wallet insert", "phone grip", "phone charm"],
}

ACCESSORY_LEAF_PRODUCT_TYPE_BY_TRIGGER = (
    (("crew socks", "crew sock", "tất", "vớ", "socks", "sock"), "Crew Socks"),
    (("dad hat", "dad cap"), "Dad Hat"),
    (("trucker hat",), "Trucker Hat"),
    (("bucket hat",), "Bucket Hat"),
    (("classic cap", "mũ đội", "mu doi", "mũ nón", "mu non", "nón", "non", "hat", "cap"), "Classic Cap"),
    (("doormat", "thảm chùi chân", "tham chui chan"), "Doormat"),
    (("sticker", "stickers"), "Sticker"),
)
ACCESSORY_LEAF_PRODUCT_TYPES = {product_type.lower() for _, product_type in ACCESSORY_LEAF_PRODUCT_TYPE_BY_TRIGGER}

_cached_categories = None
_cached_shipping_country_codes = None


def get_all_categories_dynamic() -> list:
    global _cached_categories
    if _cached_categories is not None:
        return _cached_categories
    try:
        from app.database import engine
        from app.models.catalog import Product
        from sqlmodel import Session, select
        with Session(engine) as session:
            cats = [r for r in session.exec(select(Product.category).distinct()).all() if r]
            _cached_categories = cats
            return cats
    except Exception:
        return ["T-Shirts", "Mugs", "Hoodies", "Sweatshirts", "Tank Tops", "Accessories"]


def country_flag(code: str) -> str:
    country_code = (code or "").strip().upper()
    if len(country_code) != 2 or not country_code.isalpha():
        return ""
    return "".join(chr(127397 + ord(char)) for char in country_code)


def get_shipping_country_codes_dynamic() -> set[str]:
    global _cached_shipping_country_codes
    if _cached_shipping_country_codes is not None:
        return _cached_shipping_country_codes
    try:
        from app.database import engine
        from app.models.catalog import ShippingZone
        from sqlmodel import Session, select
        with Session(engine) as session:
            codes = {str(code).upper() for code in session.exec(select(ShippingZone.country_code)).all() if code}
            _cached_shipping_country_codes = codes
            return codes
    except Exception:
        return set(COUNTRY_TO_MARKET.keys())


def get_shipping_country_option(code: str) -> Optional[dict[str, str]]:
    country_code = (code or "").strip().upper()
    if not country_code:
        return None
    try:
        from app.database import engine
        from app.models.catalog import ShippingZone
        from sqlmodel import Session, select
        with Session(engine) as session:
            zone = session.exec(select(ShippingZone).where(ShippingZone.country_code == country_code)).first()
            if not zone:
                return None
            return {"code": zone.country_code.upper(), "name": zone.country_name, "flag": country_flag(zone.country_code)}
    except Exception:
        return None


def extract_country_explanation_code(message: str) -> Optional[str]:
    msg = message.strip().lower()
    if not any(term in msg for term in ["nước", "nuoc", "quốc gia", "quoc gia", "country"]):
        return None
    match = re.search(r"\b([a-z]{2})\b", msg)
    if not match:
        return None
    code = match.group(1).upper()
    if code in get_shipping_country_codes_dynamic():
        return code
    return None


def is_global_availability_query(message: str) -> bool:
    msg = re.sub(r"\s+", " ", message.strip().lower())
    market_question = any(term in msg for term in [
        "thị trường nào", "thi truong nao", "nước nào", "nuoc nao", "quốc gia nào", "quoc gia nao",
        "market nào", "which market", "which markets", "which country", "which countries",
    ])
    availability_signal = any(term in msg for term in [" có ", "co ", "available", "support", "hỗ trợ", "ho tro", "ship"])
    return market_question and availability_signal


def normalize_slots(slots: Dict[str, Any]) -> Dict[str, Any]:
    """Chuẩn hóa slots sau khi đã có dữ liệu từ LLM hoặc form input."""
    new_slots = slots.copy()

    country = new_slots.get("country")
    if country:
        country_upper = str(country).strip().upper()
        new_slots["country"] = country_upper
        if country_upper in COUNTRY_TO_MARKET:
            new_slots["target_market"] = COUNTRY_TO_MARKET[country_upper]

    target_market = new_slots.get("target_market")
    if target_market:
        market_upper = str(target_market).strip().upper()
        if market_upper in ["AU", "NZ", "SOUTHERN_HEMISPHERE", "SOUTHERN HEMISPHERE"]:
            market_upper = "AU_NZ"
        new_slots["target_market"] = market_upper
        if not new_slots.get("country"):
            if market_upper == "EU":
                new_slots["country"] = "DE"
            elif market_upper == "AU_NZ":
                new_slots["country"] = "AU"
            elif market_upper in ["US", "VN", "ZA"]:
                new_slots["country"] = market_upper

    if not new_slots.get("month"):
        new_slots["month"] = 6

    product_type = new_slots.get("product_type")
    if product_type:
        pt_lower = str(product_type).lower()
        if pt_lower not in ACCESSORY_LEAF_PRODUCT_TYPES:
            matched_cat = None
            for cat, synonyms in CATEGORY_MAP.items():
                if pt_lower in [c.lower() for c in synonyms] or pt_lower == cat.lower():
                    matched_cat = cat
                    break
            if matched_cat:
                new_slots["product_type"] = matched_cat

    return new_slots



def detect_language(message: str) -> str:
    """Nhận dạng ngôn ngữ qua dấu tiếng Việt hoặc từ khóa đặc trưng."""
    normalized = message.lower()
    if re.search(r'[àáảãạăằắẳẵặâầấẩẫậèéẽẻẹêềếểễệđìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]', message) or \
       any(w in normalized for w in ["tìm", "gợi ý", "mùa", "nên", "bán", "ship", "đặt", "đơn", "xưởng", "lãi", "giá", "vận chuyển", "lợi nhuận", "biên", "thị trường"]):
        return "vi"
    return "en"


VIETNAMESE_HINT_PATTERN = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẽẻẹêềếểễệđìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]",
    re.IGNORECASE,
)

VIETNAMESE_HINT_WORDS = {
    "tìm", "tim", "gợi", "goi", "mùa", "nên", "nen", "bán", "ban", "mua",
    "đặt", "dat", "đơn", "don", "xưởng", "xuong", "lãi", "lai", "giá", "gia",
    "vận", "van", "chuyển", "chuyen", "lợi", "loi", "nhuận", "nhuan", "biên", "bien",
    "thị", "thi", "trường", "truong", "so", "sánh", "sanh", "sản", "san", "phẩm", "pham",
    "quốc", "quoc", "nước", "nuoc", "tính", "tinh", "cho", "các", "cac", "này", "nay", "kia",
    "ao", "thun", "di",
}

ENGLISH_HINT_WORDS = {
    "find", "recommend", "compare", "calculate", "margin", "ship", "shipping", "country", "market",
    "factory", "factories", "product", "products", "cost", "price", "profit", "delivery",
    "can", "you", "this", "that", "for", "sell", "sales", "summer", "winter",
}

SHORT_CONFIRMATION_PAYLOADS = {
    "yes", "no", "ok", "okay", "y", "n", "confirm", "confirmed", "continue",
    "đồng ý", "dong y", "xác nhận", "xac nhan", "tiếp tục", "tiep tuc", "có", "co", "không", "khong",
}


def _tokenize_language_words(message: str) -> list[str]:
    return re.findall(r"[a-zA-ZÀ-ỹ]+", (message or "").lower())


def _language_signal(message: str) -> Optional[str]:
    normalized = (message or "").strip().lower()
    if not normalized:
        return None
    if VIETNAMESE_HINT_PATTERN.search(normalized):
        return "vi"

    words = _tokenize_language_words(normalized)
    vietnamese_hits = sum(1 for word in words if word in VIETNAMESE_HINT_WORDS)
    english_hits = sum(1 for word in words if word in ENGLISH_HINT_WORDS)

    if vietnamese_hits >= 2 and vietnamese_hits >= english_hits:
        return "vi"
    if english_hits >= 2 and english_hits > vietnamese_hits:
        return "en"
    if english_hits >= 1 and len(words) >= 3 and english_hits > vietnamese_hits:
        return "en"
    return None


def _is_ambiguous_language_payload(message: str) -> bool:
    normalized = re.sub(r"\s+", " ", (message or "").strip())
    if not normalized:
        return True

    lowered = normalized.lower()
    if lowered in SHORT_CONFIRMATION_PAYLOADS:
        return True
    if re.fullmatch(r"[A-Za-z]{2}", normalized):
        return True
    if re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{2,}", normalized):
        return True

    words = _tokenize_language_words(normalized)
    if len(words) <= 2 and _language_signal(normalized) is None:
        return True
    return False


def _latest_clear_user_language(history: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    if not history:
        return None
    for msg in reversed(history):
        if msg.get("role") != "user":
            continue
        content = str(msg.get("content", ""))
        if _is_ambiguous_language_payload(content):
            continue
        signal = _language_signal(content)
        if signal:
            return signal
    return None


def resolve_effective_language(message: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    signal = _language_signal(message)
    is_ambiguous = _is_ambiguous_language_payload(message)
    if signal and not is_ambiguous:
        return signal

    if is_ambiguous:
        history_language = _latest_clear_user_language(history)
        if history_language:
            return history_language

    return detect_language(message)


def language_runtime_instruction(lang: str) -> str:
    if lang == "vi":
        return (
            "[CRITICAL] The active conversation language is VIETNAMESE. You must strictly output "
            "all your thoughts, bullet summaries, recommendations, and prose text in VIETNAMESE "
            "for this turn, regardless of the language of the tool outputs or short token payloads."
        )
    return (
        "[CRITICAL] The active conversation language is ENGLISH. You must strictly output "
        "all your thoughts, bullet summaries, recommendations, and prose text in ENGLISH "
        "for this turn, regardless of the language of the tool outputs or short token payloads."
    )


DOMAINS = {
    "mugs": ["cốc", "coc", "ly", "tách", "tach", "mug", "mugs"],
    "kids": ["trẻ em", "tre em", "em bé", "em be", "sơ sinh", "so sinh", "kid", "kids", "baby", "youth", "toddler", "child", "children", "onesie"],
    "pants": ["quần", "quan", "pants", "shorts", "leggings", "bottoms", "pajama", "pajamas", "boxer", "boxers", "sweatpant", "sweatpants"],
    "shirts": ["áo", "ao", "shirt", "t-shirt", "tshirt", "tee", "hoodie", "sweatshirt", "sweater", "tank"],
    "caps": ["mũ", "mu", "nón", "non", "cap", "hat", "hats", "caps", "bucket hat", "beanie"],
    "decor": ["flags", "cờ", "co", "đồng hồ", "dong ho", "thảm", "tham", "blanket", "chăn", "chan", "pillow", "gối", "goi", "ornament", "trang trí", "trang tri", "keychain", "móc khóa", "moc khoa", "tất", "vớ", "socks", "sticker", "ornaments"]
}

DEMOGRAPHICS = {
    "kids": ["trẻ em", "tre em", "em bé", "em be", "sơ sinh", "so sinh", "kid", "kids", "baby", "youth", "toddler", "child", "children", "onesie"],
    "women": ["nữ", "nu", "women", "women's", "lady", "lady's", "ladies", "female", "woman", "gái", "gai"],
    "men": ["nam", "men", "men's", "male", "man", "trai"]
}


def _contains_word_local(text_value: str, word: str) -> bool:
    if not text_value or not word:
        return False
    text_clean = re.sub(r'\s+', ' ', text_value.replace("|", " ").replace("-", " ")).strip()
    word_clean = re.sub(r'\s+', ' ', word.replace("|", " ").replace("-", " ")).strip()
    pattern = rf"(?<!\w){re.escape(word_clean)}(?!\w)"
    return bool(re.search(pattern, text_clean, re.UNICODE))


def _accessory_leaf_product_type(message: str) -> Optional[str]:
    msg = (message or "").lower()
    for triggers, product_type in ACCESSORY_LEAF_PRODUCT_TYPE_BY_TRIGGER:
        if any(_contains_word_local(msg, trigger) for trigger in triggers):
            return product_type
    return None


def get_message_domain(message: str) -> Optional[str]:
    msg = message.lower()
    for domain, triggers in DOMAINS.items():
        if any(_contains_word_local(msg, trigger) for trigger in triggers):
            return domain
    return None


def get_slots_domain(slots: Dict[str, Any]) -> Optional[str]:
    pt = str(slots.get("product_type") or "").lower()
    sku = str(slots.get("sku") or "").lower()
    for domain, triggers in DOMAINS.items():
        if any(trigger in pt or trigger in sku for trigger in triggers):
            return domain
    return None


def get_message_demographic(message: str) -> Optional[str]:
    msg = message.lower()
    for demo, triggers in DEMOGRAPHICS.items():
        if any(_contains_word_local(msg, trigger) for trigger in triggers):
            return demo
    return None


def get_slots_demographic(slots: Dict[str, Any]) -> Optional[str]:
    pt = str(slots.get("product_type") or "").lower()
    sku = str(slots.get("sku") or "").lower()
    for demo, triggers in DEMOGRAPHICS.items():
        if any(trigger in pt or trigger in sku for trigger in triggers):
            return demo
    return None


def is_pure_pricing_adjustment_fn(message: str) -> bool:
    msg = message.lower()
    sell_match = re.search(r'(?:bán\s*lẻ|giá\s*lẻ|giá\s*bán\s*lẻ|bán|giá\s*bán|selling\s*price|retail\s*price|retail|giá)\s*(?:\$)?\s*(\d+(?:\.\d+)?)\s*(?:\$|đô|usd|eur|đ)?', msg)
    margin_match = re.search(r'(?:margin|lợi\s*nhuận)\s*(?:tối\s*thiểu|min|trên|hơn|lớn\s*hơn|>|>=|over|above|at\s*least)?\s*(\d+)\s*%', msg)
    pure_price_match = re.search(r'(?:\$)\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:\$|đô|usd|eur|đ)', msg)

    has_price_keyword = bool(sell_match or margin_match or pure_price_match)

    product_keywords = [
        "áo", "ao", "quần", "quan", "mũ", "mu", "cốc", "coc", "ly", "tách", "tach", "onesie", "shirt", "pant", "mug", "hoodie", "pillow", "hat", "cap", "bra", "blanket",
        "bag", "ornament", "candle", "tote", "block", "suncatcher", "flag", "t-shirt", "tshirt", "pajama", "sweatpant", "jersey", "leggings", "polo", "tất", "vớ", "socks", "sticker", "keychain"
    ]
    has_product_keyword = any(_contains_word_local(msg, pw) for pw in product_keywords)

    return has_price_keyword and not has_product_keyword


def parse_intent_and_slots(message: str, slots: Dict[str, Any], current_intent: Optional[str], history: Optional[List[Dict[str, Any]]] = None) -> Tuple[str, Dict[str, Any]]:
    """Heuristic router nhẹ: giữ intent keyword/form-data, để LLM sở hữu geography và temporal slots."""
    msg = message.lower()
    new_slots = slots.copy()

    explicit_country = None
    if re.search(r"\b(uk|gb|united kingdom)\b|sang\s+anh|anh\s+quốc|anh\s+quoc", msg):
        explicit_country = "GB"
    elif re.search(r"\b(de|germany)\b|đức|duc", msg):
        explicit_country = "DE"
    elif re.search(r"\b(us|usa|united states)\b|california|mỹ|my", msg):
        explicit_country = "US"
    else:
        stripped_code = message.strip().upper()
        if re.fullmatch(r"[A-Z]{2}", stripped_code) and stripped_code in get_shipping_country_codes_dynamic():
            explicit_country = stripped_code
    if explicit_country:
        new_slots["country"] = explicit_country

    is_pure_adjustment = is_pure_pricing_adjustment_fn(message)

    if is_pure_adjustment:
        # Giữ nguyên product_type và các thông tin cũ từ slots
        if "product_type" in slots:
            new_slots["product_type"] = slots["product_type"]
        if "sku" in slots:
            new_slots["sku"] = slots["sku"]

    intent = current_intent or "general_chat"
    if current_intent == "global_availability" and explicit_country and (new_slots.get("product_type") or new_slots.get("sku")):
        intent = "recommend"

    form_data = {}
    for line in message.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            form_data[k.strip().lower()] = v.strip()

    if form_data:
        if "catalog_sku" in form_data:
            # Preserve original SKU case (e.g. USBBC3001DTF-Black-S) - do NOT uppercase
            new_slots["sku"] = form_data["catalog_sku"].strip()
        if "quantity" in form_data:
            try:
                new_slots["quantity"] = int(form_data["quantity"])
            except ValueError:
                pass
        if "print_sides" in form_data:
            new_slots["print_sides"] = form_data["print_sides"]
        if "shipping_carrier" in form_data:
            new_slots["shipping_carrier"] = form_data["shipping_carrier"]

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
            if "shipping_email" in form_data:
                shipping_address["email"] = form_data["shipping_email"]
            if "shipping_phone" in form_data:
                shipping_address["phone"] = form_data["shipping_phone"]
            new_slots["shipping_address"] = shipping_address
            intent = "create_order"

    if not is_pure_adjustment:
        # Reset slots khi phát hiện sự chuyển đổi phân khúc sản phẩm hoặc đối tượng nhân khẩu học
        msg_domain = get_message_domain(message)
        slots_domain = get_slots_domain(slots)
        msg_demo = get_message_demographic(message)
        slots_demo = get_slots_demographic(slots)

        is_domain_switch = (msg_domain is not None and slots_domain is not None and msg_domain != slots_domain)
        is_demo_switch = (msg_demo is not None and slots_demo is not None and msg_demo != slots_demo)
        explicit_keep = any(w in msg for w in ["giữ nguyên", "giu nguyen", "keep target", "keep market", "keep margin", "như cũ", "nhu cu", "giữ lại", "giu lai"])

        if (is_domain_switch or is_demo_switch) and not explicit_keep:
            # Flush/Reset các tham số lịch sử
            for key in ["min_margin", "product_type", "sku", "max_base_cost", "max_shipping_days", "selling_price", "quantity", "print_sides", "country", "target_market"]:
                if key in new_slots:
                    del new_slots[key]

        is_discovery = any(w in msg for w in [
            "ngoài", "khác", "loại khác", "sản phẩm khác", "danh mục",
            "nhiều loại", "đa dạng", "variety", "alternative", "other than", "besides", "except"
        ])

        accessory_leaf_product_type = _accessory_leaf_product_type(message)
        accessories_exceptions = ["tất", "vớ", "socks", "trang trí", "ornament", "sticker", "keychain", "móc khóa", "moc khoa"]
        if "polo" in msg and not any(acc in msg for acc in accessories_exceptions):
            new_slots["product_type"] = "polo"
            if intent == "general_chat":
                intent = "recommend"
        elif accessory_leaf_product_type:
            new_slots["product_type"] = accessory_leaf_product_type
            if intent == "general_chat":
                intent = "recommend"
        elif is_discovery:
            exclude_pt = ""
            db_categories = get_all_categories_dynamic()
            for cat in db_categories:
                synonyms = CATEGORY_MAP.get(cat, [])
                if any(_contains_word_local(msg, syn) for syn in synonyms) or _contains_word_local(msg, cat.lower()):
                    exclude_pt = f"_{cat}"
                    break

            new_slots["product_type"] = f"alternative{exclude_pt}"
            if intent == "general_chat":
                intent = "recommend"
        else:
            # Match category từ CATEGORY_MAP (14 categories mới)
            matched_cat = None
            for cat in CATEGORY_MAP.keys():
                synonyms = CATEGORY_MAP.get(cat, [])
                if any(_contains_word_local(msg, syn) for syn in synonyms) or _contains_word_local(msg, cat.lower()):
                    matched_cat = cat
                    break

            if matched_cat:
                new_slots["product_type"] = matched_cat
                if intent == "general_chat":
                    intent = "recommend"
            else:
                # Fallback: extract từ query
                search_intent_indicators = [
                    "tìm", "gợi ý", "sản phẩm", "catalog", "bán", "mua", "recommend", "suggest", "product", "items", "show", "cần", "muốn",
                    "áo", "quần", "mũ", "cốc", "ly", "onesie", "shirt", "pant", "mug", "hoodie", "pillow", "hat", "cap", "bra", "blanket",
                    "bag", "ornament", "candle", "tote", "block", "suncatcher", "flag", "t-shirt", "tshirt", "pajama", "sweatpant", "jersey",
                    "leggings", "polo"
                ]
                if any(w in msg for w in search_intent_indicators):
                    clean_msg = message.strip()
                    prefixes_to_strip = [
                        "tìm kiếm sản phẩm", "tim kiem san pham",
                        "gợi ý cho tôi", "goi y cho toi",
                        "tôi muốn tìm", "toi muon tim",
                        "tôi muốn mua", "toi muon mua",
                        "tìm sản phẩm", "tim san pham",
                        "tìm cho tôi", "tim cho toi",
                        "cho tôi xem", "cho toi xem",
                        "search for",
                        "tôi cần", "toi can",
                        "show me", "find me",
                        "search",
                        "show", "find",
                        "tìm", "tim"
                    ]
                    for prefix in prefixes_to_strip:
                        if clean_msg.lower().startswith(prefix):
                            clean_msg = clean_msg[len(prefix):].strip()
                            break
                    clean_msg = re.sub(r'^[,\.\?\!\s]+|[,\.\?\!\s]+$', '', clean_msg)
                    if clean_msg:
                        new_slots["product_type"] = clean_msg
                        if intent == "general_chat":
                            intent = "recommend"

            if "matching product" in msg:
                new_slots["product_type"] = message.strip()
                if intent == "general_chat":
                    intent = "recommend"

        if is_global_availability_query(message):
            new_slots.pop("country", None)
            new_slots.pop("target_market", None)
            new_slots.pop("_missing_field", None)
            new_slots.pop("_pending_country", None)
            new_slots.pop("_active_items", None)
            new_slots.pop("_active_skus", None)
            new_slots.pop("_active_product_ids", None)
            intent = "global_availability"

        # Category isolation flush: when product_type changes between turns,
        # purge category-specific params to prevent cross-category slot bleeding.
        # Must compare normalized forms since old slots go through normalize_slots()
        # but new_slots may still hold raw values (e.g. "polo" vs "Polo Shirts").
        def _resolve_cat(raw_val):
            if not raw_val:
                return None
            rv_lower = str(raw_val).lower()
            for _cat in CATEGORY_MAP.keys():
                _syns = CATEGORY_MAP.get(_cat, [])
                if rv_lower in [s.lower() for s in _syns] or rv_lower == _cat.lower():
                    return _cat
            return raw_val

        new_pt = _resolve_cat(new_slots.get("product_type"))
        old_pt = _resolve_cat(slots.get("product_type"))
        if new_pt is not None and new_pt != old_pt:
            for key in ['max_base_cost', 'selling_price', 'min_margin', 'max_shipping_days', 'print_sides', 'sku', 'quantity', '_active_items', '_active_skus', '_active_product_ids']:
                new_slots.pop(key, None)
                slots.pop(key, None)

    if any(w in msg for w in ["system metadata", "system_metadata", "thông tin hệ thống", "metadata hệ thống", "trạng thái hệ thống", "api metadata", "database metadata"]):
        intent = "get_system_metadata"

    if any(w in msg for w in ["hỗ trợ mấy thị trường", "hỗ trợ bao nhiêu thị trường", "các thị trường đang hỗ trợ", "thị trường đang hỗ trợ", "supported markets", "active markets", "market coverage"]):
        intent = "capability_discovery"

    budget_match = re.search(
        r'(?:dưới|dưới\s*khoảng|dưới\s*mức|<|under)\s*(?:\$)?\s*(\d+(?:\.\d+)?)\s*(?:\$|đô|usd|eur|đ)?|(?:giá\s*)?(?:tầm|khoảng)?\s*(?:\$)?\s*(\d+(?:\.\d+)?)\s*(?:\$|đô|usd|eur|đ)?\s*(?:đổ\s*lại|trở\s*xuống|or\s*less|max)',
        msg,
    )
    if budget_match:
        new_slots["max_base_cost"] = float(budget_match.group(1) or budget_match.group(2))
        if intent == "general_chat":
            intent = "recommend"

    ship_match = re.search(r'(?:ship\s*|giao\s*|vận\s*chuyển\s*)?(?:dưới|nhanh\s*hơn|<|under|within)\s*(\d+)\s*(?:ngày|day)', msg)
    if ship_match:
        new_slots["max_shipping_days"] = int(ship_match.group(1))

    sell_match = re.search(r'(?:bán\s+giá|bán\s*lẻ|giá\s*lẻ|giá\s*bán\s*lẻ|bán|giá\s*bán|selling\s*price|retail\s*price|retail|giá)\s*(?:\$)?\s*(\d+(?:\.\d+)?)\s*(?:\$|đô|usd|eur|đ)?', msg)
    if sell_match:
        new_slots["selling_price"] = float(sell_match.group(1))
        if intent in ["general_chat", "recommend"]:
            intent = "calculate_margin"
    elif not sell_match and not budget_match:
        pure_price_match = re.search(r'(?:\$)\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:\$|đô|usd|eur|đ)', msg)
        if pure_price_match:
            val = pure_price_match.group(1) or pure_price_match.group(2)
            new_slots["selling_price"] = float(val)
            if intent in ["general_chat", "recommend"]:
                intent = "calculate_margin"

    margin_match = re.search(r'(?:margin|lợi\s*nhuận)\s*(?:tối\s*thiểu|min|trên|hơn|lớn\s*hơn|>|>=|over|above|at\s*least)?\s*(\d+)\s*%', msg)
    if margin_match:
        new_slots["min_margin"] = float(margin_match.group(1))
        if intent in ["general_chat", "recommend"]:
            intent = "calculate_margin"

    # Match SKU on original message (preserve case), support 3+ segments
    # Try 4-segment first (e.g., USBBC3001DTF-Black-S), then 3-segment (e.g., USS3DAM11-Black-11oz)
    sku_match = re.search(r'([A-Za-z0-9]+-[A-Za-z0-9]+-[A-Za-z0-9]+-[A-Za-z0-9]+)', message)
    if not sku_match:
        sku_match = re.search(r'([A-Za-z]{2,3}-[A-Za-z]{3}-[A-Za-z]{3,4}-[A-Za-z0-9]+)', message)
    if not sku_match:
        # Match 3-segment SKUs (e.g., USS3DAM11-Black-11oz)
        sku_match = re.search(r'([A-Za-z0-9]+-[A-Za-z0-9]+-[A-Za-z0-9]+)', message)
    if sku_match:
        # Preserve original SKU case (e.g. USBBC3001DTF-Black-S) - do NOT uppercase
        new_slots["sku"] = sku_match.group(1).strip()
        if "tạo đơn" in msg or "tạo order" in msg or "order" in msg or "mua" in msg:
            intent = "create_order"
        elif intent == "general_chat":
            intent = "calculate_margin"

    qty_match = re.search(r'(?:số\s*lượng|quantity|qty|mua|lấy)\s*(\d+)', msg)
    if qty_match:
        new_slots["quantity"] = int(qty_match.group(1))

    if any(w in msg for w in ["so sánh", "so sanh", "compare", "khác nhau thế nào", "khác biệt"]):
        intent = "compare"

    if any(w in msg for w in ["xưởng", "xuong", "factory", "workshop", "warehouse", "fulfillment", "nhà in", "nha in"]):
        intent = "compare"

    if any(w in msg for w in ["tạo đơn", "tạo order", "tạo đơn hàng", "order nháp", "draft order", "checkout"]):
        intent = "create_order"
        addr_parts = message.split(",")
        address_tokens = []
        for part in addr_parts:
            part_str = part.strip()
            if not any(part_str.lower().startswith(param) for param in ["sku=", "quantity=", "shipping_email=", "shipping_phone="]):
                address_tokens.append(part_str)

        if len(address_tokens) >= 4:
            try:
                country = address_tokens[-1].upper()
                zip_code = address_tokens[-2]

                if len(address_tokens) >= 5:
                    state = address_tokens[-3]
                    city = address_tokens[-4]
                    address1 = ", ".join(address_tokens[1:-3])
                else:
                    state = ""
                    city = address_tokens[-3]
                    address1 = ", ".join(address_tokens[1:-2])

                full_name = address_tokens[0].replace("Tạo đơn cho", "").replace("tạo đơn cho", "").replace("Tạo đơn", "").replace("tạo đơn", "").strip()

                new_slots["shipping_address"] = {
                    "full_name": full_name,
                    "address1": address1,
                    "city": city,
                    "state": state,
                    "zip_code": zip_code,
                    "country": country
                }
                new_slots["country"] = country
            except Exception:
                pass

    if any(w in msg for w in ["2 mặt", "hai mặt", "cả hai mặt", "trước sau", "both sides", "two sides", "front and back", "print_sides: both"]):
        new_slots["print_sides"] = "both"
    elif any(w in msg for w in ["1 mặt", "một mặt", "mặt trước", "chỉ mặt trước", "front only", "print_sides: front"]):
        new_slots["print_sides"] = "front"
    elif any(w in msg for w in ["mặt sau", "chỉ mặt sau", "back only", "print_sides: back"]):
        new_slots["print_sides"] = "back"

    if any(w in msg for w in ["mùa", "xu hướng", "trend", "thời tiết", "lễ hội", "sự kiện", "bán gì", "gợi ý tháng", "seasonal", "weather", "holiday", "event"]):
        if intent == "general_chat":
            intent = "recommend"

    if intent in ["general_chat", "recommend"]:
        if any(w in msg for w in ["tagline", "slogan"]):
            intent = "general_knowledge_conversation"
        elif intent == "general_chat":
            normalized_msg = msg.strip()
            is_simple_greeting = normalized_msg in ["chào", "chào bạn", "hello", "hi", "xin chào", "hey", "greetings"]
            if not is_simple_greeting:
                intent = "general_knowledge_conversation"

    return intent, normalize_slots(new_slots)
