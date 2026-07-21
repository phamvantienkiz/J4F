from sqlmodel import Session, select
import app.database as db
from app.models.catalog import Product, ProductVariant, ShippingZone, ShippingFee
from app.services.burgerprints import BurgerPrintsClient
from app.services.catalog_search import fallback_product_ids, hybrid_search_products, ranked_product_id, ranked_product_score
from typing import List, Dict, Any, Optional
import math
import logging
import re
import datetime

logger = logging.getLogger(__name__)

SHIPPING_API_DATA_ERROR = "[ERROR: Missing Shipping API Data]"


def _normalize_delivery_time(value: Optional[str]) -> str:
    if not value:
        return SHIPPING_API_DATA_ERROR
    return value.replace("bussiness", "business")


def _debug_ascii(value) -> str:
    return str(value).encode("unicode_escape").decode("ascii")


def _normalize_shipping_country(country_code: str) -> str:
    country = (country_code or "").strip().upper()
    return "GB" if country in {"UK", "UNITED KINGDOM"} else country


def _shipping_fees_for_partner(session: Session, country_code: str, partner_name: Optional[str] = None) -> List[ShippingFee]:
    country = _normalize_shipping_country(country_code)
    zone = session.exec(select(ShippingZone).where(ShippingZone.country_code == country)).first()
    if not zone:
        return []

    if partner_name:
        partner_fees = session.exec(
            select(ShippingFee).where(
                ShippingFee.zone_id == zone.id,
                ShippingFee.partner_name == partner_name,
            )
        ).all()
        if partner_fees:
            return partner_fees

    generic_fees = session.exec(
        select(ShippingFee).where(
            ShippingFee.zone_id == zone.id,
            ShippingFee.partner_name == None,
        )
    ).all()
    if generic_fees:
        return generic_fees

    return session.exec(select(ShippingFee).where(ShippingFee.zone_id == zone.id)).all()


def _carrier_options_from_fees(fees: List[ShippingFee], quantity: int = 1) -> List[Dict[str, Any]]:
    options = []
    seen = set()
    for fee in fees:
        first_fee = fee.first_item_fee or 0.0
        additional_fee = fee.additional_item_fee or 0.0
        total_fee = first_fee + max(quantity - 1, 0) * additional_fee
        delivery_time = _normalize_delivery_time(fee.delivery_time)
        option_key = (fee.carrier, round(total_fee, 2), delivery_time)
        if option_key in seen:
            continue
        seen.add(option_key)
        options.append({
            "zone_id": fee.zone_id,
            "partner_name": fee.partner_name,
            "carrier": fee.carrier,
            "first_item_fee": round(first_fee, 2),
            "additional_item_fee": round(additional_fee, 2),
            "total_shipping": round(total_fee, 2),
            "fee": round(total_fee, 2),
            "sla": delivery_time,
            "delivery_time": delivery_time,
            "selected": False,
        })
    options.sort(key=lambda option: option["fee"])
    return options


def _selected_shipping_option(options: List[Dict[str, Any]]) -> Dict[str, Any]:
    return next((option for option in options if option.get("selected") is True), options[0] if options else {})


def _optimized_shipping_result(
    fees: List[ShippingFee],
    base_cost_value: float,
    tax_fee: float,
    quantity: int = 1
) -> tuple[float, str, str, bool, List[Dict[str, Any]]]:
    available_carriers = _carrier_options_from_fees(fees, quantity)
    if not available_carriers:
        return 0.0, SHIPPING_API_DATA_ERROR, SHIPPING_API_DATA_ERROR, True, []

    best = min(available_carriers, key=lambda option: base_cost_value + option["fee"] + tax_fee)
    best["selected"] = True
    api_sync_required = any(option["sla"] == SHIPPING_API_DATA_ERROR for option in available_carriers)
    return best["fee"], best["carrier"], best["sla"], api_sync_required, available_carriers


def _shipping_days(delivery_time: str) -> Optional[int]:
    if delivery_time == SHIPPING_API_DATA_ERROR:
        return None
    try:
        days_parts = delivery_time.replace("business", "").replace("days", "").strip().split("-")
        if len(days_parts) >= 2:
            return int(days_parts[1].strip())
        if len(days_parts) == 1:
            return int(days_parts[0].strip())
    except Exception:
        return None
    return None


def get_tax_rate(country_code: str) -> float:
    """
    Trả về thuế suất giả định dựa trên quốc gia để tính landed cost.
    - US: 8% (Sales tax trung bình)
    - EU (DE, FR, GB): 19% (VAT trung bình)
    - VN: 0% (Không tính thuế nội địa)
    """
    c = country_code.upper()
    if c == "US":
        return 0.08
    elif c in ["DE", "FR", "GB", "EU"]:
        return 0.19
    elif c == "AU":
        return 0.10
    elif c == "NZ":
        return 0.15
    elif c == "ZA":
        return 0.15
    return 0.0

def mask_pii(text: str) -> str:
    """
    Che giấu thông tin cá nhân nhạy cảm trong phản hồi chatbot.
    """
    if not text:
        return ""
    # Che giấu số điện thoại
    text = re.sub(r'\b\d{7,11}\b', lambda m: m.group(0)[:3] + "****" + m.group(0)[-2:], text)
    # Che giấu email
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                  lambda m: m.group(0)[0] + "***@" + m.group(0).split('@')[1], text)
    return text

PRODUCT_SEARCH_GROUPS = [
    # === PRIORITY 1: SPECIFIC PRODUCT TYPES ===
    {
        "category": "T-Shirts",
        "priority": 1,
        "triggers": [
            "t-shirt", "t-shirts", "tshirt", "tshirts", "áo thun", "ao thun", "áo phông", "ao phong",
            "tee", "tees", "hawaii shirt", "hawaiian shirt", "jersey shirt", "baseball jersey"
        ],
        "tokens": [
            "t-shirt", "t-shirts", "tshirt", "tshirts", "tee", "tees",
            "hawaii shirt", "jersey shirt", "baseball jersey", "football jersey", "soccer jersey",
            "gildan", "bella", "comfort colors", "canvas 3001"
        ],
        "exclusion_blacklist": [
            "tank top", "muscle tank", "racerback tank", "ba lỗ",
            "hoodie", "zip hoodie", "áo mũ",
            "sweatshirt", "crewneck", "sweater", "áo nỉ",
            "polo", "polo shirt", "áo polo", "pmp", "pwp", "zpbj"
        ]
    },
    {
        "category": "Mugs",
        "priority": 1,
        "triggers": [
            "mug", "mugs", "cốc", "coc", "ly", "ly sứ", "ly su", "tách", "tach",
            "ceramic mug", "accent mug", "magic mug", "3d mug", "latte mug"
        ],
        "tokens": [
            "mug", "mugs", "ceramic mug", "accent mug", "magic mug", "3d mug", "latte mug",
            "clear glass mug", "enamel camping mug", "glitter mug"
        ],
        "exclusion_blacklist": [
            "tumbler", "bottle", "stainless steel bottle",
            "cốc giữ nhiệt", "bình giữ nhiệt"
        ]
    },
    {
        "category": "Tank Tops",
        "priority": 1,
        "triggers": [
            "tank top", "tank tops", "ba lỗ", "áo ba lỗ", "ao ba lo",
            "muscle tank", "racerback tank", "cropped tank"
        ],
        "tokens": [
            "tank top", "tank tops", "ba lỗ", "áo ba lỗ",
            "muscle tank", "racerback tank", "cropped tank"
        ],
        "exclusion_blacklist": [
            "t-shirt", "t-shirts", "tshirt", "áo thun", "tee", "tees",
            "hoodie", "zip hoodie", "áo mũ",
            "sweatshirt", "crewneck", "áo nỉ"
        ]
    },
    {
        "category": "Hoodies",
        "priority": 1,
        "triggers": [
            "hoodie", "hoodies", "áo mũ", "ao mu", "áo nỉ có mũ", "ao ni co mu",
            "zip hoodie", "cropped hoodie", "pullover hoodie"
        ],
        "tokens": [
            "hoodie", "hoodies", "áo mũ", "áo nỉ có mũ",
            "zip hoodie", "cropped hoodie", "pullover hoodie"
        ],
        "exclusion_blacklist": [
            "t-shirt", "t-shirts", "tshirt", "áo thun", "tee",
            "tank top", "ba lỗ", "áo ba lỗ",
            "sweatshirt", "crewneck", "áo nỉ"
        ]
    },
    {
        "category": "Sweatshirts",
        "priority": 1,
        "triggers": [
            "sweatshirt", "sweatshirts", "áo nỉ", "ao ni", "crewneck", "sweater",
            "ugly sweater", "pullover"
        ],
        "tokens": [
            "sweatshirt", "sweatshirts", "áo nỉ", "crewneck", "sweater",
            "ugly sweater", "pullover"
        ],
        "exclusion_blacklist": [
            "t-shirt", "t-shirts", "tshirt", "áo thun", "tee",
            "tank top", "ba lỗ", "áo ba lỗ",
            "hoodie", "zip hoodie", "áo mũ", "áo nỉ có mũ"
        ]
    },
    {
        "category": "Blankets",
        "priority": 1,
        "triggers": [
            "blanket", "blankets", "chăn", "chan", "mền", "men",
            "fleece blanket", "sherpa blanket", "minky blanket"
        ],
        "tokens": [
            "blanket", "blankets", "chăn", "mền",
            "fleece blanket", "sherpa blanket", "minky blanket"
        ],
        "exclusion_blacklist": [
            "flag", "house flag", "garden flag",
            "doormat", "thảm chùi chân"
        ]
    },
    {
        "category": "Polo Shirts",
        "priority": 1,
        "triggers": [
            "polo", "polo shirt", "polo shirts", "áo polo", "ao polo",
            "bowling jersey", "pmp", "pwp", "zpbj"
        ],
        "tokens": [
            "polo", "polo shirt", "polo shirts", "áo polo",
            "bowling jersey", "pmp", "pwp", "zpbj"
        ],
        "exclusion_blacklist": [
            "t-shirt", "t-shirts", "tshirt", "áo thun", "tee",
            "tank top", "ba lỗ", "áo ba lỗ",
            "hoodie", "sweatshirt", "crewneck"
        ]
    },

    # === PRIORITY 2: DEMOGRAPHIC CATEGORIES ===
    {
        "category": "Baby & Kids",
        "priority": 2,
        "triggers": [
            "baby", "kids", "kid", "toddler", "youth", "trẻ em", "tre em", "em bé", "em be",
            "onesie", "sơ sinh", "so sinh", "bé gái", "bé trai"
        ],
        "tokens": [
            "baby", "kids", "kid", "toddler", "youth", "trẻ em", "em bé",
            "onesie", "sơ sinh", "bé gái", "bé trai",
            "kid t-shirt", "kid hoodie", "baby tee"
        ],
        "exclusion_blacklist": [
            "polo", "polo shirt", "áo polo",
            "sweatpant", "quần dài", "pajama"
        ]
    },

    # === PRIORITY 3: FUNCTIONAL CATEGORIES ===
    {
        "category": "Pajamas & Sleepwear",
        "priority": 3,
        "triggers": [
            "pajama", "pajamas", "pijama", "sleepwear", "đồ ngủ", "do ngu",
            "quần ngủ", "quan ngu", "satin pajama", "silk pajama", "pajama set"
        ],
        "tokens": [
            "pajama", "pajamas", "pijama", "sleepwear", "đồ ngủ", "quần ngủ",
            "satin pajama", "silk pajama", "pajama set"
        ],
        "exclusion_blacklist": [
            "bottoms", "quần", "quan", "pants", "shorts", "quần short", "quần đùi",
            "basketball shorts", "hawaiian shorts", "sweatpant", "leggings",
            "t-shirt", "áo thun", "jersey", "đồ thể thao"
        ]
    },
    {
        "category": "Bottoms & Shorts",
        "priority": 3,
        "triggers": [
            "bottoms", "quần", "quan", "pants", "shorts", "quần short", "quần đùi",
            "basketball shorts", "hawaiian shorts", "sweatpant", "leggings"
        ],
        "tokens": [
            "bottoms", "quần", "pants", "shorts", "quần short", "quần đùi",
            "basketball shorts", "hawaiian shorts", "sweatpant", "leggings"
        ],
        "exclusion_blacklist": [
            "t-shirt", "áo thun", "hoodie", "áo mũ",
            "pajama", "pajamas", "pijama", "đồ ngủ", "quần ngủ"
        ]
    },
    {
        "category": "Sportswear",
        "priority": 3,
        "triggers": [
            "sportswear", "thể thao", "the thao", "đồ thể thao", "do the thao",
            "football jersey", "soccer jersey", "sports bra", "leggings", "activewear"
        ],
        "tokens": [
            "sportswear", "thể thao", "đồ thể thao",
            "football jersey", "soccer jersey", "sports bra", "leggings", "activewear"
        ],
        "exclusion_blacklist": [
            "polo", "polo shirt", "áo polo", "pmp", "pwp",
            "t-shirt", "áo thun", "tee"
        ]
    },

    # === PRIORITY 4: DECOR CATEGORIES ===
    {
        "category": "Ornaments & Gifts",
        "priority": 4,
        "triggers": [
            "ornament", "ornaments", "trang trí", "trang tri", "quà tặng", "qua tang",
            "acrylic ornament", "ceramic ornament"
        ],
        "tokens": [
            "ornament", "ornaments", "trang trí", "quà tặng",
            "acrylic ornament", "ceramic ornament"
        ],
        "exclusion_blacklist": [
            "flag", "house flag", "garden flag",
            "doormat", "thảm chùi chân"
        ]
    },
    {
        "category": "Home Decor & Flags",
        "priority": 4,
        "triggers": [
            "home decor", "flags", "cờ", "garden flag", "house flag",
            "wood sign", "doormat", "thảm chùi chân", "đồng hồ", "dong ho"
        ],
        "tokens": [
            "home decor", "flags", "cờ", "garden flag", "house flag",
            "wood sign", "doormat", "thảm chùi chân", "đồng hồ"
        ],
        "exclusion_blacklist": [
            "ornament", "acrylic ornament", "ceramic ornament",
            "blanket", "chăn"
        ]
    },

    # === PRIORITY 5: CATCH-ALL ===
    {
        "category": "Accessories",
        "priority": 5,
        "triggers": [
            "accessories", "phụ kiện", "phu kien", "tất", "vớ", "socks",
            "sticker", "keychain", "canvas", "poster", "tumbler", "bottle",
            "doormat", "clock", "towel", "pillow", "sneaker", "shoes", "mouse pad", "suncatcher",
            "móc khóa", "moc khoa", "giày", "giay", "mũ", "mu", "mũ đội", "mu doi", "nón", "non", "cap", "hat"
        ],
        "tokens": [
            "accessories", "phụ kiện", "tất", "vớ", "socks",
            "sticker", "keychain", "canvas", "poster", "tumbler", "bottle",
            "doormat", "clock", "towel", "pillow", "sneaker", "shoes", "mouse pad", "suncatcher",
            "móc khóa", "giày", "mũ", "nón", "cap", "hat"
        ],
        "exclusion_blacklist": [
            "t-shirt", "t-shirts", "tshirt", "áo thun", "tee",
            "tank top", "ba lỗ", "áo ba lỗ",
            "hoodie", "zip hoodie", "áo mũ",
            "sweatshirt", "crewneck", "áo nỉ",
            "polo", "polo shirt", "áo polo",
            "shorts", "pants", "quần",
            "pajama", "pajamas", "đồ ngủ",
            "blanket", "chăn"
        ]
    }
]
ALL_PRODUCT_KEYWORDS = {"", "all", "tất cả", "tat ca"}
SEARCH_PRODUCT_CANDIDATE_LIMIT = 30


def _contains_term(text_value: str, term: str) -> bool:
    if not text_value or not term:
        return False
    text_clean = re.sub(r"[\s-]+", " ", text_value).strip()
    term_clean = re.sub(r"[\s-]+", " ", term).strip()
    return bool(re.search(rf"(?<!\w){re.escape(term_clean)}(?!\w)", text_clean, re.UNICODE))


ACCESSORY_LEAF_SPECS = [
    (("canvas shoes", "canvas shoe"), ("canvas shoes",), ("Canvas Shoes",)),
    (("canvas print", "framed canvas", "tranh canvas", "wall canvas"), ("canvas print", "framed canvas"), ("Canvas Print", "Framed Canvas")),
    (("poster",), ("poster",), ("Poster",)),
    (("textile art",), ("textile art",), ("Textile Art",)),
    (("classic cap",), ("classic cap",), ("Classic Cap",)),
    (("dad hat", "dad cap"), ("dad hat", "dad cap"), ("Dad Hat", "Dad Cap")),
    (("trucker hat",), ("trucker hat",), ("Trucker Hat",)),
    (("bucket hat",), ("bucket hat",), ("Bucket Hat",)),
    (("mũ", "mu", "mũ đội", "mu doi", "mũ nón", "mu non", "nón", "non", "hat", "cap"), ("classic cap",), ("Classic Cap",)),
    (("acrylic ornament",), ("acrylic ornament",), ("Acrylic Ornament",)),
    (("glass ornament",), ("glass ornament",), ("Glass Ornament",)),
    (("wood ornament",), ("wood ornament",), ("Wood Ornament",)),
    (("aluminum ornament", "aluminium ornament"), ("aluminum ornament", "aluminium ornament"), ("Aluminum Ornament", "Aluminium Ornament")),
    (("long sleeve", "long-sleeve"), ("long sleeve", "long-sleeve"), ("Long Sleeve",)),
    (("tumbler", "acc30tgm"), ("tumbler", "acc30tgm"), ("Tumbler", "ACC30TGM")),
    (("stainless steel bottle", "steel bottle", "bottle"), ("bottle",), ("Bottle", "Stainless Steel Bottle")),
    (("tritan cup",), ("tritan cup",), ("Tritan Cup",)),
    (("doormat", "thảm chùi chân", "tham chui chan"), ("doormat",), ("Doormat",)),
    (("wall clock", "clock"), ("clock",), ("Clock", "Wall Clock")),
    (("towel", "tea towel"), ("towel",), ("Towel",)),
    (("tapestry",), ("tapestry",), ("Tapestry",)),
    (("pillow", "pillow cover", "throw pillow"), ("pillow",), ("Pillow",)),
    (("candle holder",), ("candle holder",), ("Candle Holder",)),
    (("keychain", "key chain", "móc khóa", "moc khoa"), ("keychain", "key chain"), ("Keychain", "Key Chain")),
    (("wallet insert", "wallet insert card"), ("wallet insert",), ("Wallet Insert", "Wallet Insert Card")),
    (("tote bag", "tote"), ("tote",), ("Tote Bag",)),
    (("night light",), ("night light",), ("Night Light",)),
    (("plaque", "acrylic plaque"), ("plaque",), ("Plaque",)),
    (("acrylic block",), ("acrylic block",), ("Acrylic Block",)),
    (("sneaker", "sneakers"), ("sneaker",), ("Sneaker",)),
    (("tất", "vớ", "socks", "sock", "crew socks", "crew sock"), ("crew socks",), ("Crew Socks",)),
    (("onesie", "baby onesie", "baby's onesie"), ("onesie",), ("Onesie",)),
    (("youth baseball jersey", "baseball jersey"), ("baseball jersey",), ("Baseball Jersey",)),
    (("sticker", "stickers"), ("sticker",), ("Sticker",)),
    (("mouse pad", "mousepad"), ("mouse pad", "mousepad"), ("Mouse Pad",)),
    (("phone grip",), ("phone grip",), ("Phone Grip",)),
    (("phone charm",), ("phone charm",), ("Phone Charm",)),
    (("suncatcher",), ("suncatcher",), ("Suncatcher",)),
]


def _accessory_leaf_spec(text: str):
    text_lower = (text or "").lower()
    for triggers, name_terms, phrases in ACCESSORY_LEAF_SPECS:
        if any(_contains_term(text_lower, trigger) for trigger in triggers):
            return name_terms, phrases
    return None


def _name_has_leaf_term(name: str, terms) -> bool:
    name_lower = (name or "").lower()
    return any(_contains_term(name_lower, term) for term in terms)


def _specific_product_matcher(search_text: str, product_type: str = ""):
    text = f"{search_text or ''} {product_type or ''}".lower()

    def has_any(*terms: str) -> bool:
        return any(_contains_term(text, term) for term in terms)

    leaf_spec = _accessory_leaf_spec(text)
    if leaf_spec is not None:
        name_terms, _ = leaf_spec
        return lambda p: _name_has_leaf_term(p.name or "", name_terms) or _name_has_leaf_term(p.id or "", name_terms)

    if has_any("t-shirt", "t-shirts", "tshirt", "tshirts", "áo thun", "ao thun") or (product_type or "").lower() == "t-shirts":
        return lambda p: (
            (p.category or "").lower() == "t-shirts"
            or _contains_term((p.name or "").lower(), "t-shirt")
            or _contains_term((p.name or "").lower(), "tshirt")
        )
    if has_any("polo", "pmp", "pwp", "zpbj"):
        return lambda p: "polo" in (p.name or "").lower()
    if has_any("sports bra", "bra"):
        return lambda p: "bra" in (p.name or "").lower()
    if has_any("tumbler", "acc30tgm"):
        return lambda p: "tumbler" in (p.name or "").lower() or "acc30tgm" in (p.id or "").lower()
    if has_any("tote bag", "tote"):
        return lambda p: "tote" in (p.name or "").lower() or "tote" in (p.id or "").lower()
    if has_any("keychain", "key chain", "móc khóa", "moc khoa"):
        return lambda p: "keychain" in (p.name or "").lower() or "key chain" in (p.name or "").lower()
    if has_any("tất", "vớ", "socks", "sock", "crew socks", "crew sock"):
        return lambda p: "sock" in (p.name or "").lower()
    if has_any("sticker", "stickers"):
        return lambda p: "sticker" in (p.name or "").lower()
    if has_any("doormat", "thảm chùi chân", "tham chui chan"):
        return lambda p: "doormat" in (p.name or "").lower()
    if has_any("mũ", "mu", "mũ đội", "mu doi", "nón", "non", "hat", "cap"):
        return lambda p: _contains_term((p.name or "").lower(), "hat") or _contains_term((p.name or "").lower(), "cap")
    if has_any("mouse pad", "mousepad"):
        return lambda p: "mouse pad" in (p.name or "").lower() or "mousepad" in (p.name or "").lower()
    if has_any("night light"):
        return lambda p: "night light" in (p.name or "").lower()
    if has_any("acrylic ornament"):
        return lambda p: "acrylic" in (p.name or "").lower() and "ornament" in (p.name or "").lower()
    if has_any("sherpa blanket"):
        return lambda p: "sherpa" in (p.name or "").lower() and "blanket" in (p.name or "").lower()
    if has_any("blanket", "chăn", "chan"):
        return lambda p: "blanket" in (p.name or "").lower()
    if has_any("pajama", "pajamas", "pijama", "sleepwear", "đồ ngủ", "do ngu", "quần ngủ", "quan ngu") or (product_type or "").lower() == "pajamas & sleepwear":
        return lambda p: "pajama" in (p.name or "").lower() or "sleepwear" in (p.name or "").lower()
    if has_any("sweatshirt", "crewneck", "áo nỉ", "ao ni") or (product_type or "").lower() == "sweatshirts":
        return lambda p: (
            ("sweatshirt" in (p.name or "").lower() or "crewneck" in (p.name or "").lower())
            and "hoodie" not in (p.name or "").lower()
            and "t-shirt" not in (p.name or "").lower()
            and "tank" not in (p.name or "").lower()
        )
    return None


def _direct_products_for_specific_query(session: Session, search_text: str, product_type: str = "") -> List[Product]:
    text = f"{search_text or ''} {product_type or ''}".lower()
    phrases = []
    leaf_spec = _accessory_leaf_spec(text)
    if leaf_spec is not None:
        _, phrases = leaf_spec
    elif "acc30tgm" in text:
        phrases = ["ACC30TGM", "Tumbler 30oz"]
    elif "sports bra" in text:
        phrases = ["Sports Bra"]
    elif "mouse pad" in text or "mousepad" in text:
        phrases = ["Mouse Pad"]
    elif "night light" in text:
        phrases = ["Night Light"]
    elif "acrylic ornament" in text:
        phrases = ["Acrylic Ornament"]
    elif "sherpa" in text and "blanket" in text:
        phrases = ["Sherpa Blanket"]
    elif "tote" in text:
        phrases = ["Tote Bag"]
    elif "keychain" in text or "key chain" in text:
        phrases = ["Keychain", "Key Chain"]
    elif any(_contains_term(text, term) for term in ["tất", "vớ", "socks", "sock", "crew socks", "crew sock"]):
        phrases = ["Crew Socks", "Socks"]
    elif "sticker" in text:
        phrases = ["Sticker"]
    elif "doormat" in text or "thảm chùi chân" in text or "tham chui chan" in text:
        phrases = ["Doormat"]
    elif any(_contains_term(text, term) for term in ["mũ", "mu", "mũ đội", "mu doi", "nón", "non", "hat", "cap"]):
        phrases = ["Hat", "Cap"]
    elif any(term in text for term in ["pajama", "pajamas", "pijama", "sleepwear", "đồ ngủ", "do ngu", "quần ngủ", "quan ngu"]) or (product_type or "").lower() == "pajamas & sleepwear":
        phrases = ["Pajama", "Pajamas", "Sleepwear"]
    elif "sweatshirt" in text or "crewneck" in text or (product_type or "").lower() == "sweatshirts":
        phrases = ["Sweatshirt", "Crewneck"]

    code_terms = [term for term in re.findall(r"\b[A-Z0-9]{5,}\b", (search_text or "").upper()) if any(ch.isdigit() for ch in term)]
    if not phrases and not code_terms:
        return []

    from sqlalchemy import or_
    clauses = []
    for phrase in phrases:
        clauses.append(Product.name.ilike(f"%{phrase}%"))
        clauses.append(Product.id.ilike(f"%{phrase}%"))
    for code in code_terms:
        clauses.append(Product.id.ilike(f"%{code}%"))
    products = session.exec(select(Product).where(or_(*clauses)).limit(30)).all()
    matcher = _specific_product_matcher(search_text, product_type)
    return [p for p in products if matcher is None or matcher(p)]


def _response_category_for_product(category: Optional[str], product_name: str, search_text: str, product_type: str = "") -> Optional[str]:
    category_value = category
    text = f"{product_name or ''} {search_text or ''} {product_type or ''}".lower()
    if "polo" in text:
        return "Polo Shirts"
    accessory_terms = [
        "tumbler", "tote", "keychain", "key chain", "mouse pad", "mousepad",
        "night light", "acrylic ornament", "doormat", "sticker", "suncatcher",
        "hat", "cap", "sock", "socks", "poster", "textile art", "ornament", "long sleeve",
        "bottle", "tritan cup", "clock", "towel", "tapestry", "pillow", "candle holder",
        "wallet insert", "plaque", "acrylic block", "sneaker", "canvas shoes", "onesie", "phone grip", "phone charm",
    ]
    if _accessory_leaf_spec(text) is not None or any(term in text for term in accessory_terms):
        category_value = "Accessories"
    return category_value


def _expand_search_tokens(product_type: Optional[str]) -> Optional[List[str]]:
    """
    Expand search tokens based on product type query.
    Uses priority-based PRODUCT_SEARCH_GROUPS with exclusion blacklists to prevent cross-category bleeding.

    Returns:
        List of search tokens, or None if product_type is empty/all/tất cả
    """
    keyword = (product_type or "").strip().lower()
    if keyword in ALL_PRODUCT_KEYWORDS:
        return None

    # Strip common search prefixes
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
        if keyword.startswith(prefix):
            keyword = keyword[len(prefix):].strip()
            break

    # Match query against all PRODUCT_SEARCH_GROUPS
    matched_groups = []
    for group in PRODUCT_SEARCH_GROUPS:
        matched = False
        for trigger in group["triggers"]:
            if _contains_term(keyword, trigger):
                matched = True
                break
        if matched:
            matched_groups.append(group)

    # If no groups matched, return keyword as-is
    if not matched_groups:
        return [keyword]

    # Sort matched groups by priority (lower number = higher priority)
    matched_groups.sort(key=lambda g: g["priority"])

    # Get highest-priority group
    highest_priority_group = matched_groups[0]

    leaf_spec = _accessory_leaf_spec(keyword)
    if leaf_spec is not None and highest_priority_group["priority"] >= 4:
        name_terms, _ = leaf_spec
        return list(name_terms)

    # Collect tokens from ALL matched groups
    tokens = []
    for group in matched_groups:
        tokens.extend(group["tokens"])

    # Apply exclusion blacklist from highest-priority group (EXACT match only)
    blacklist = highest_priority_group.get("exclusion_blacklist", [])
    blacklist_lower = {b.lower() for b in blacklist}

    filtered_tokens = []
    for token in tokens:
        token_lower = token.lower()
        # Only exclude if token EXACTLY matches a blacklisted term
        if token_lower not in blacklist_lower:
            filtered_tokens.append(token)

    # Remove duplicates while preserving order
    seen = set()
    unique_tokens = []
    for token in filtered_tokens:
        if token not in seen:
            seen.add(token)
            unique_tokens.append(token)

    return unique_tokens


def _diversify_results(results: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Đa dạng hóa danh sách kết quả theo xưởng sản xuất (partner_name) bằng Round Robin,
    trong đó các xưởng được ưu tiên duyệt theo giá landed_cost tốt nhất của họ tăng dần.
    Sau đó sắp xếp lại toàn bộ kết quả được chọn theo landed_cost tăng dần.
    """
    if not results:
        return []

    # Gom nhóm theo partner_name
    groups = {}
    for item in results:
        partner = item.get("partner_name") or "BurgerPrints"
        if partner not in groups:
            groups[partner] = []
        groups[partner].append(item)

    # Sắp xếp các item trong mỗi nhóm theo landed_cost tăng dần
    for partner in groups:
        groups[partner].sort(key=lambda x: x["landed_cost"])

    # Sắp xếp các partner theo landed_cost nhỏ nhất của họ tăng dần
    sorted_partners = sorted(groups.keys(), key=lambda p: groups[p][0]["landed_cost"])

    diversified = []
    max_len = max(len(lst) for lst in groups.values()) if groups else 0

    # Lấy xen kẽ theo Round Robin
    for i in range(max_len):
        for partner in sorted_partners:
            if i < len(groups[partner]):
                diversified.append(groups[partner][i])
                if len(diversified) >= limit:
                    break
        if len(diversified) >= limit:
            break

    # Sắp xếp lại danh sách kết quả cuối cùng theo landed_cost tăng dần
    diversified.sort(key=lambda x: x["landed_cost"])
    return diversified

def search_products_tool(
    product_type: str,
    country: str,
    max_base_cost: Optional[float] = None,
    max_shipping_days: Optional[int] = None,
    print_sides: str = "front",
    query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Tìm kiếm và đề xuất các biến thể phù hợp nhất.
    Có chế độ "lựa chọn thay thế gần nhất" (nearest alternative mode) nếu không có SKU nào khớp 100%.
    """
    country_code = _normalize_shipping_country(country)

    with Session(db.engine) as session:
        is_discovery_query = product_type is not None and product_type.startswith("alternative")

        if is_discovery_query:
            # 1. Dynamic Discovery: SELECT DISTINCT category FROM public.products;
            categories = [r for r in session.exec(select(Product.category).distinct()).all() if r]

            # Xác định các category cần loại trừ
            exclude_categories = []
            pt_clean = product_type.lower()

            target_exclude = ""
            if "_" in product_type:
                target_exclude = product_type.split("_", 1)[1].strip().lower()

            for cat in categories:
                cat_lower = cat.lower()
                if target_exclude and (target_exclude in cat_lower or cat_lower in target_exclude):
                    exclude_categories.append(cat)
                elif not target_exclude:
                    from app.agent.engine.intent import CATEGORY_MAP
                    synonyms = CATEGORY_MAP.get(cat, [])
                    if any(syn in pt_clean for syn in synonyms) or cat_lower in pt_clean:
                        exclude_categories.append(cat)

            filtered_categories = [cat for cat in categories if cat not in exclude_categories]
            if not filtered_categories:
                filtered_categories = categories

            # 2. Lấy tối đa 2 sản phẩm đại diện cho mỗi category
            products = []
            for cat in filtered_categories:
                cat_prods = session.exec(
                    select(Product).where(Product.category == cat).limit(2)
                ).all()
                products.extend(cat_prods)

            # Lấy thêm 2 sản phẩm đại diện từ nhóm null category
            from sqlalchemy import or_
            null_cat_prods = session.exec(
                select(Product).where(or_(Product.category == None, Product.category == '')).limit(2)
            ).all()
            products.extend(null_cat_prods)

            product_ids = [p.id for p in products]
            score_by_product_id = {pid: 1.0 for pid in product_ids}
        else:
            search_tokens = _expand_search_tokens(query or product_type)
            candidate_limit = 50 if search_tokens is None else SEARCH_PRODUCT_CANDIDATE_LIMIT
            product_matches = hybrid_search_products(session, query or product_type or "", search_tokens, limit=candidate_limit)

            product_ids = [ranked_product_id(match) for match in product_matches]
            score_by_product_id = {
                ranked_product_id(match): ranked_product_score(match)
                for match in product_matches
                if ranked_product_score(match) is not None
            }

            products = session.exec(select(Product).where(Product.id.in_(product_ids))).all() if product_ids else []
            print(f"[SEARCH-DEBUG] query='{_debug_ascii(query)}' pt='{product_type}' tokens={_debug_ascii(search_tokens)} limit={candidate_limit} matches={len(product_matches)} products={len(products)}")
            if not products:
                print(f"[SEARCH-DEBUG] EARLY EXIT: no products from hybrid_search")
                return []

            # Noun-based filtering
            pt_clean = (query or product_type or "").strip().lower()
            pants_query_words = ["quần", "quan", "pants", "shorts", "leggings", "pajamas", "pajama", "boxer briefs", "sweatpant", "bottoms"]
            shirt_query_words = ["áo", "ao", "shirt", "t-shirt", "tshirt", "tee", "hoodie", "sweatshirt", "sweater", "tank", "jersey", "onesie", "ba lỗ", "ba lo", "apparel"]
            mug_query_words = ["cốc", "coc", "mug", "mugs", "ly", "tách", "tach"]

            def _contains_word(text_value: str, word: str) -> bool:
                if not text_value or not word:
                    return False
                pattern = rf"(?<!\w){re.escape(word)}(?!\w)"
                return bool(re.search(pattern, text_value, re.UNICODE))

            has_pants_query = any(_contains_word(pt_clean, w) for w in pants_query_words)
            has_shirt_query = any(_contains_word(pt_clean, w) for w in shirt_query_words)
            has_mug_query = any(_contains_word(pt_clean, w) for w in mug_query_words)

            filtered_products = []
            if has_pants_query and not has_shirt_query and not has_mug_query:
                for p in products:
                    name_lower = (p.name or "").lower()
                    cat_lower = (p.category or "").lower()
                    is_pants = cat_lower == "bottoms" or any(w in name_lower for w in ["pants", "shorts", "leggings", "pajamas", "pajama", "boxer briefs", "sweatpant", "bottoms", "quần", "quan"])
                    is_upper = cat_lower in ["t-shirts", "hoodies", "sweatshirts", "tank tops"] or any(w in name_lower for w in ["tank top", "t-shirt", "tshirt", "hoodie", "sweatshirt", "sweater", "onesie"])
                    if is_pants and not is_upper:
                        # Xác định các tiểu loại quần trong câu query
                        is_long_pants_query = any(_contains_word(pt_clean, w) for w in ["dài", "dai", "pajama", "pajamas", "sweatpant", "sweatpants", "leggings", "legging", "long"])
                        is_shorts_query = any(_contains_word(pt_clean, w) for w in ["short", "shorts", "đùi", "dui"])
                        is_boxer_query = any(_contains_word(pt_clean, w) for w in ["lót", "lot", "sịp", "sip", "boxer", "boxers"])

                        name_has_shorts = any(w in name_lower for w in ["shorts", "short"])
                        name_has_boxer = any(w in name_lower for w in ["boxer", "briefs", "underpants"])
                        name_has_long = any(w in name_lower for w in ["long pants", "pajamas", "pajama", "sweatpant", "leggings", "legging", "long-sleeve"])

                        if is_long_pants_query:
                            if name_has_shorts or name_has_boxer:
                                continue
                            # Lọc chi tiết hơn cho quần dài cụ thể
                            has_pajama_word = any(_contains_word(pt_clean, w) for w in ["pajama", "pajamas"])
                            has_leggings_word = any(_contains_word(pt_clean, w) for w in ["leggings", "legging"])
                            has_sweatpant_word = any(_contains_word(pt_clean, w) for w in ["sweatpant", "sweatpants"])

                            name_has_pajama = any(w in name_lower for w in ["pajama", "pajamas"])
                            name_has_leggings = any(w in name_lower for w in ["leggings", "legging"])
                            name_has_sweatpant = any(w in name_lower for w in ["sweatpant", "sweatpants"])

                            if has_pajama_word and not name_has_pajama:
                                continue
                            if has_leggings_word and not name_has_leggings:
                                continue
                            if has_sweatpant_word and not name_has_sweatpant:
                                continue
                        elif is_shorts_query:
                            if name_has_long or name_has_boxer:
                                continue
                        elif is_boxer_query:
                            if name_has_long or name_has_shorts:
                                continue
                        else:
                            if name_has_boxer:
                                continue

                        filtered_products.append(p)
                products = filtered_products
            elif has_shirt_query and not has_pants_query and not has_mug_query:
                for p in products:
                    name_lower = (p.name or "").lower()
                    cat_lower = (p.category or "").lower()
                    is_shirt = cat_lower in ["t-shirts", "hoodies", "sweatshirts", "tank tops"] or any(w in name_lower for w in ["tank top", "jersey", "t-shirt", "tshirt", "tee", "hoodie", "sweatshirt", "sweater", "shirt", "onesie", "áo", "ao", "ba lỗ", "ba lo", "apparel"])
                    is_bottom = cat_lower == "bottoms" or any(w in name_lower for w in ["pants", "shorts", "leggings", "pajamas", "pajama", "boxer briefs", "sweatpant", "bottoms"])
                    is_pet_apparel = "pet" in cat_lower or any(_contains_word(name_lower, w) for w in ["pet", "dog", "cat"])
                    if is_shirt and not is_bottom and not is_pet_apparel:
                        filtered_products.append(p)
                products = filtered_products
            elif has_mug_query and not has_pants_query and not has_shirt_query:
                for p in products:
                    name_lower = (p.name or "").lower()
                    cat_lower = (p.category or "").lower()
                    is_mug = cat_lower == "mugs" or any(w in name_lower for w in ["mug", "mugs", "cốc", "coc", "ly", "tách", "tach"])
                    if is_mug:
                        filtered_products.append(p)
                products = filtered_products

            from app.services.catalog_search import filter_products_by_gender_and_age
            products = filter_products_by_gender_and_age(query or product_type, products)

            direct_products = _direct_products_for_specific_query(session, query or product_type or "", product_type or "")
            if direct_products:
                direct_ids = {p.id for p in direct_products}
                products = direct_products + [p for p in products if p.id not in direct_ids]
                product_ids = [p.id for p in products]

            matcher = _specific_product_matcher(query or product_type or "", product_type or "")
            if matcher is not None:
                matched_products = [p for p in products if matcher(p)]
                if not matched_products:
                    matched_products = direct_products
                products = matched_products

            if not products:
                return []

            product_order = {product_id: index for index, product_id in enumerate(product_ids)}
            products.sort(key=lambda product: product_order.get(product.id, len(product_order)))
            product_ids = [p.id for p in products]

        # Lấy tất cả các variant của các sản phẩm này
        variants = session.exec(select(ProductVariant).where(ProductVariant.product_id.in_(product_ids))).all()

        is_eu_market = country_code in ["DE", "FR", "EU"]
        is_au_nz_market = country_code in ["AU", "NZ"]
        is_za_market = country_code == "ZA"
        if is_eu_market:
            variants = [v for v in variants if v.location_name == "EU" or (v.shipping_cost_ww is not None and v.shipping_cost_ww > 0)]
        elif is_au_nz_market:
            local_variants = [v for v in variants if (v.location_name or "").upper() in ["AU", "NZ", "AU/NZ", "AU_NZ", "SOUTHERN HEMISPHERE"]]
            variants = local_variants or [v for v in variants if v.shipping_cost_ww is not None and v.shipping_cost_ww > 0]
        elif is_za_market:
            variants = [v for v in variants if (v.location_name or "").upper() in ["ZA", "SOUTH AFRICA", "AFRICA"] or (v.shipping_cost_ww is not None and v.shipping_cost_ww > 0)]

        all_results = []
        matched_results = []
        shipping_fee_cache = {}

        for var in variants:
            # Tính base cost dựa vào tùy chọn in
            base_cost_value = var.base_cost
            if print_sides == "both":
                second_cost = var.second_item_price or 0.0
                base_cost_value += second_cost

            # Tính thuế
            tax_rate = get_tax_rate(country_code)
            tax_fee = base_cost_value * tax_rate

            shipping_cache_key = (country_code, var.partner_name)
            if shipping_cache_key not in shipping_fee_cache:
                shipping_fee_cache[shipping_cache_key] = _shipping_fees_for_partner(session, country_code, var.partner_name)
            fees = shipping_fee_cache[shipping_cache_key]
            shipping_cost, carrier_name, del_time, api_sync_required, available_carriers = _optimized_shipping_result(
                fees,
                base_cost_value,
                tax_fee
            )
            selected_shipping = _selected_shipping_option(available_carriers)
            shipping_days = _shipping_days(del_time)

            # Tính Landed Cost = Base Cost + Shipping + Tax
            landed_cost = base_cost_value + shipping_cost + tax_fee

            prod = next((p for p in products if p.id == var.product_id), None)
            prod_name = prod.name if prod else "Product"
            prod_category = _response_category_for_product(prod.category if prod else None, prod_name, query or "", product_type or "")

            item_data = {
                "sku": var.sku,
                "product_id": var.product_id,
                "product_name": prod_name,
                "category": prod_category,
                "display_name": f"{prod_name} ({var.color} / {var.size})",
                "color": var.color,
                "size": var.size,
                "partner_name": var.partner_name or "BurgerPrints",
                "location_name": var.location_name or "US",
                "base_cost": round(var.base_cost, 2),
                "second_item_price": round(var.second_item_price or 0.0, 2),
                "shipping_fee": round(shipping_cost, 2),
                "zone_id": selected_shipping.get("zone_id"),
                "shipping_partner_name": selected_shipping.get("partner_name"),
                "first_item_fee": selected_shipping.get("first_item_fee"),
                "additional_item_fee": selected_shipping.get("additional_item_fee"),
                "total_shipping": selected_shipping.get("total_shipping"),
                "tax_fee": round(tax_fee, 2),
                "tax_rate": tax_rate,
                "landed_cost": round(landed_cost, 2),
                "delivery_time": del_time,
                "carrier": [carrier_name],
                "available_carriers": available_carriers,
                "candidate_shipping_options": available_carriers,
                "api_sync_required": api_sync_required,
                "mockup_url": var.mockup_url,
                "image_url": prod.image_url if prod else None,
                "print_sides": print_sides,
                "filter_match": "exact",
                "filter_excess": {}
            }

            score = score_by_product_id.get(var.product_id)
            if score is not None:
                item_data["rrf_score"] = score

            all_results.append(item_data)

            # Kiểm tra bộ lọc
            is_match = True
            excess = {}

            if max_base_cost is not None and base_cost_value > max_base_cost:
                is_match = False
                excess["base_cost"] = round(base_cost_value - max_base_cost, 2)

            if max_shipping_days is not None:
                if shipping_days is None:
                    is_match = False
                    excess["shipping_days"] = "api_sync_required"
                elif shipping_days > max_shipping_days:
                    is_match = False
                    excess["shipping_days"] = shipping_days - max_shipping_days

            if is_match:
                matched_results.append(item_data)
            else:
                item_data_copy = item_data.copy()
                item_data_copy["filter_match"] = "nearest_alternative"
                item_data_copy["filter_excess"] = excess
                # Ghi nhận vào danh sách thay thế
                all_results[-1] = item_data_copy

        # Keep the cheapest variant per (product_id, partner_name) combination.
        # This allows multiple factories for the same product model to coexist,
        # enabling proper multi-vendor comparison in the UI table.
        def _keep_best_variant_per_product_factory(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            best_by_product_factory = {}
            for item in items:
                pid = item["product_id"]
                partner = item.get("partner_name", "BurgerPrints")
                key = (pid, partner)
                cost = item["landed_cost"]
                if key not in best_by_product_factory or cost < best_by_product_factory[key]["landed_cost"]:
                    best_by_product_factory[key] = item

            # Sort by product_id search order (RRF score), then by partner landed_cost within same product
            ordered_pids = {pid: idx for idx, pid in enumerate(product_ids)}
            result_list = list(best_by_product_factory.values())
            result_list.sort(key=lambda x: (ordered_pids.get(x["product_id"], len(ordered_pids)), x["landed_cost"]))
            return result_list

        matched_representatives = _keep_best_variant_per_product_factory(matched_results)
        all_representatives = _keep_best_variant_per_product_factory(all_results)

        # Áp dụng đa dạng hóa xưởng sản xuất trên các đại diện sản phẩm
        diversified_matched = _diversify_results(matched_representatives, limit=10)
        diversified_all = _diversify_results(all_representatives, limit=10)

        # Chọn danh sách kết quả để trả về và đính kèm sister variants
        final_results = diversified_matched if diversified_matched else diversified_all

        # Strict category filtering: if searching for a specific product type, enforce it strictly
        # This prevents "Tank Top" or "Long-Sleeve" from appearing in T-Shirt results
        if product_type:
            pt_lower = f"{product_type or ''} {query or ''}".lower()
            print(f"[STRICT-FILTER] product_type='{product_type}' pt_lower='{pt_lower}' input_count={len(final_results)}", flush=True)
            category_filtered = []
            for item in final_results:
                item_name = (item.get("product_name") or "").lower()
                item_category = (item.get("category") or "").lower()
                dropped = False
                drop_reason = ""

                leaf_spec = _accessory_leaf_spec(pt_lower)
                if leaf_spec is not None:
                    name_terms, _ = leaf_spec
                    if not _name_has_leaf_term(item_name, name_terms):
                        dropped = True
                        drop_reason = f"no_accessory_leaf_keyword(name='{item_name}')"

                # T-Shirts: must contain exact T-Shirt evidence, not unrelated brand words like Q Tees.
                elif _contains_term(pt_lower, "t-shirt") or _contains_term(pt_lower, "tshirt") or _contains_term(pt_lower, "áo thun"):
                    if "pet" in item_category or any(_contains_term(item_name, term) for term in ["pet", "dog", "cat"]):
                        dropped = True
                        drop_reason = f"blacklist(pet_apparel name='{item_name}' cat='{item_category}')"
                    elif "tank" in item_name or "long-sleeve" in item_name:
                        dropped = True
                        drop_reason = f"blacklist(tank/long-sleeve in '{item_name}')"
                    elif not (
                        item_category == "t-shirts"
                        or _contains_term(item_name, "t-shirt")
                        or _contains_term(item_name, "tshirt")
                        or _contains_term(item_name, "áo thun")
                    ):
                        dropped = True
                        drop_reason = f"no_tshirt_keyword(name='{item_name}' cat='{item_category}')"

                # Tank Tops: must contain "tank", must NOT contain "t-shirt" (unless it's a tank-style tee)
                elif "tank" in pt_lower or "ba lỗ" in pt_lower or "áo ba lỗ" in pt_lower:
                    if "tank" not in item_name and "ba lỗ" not in item_name and "áo ba lỗ" not in item_name:
                        dropped = True
                        drop_reason = f"no_tank_keyword(name='{item_name}')"

                # Hoodies: must contain "hoodie" or "áo hoodie"
                elif "hoodie" in pt_lower or "áo hoodie" in pt_lower:
                    if "hoodie" not in item_name and "áo hoodie" not in item_name:
                        dropped = True
                        drop_reason = f"no_hoodie_keyword(name='{item_name}')"

                # Sweatshirts: must contain "sweatshirt" or "crewneck", must NOT contain "hoodie"
                elif "sweatshirt" in pt_lower or "áo nỉ" in pt_lower or "crewneck" in pt_lower:
                    if "hoodie" in item_name:
                        dropped = True
                        drop_reason = f"blacklist(hoodie in '{item_name}')"
                    elif "sweatshirt" not in item_name and "crewneck" not in item_name and "áo nỉ" not in item_name:
                        dropped = True
                        drop_reason = f"no_sweatshirt_keyword(name='{item_name}')"

                elif any(term in pt_lower for term in ["pajama", "pajamas", "pijama", "sleepwear", "đồ ngủ", "do ngu", "quần ngủ", "quan ngu"]):
                    if not ("pajama" in item_name or "sleepwear" in item_name or "pajama" in item_category or "sleepwear" in item_category):
                        dropped = True
                        drop_reason = f"no_pajama_keyword(name='{item_name}' cat='{item_category}')"

                elif any(_contains_term(pt_lower, term) for term in ["tất", "vớ", "socks", "sock", "crew socks", "crew sock"]):
                    if "sock" not in item_name:
                        dropped = True
                        drop_reason = f"no_sock_keyword(name='{item_name}')"

                elif any(_contains_term(pt_lower, term) for term in ["sticker", "stickers"]):
                    if "sticker" not in item_name:
                        dropped = True
                        drop_reason = f"no_sticker_keyword(name='{item_name}')"

                elif any(_contains_term(pt_lower, term) for term in ["doormat", "thảm chùi chân", "tham chui chan"]):
                    if "doormat" not in item_name:
                        dropped = True
                        drop_reason = f"no_doormat_keyword(name='{item_name}')"

                elif any(_contains_term(pt_lower, term) for term in ["mũ", "mu", "mũ đội", "mu doi", "nón", "non", "hat", "cap"]):
                    if not (_contains_term(item_name, "hat") or _contains_term(item_name, "cap")):
                        dropped = True
                        drop_reason = f"no_hat_cap_keyword(name='{item_name}')"

                # Polo Shirts: must contain "polo"
                elif "polo" in pt_lower or "áo polo" in pt_lower:
                    if "polo" not in item_name and "áo polo" not in item_name:
                        dropped = True
                        drop_reason = f"no_polo_keyword(name='{item_name}')"

                # Mugs: must contain "mug" or "cốc" or "ly"
                elif "mug" in pt_lower or "cốc" in pt_lower or "ly" in pt_lower:
                    if "mug" not in item_name and "cốc" not in item_name and "ly" not in item_name:
                        dropped = True
                        drop_reason = f"no_mug_keyword(name='{item_name}')"

                if dropped:
                    print(f"[STRICT-FILTER] DROPPED: {item.get('sku')} reason={drop_reason}", flush=True)
                else:
                    category_filtered.append(item)
            print(f"[STRICT-FILTER] output_count={len(category_filtered)} (dropped {len(final_results) - len(category_filtered)})", flush=True)
            final_results = category_filtered

        if max_base_cost is not None and product_type and not str(product_type).startswith("alternative"):
            if final_results and all(item.get("filter_match") == "nearest_alternative" for item in final_results):
                return []

        # Deduplicate top-level rows: remove items with identical (product_name, partner_name, base_cost).
        # This prevents different product types from bleeding together just because of price.
        # Only the first occurrence (cheapest landed_cost after diversify sort) is kept.
        seen_top_keys = set()
        deduped_final = []
        for item in final_results:
            top_key = (item.get("product_name", ""), item.get("partner_name", ""), item.get("base_cost", 0))
            if top_key in seen_top_keys:
                continue
            seen_top_keys.add(top_key)
            deduped_final.append(item)
        final_results = deduped_final

        # Thêm sister variants vào trường "variants" cho từng item trong danh sách kết quả cuối cùng
        for item in final_results:
            item_product_id = item.get("product_id")
            if not item_product_id:
                # Fallback tìm qua database
                db_var = session.exec(select(ProductVariant).where(ProductVariant.sku == item["sku"])).first()
                item_product_id = db_var.product_id if db_var else None

            if not item_product_id:
                item["variants"] = [item.copy()]
                continue

            # Truy vấn 100% sister variants của product_id đó từ database
            sister_vars_db = session.exec(
                select(ProductVariant).where(ProductVariant.product_id == item_product_id)
            ).all()

            # Lọc theo thị trường giống như ở dòng 317-323
            if is_eu_market:
                sister_vars_db = [v for v in sister_vars_db if v.location_name == "EU" or (v.shipping_cost_ww is not None and v.shipping_cost_ww > 0)]
            elif is_au_nz_market:
                local_variants = [v for v in sister_vars_db if (v.location_name or "").upper() in ["AU", "NZ", "AU/NZ", "AU_NZ", "SOUTHERN HEMISPHERE"]]
                sister_vars_db = local_variants or [v for v in sister_vars_db if v.shipping_cost_ww is not None and v.shipping_cost_ww > 0]
            elif is_za_market:
                sister_vars_db = [v for v in sister_vars_db if (v.location_name or "").upper() in ["ZA", "SOUTH AFRICA", "AFRICA"] or (v.shipping_cost_ww is not None and v.shipping_cost_ww > 0)]

            sister_variants = []
            for var in sister_vars_db:
                # Tính toán landed cost, shipping, tax cho variant này
                base_cost_value = var.base_cost
                if print_sides == "both":
                    second_cost = var.second_item_price or 0.0
                    base_cost_value += second_cost

                tax_rate = get_tax_rate(country_code)
                tax_fee = base_cost_value * tax_rate

                shipping_cache_key = (country_code, var.partner_name)
                if shipping_cache_key not in shipping_fee_cache:
                    shipping_fee_cache[shipping_cache_key] = _shipping_fees_for_partner(session, country_code, var.partner_name)
                fees = shipping_fee_cache[shipping_cache_key]
                shipping_cost, carrier_name, del_time, api_sync_required, available_carriers = _optimized_shipping_result(
                    fees,
                    base_cost_value,
                    tax_fee
                )
                selected_shipping = _selected_shipping_option(available_carriers)

                landed_cost = base_cost_value + shipping_cost + tax_fee

                sibling_data = {
                    "sku": var.sku,
                    "product_id": var.product_id,
                    "product_name": item["product_name"],
                    "display_name": f"{item['product_name']} ({var.color} / {var.size})",
                    "color": var.color,
                    "size": var.size,
                    "partner_name": var.partner_name or "BurgerPrints",
                    "location_name": var.location_name or "US",
                    "base_cost": round(var.base_cost, 2),
                    "second_item_price": round(var.second_item_price or 0.0, 2),
                    "shipping_fee": round(shipping_cost, 2),
                    "zone_id": selected_shipping.get("zone_id"),
                    "shipping_partner_name": selected_shipping.get("partner_name"),
                    "first_item_fee": selected_shipping.get("first_item_fee"),
                    "additional_item_fee": selected_shipping.get("additional_item_fee"),
                    "total_shipping": selected_shipping.get("total_shipping"),
                    "tax_fee": round(tax_fee, 2),
                    "tax_rate": tax_rate,
                    "landed_cost": round(landed_cost, 2),
                    "delivery_time": del_time,
                    "carrier": [carrier_name],
                    "available_carriers": available_carriers,
                    "candidate_shipping_options": available_carriers,
                    "api_sync_required": api_sync_required,
                    "mockup_url": var.mockup_url,
                    "image_url": item.get("image_url"),
                    "print_sides": print_sides,
                    "filter_match": "exact",
                    "filter_excess": {}
                }
                sister_variants.append(sibling_data)

            # Sắp xếp các sister variants theo landed_cost tăng dần
            sister_variants.sort(key=lambda x: x.get("landed_cost", 0))

            # Hide variants with identical factory (partner_name) + identical cost (base_cost).
            # Only display if the color/size has a distinct price from the same factory or comes from a different factory.
            seen_variants = set()  # Tracks (partner_name, base_cost)
            deduped_variants = []
            for sv in sister_variants:
                partner = sv.get("partner_name", "")
                cost = sv.get("base_cost", 0)
                # Create a strict unique key for the factory and price point
                variant_key = (partner, cost)
                if variant_key in seen_variants:
                    continue
                seen_variants.add(variant_key)
                deduped_variants.append(sv)
            item["variants"] = deduped_variants

        # Return the deduplicated final_results list (not the original diversified_* lists)
        # This ensures duplicate (partner_name, base_cost) rows are collapsed at the top level
        if diversified_matched:
            return final_results

        # Nearest Alternative Mode: no exact matches found
        # Category filtering already applied above, just return the filtered results
        logger.info("Chế độ Nearest Alternative được kích hoạt do không có kết quả khớp hoàn toàn.")
        return final_results


def compare_shipping_tool(product_type: str, country: str, print_sides: str = "front", query: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    So sánh phí vận chuyển và thời gian vận chuyển của các xưởng đến một quốc gia cụ thể.
    """
    country_code = _normalize_shipping_country(country)

    with Session(db.engine) as session:
        search_query = query or product_type
        products = []
        if search_query:
            from sqlalchemy import or_
            sku_like = f"{search_query}%"
            sku_variants = session.exec(
                select(ProductVariant).where(
                    or_(
                        ProductVariant.sku.ilike(sku_like),
                        ProductVariant.product_id.ilike(f"%{search_query}%"),
                    )
                )
            ).all()
            product_ids_from_sku = sorted({variant.product_id for variant in sku_variants})
            if product_ids_from_sku:
                products = session.exec(select(Product).where(Product.id.in_(product_ids_from_sku))).all()
        if not products:
            stmt = select(Product)
            if search_query:
                stmt = stmt.where(Product.category.ilike(f"%{search_query}%") | Product.name.ilike(f"%{search_query}%"))
            products = session.exec(stmt).all()

        # Lọc danh từ và lọc giới tính/độ tuổi tương tự như trong search_products_tool
        if search_query and products:
            pt_clean = search_query.strip().lower()
            pants_query_words = ["quần", "quan", "pants", "shorts", "leggings", "pajamas", "pajama", "boxer briefs", "sweatpant", "bottoms"]
            shirt_query_words = ["áo", "ao", "shirt", "t-shirt", "tshirt", "tee", "hoodie", "sweatshirt", "sweater", "tank", "jersey", "onesie", "ba lỗ", "ba lo", "apparel"]
            mug_query_words = ["cốc", "coc", "mug", "mugs", "ly", "tách", "tach"]

            def _contains_word(text_value: str, word: str) -> bool:
                if not text_value or not word:
                    return False
                pattern = rf"(?<!\w){re.escape(word)}(?!\w)"
                return bool(re.search(pattern, text_value, re.UNICODE))

            has_pants_query = any(_contains_word(pt_clean, w) for w in pants_query_words)
            has_shirt_query = any(_contains_word(pt_clean, w) for w in shirt_query_words)
            has_mug_query = any(_contains_word(pt_clean, w) for w in mug_query_words)

            filtered_products = []
            if has_pants_query and not has_shirt_query and not has_mug_query:
                for p in products:
                    name_lower = (p.name or "").lower()
                    cat_lower = (p.category or "").lower()
                    is_pants = cat_lower == "bottoms" or any(w in name_lower for w in ["pants", "shorts", "leggings", "pajamas", "pajama", "boxer briefs", "sweatpant", "bottoms", "quần", "quan"])
                    is_upper = cat_lower in ["t-shirts", "hoodies", "sweatshirts", "tank tops"] or any(w in name_lower for w in ["tank top", "t-shirt", "tshirt", "hoodie", "sweatshirt", "sweater", "onesie"])
                    if is_pants and not is_upper:
                        is_long_pants_query = any(_contains_word(pt_clean, w) for w in ["dài", "dai", "pajama", "pajamas", "sweatpant", "sweatpants", "leggings", "legging", "long"])
                        is_shorts_query = any(_contains_word(pt_clean, w) for w in ["short", "shorts", "đùi", "dui"])
                        is_boxer_query = any(_contains_word(pt_clean, w) for w in ["lót", "lot", "sịp", "sip", "boxer", "boxers"])

                        name_has_shorts = any(w in name_lower for w in ["shorts", "short"])
                        name_has_boxer = any(w in name_lower for w in ["boxer", "briefs", "underpants"])
                        name_has_long = any(w in name_lower for w in ["long pants", "pajamas", "pajama", "sweatpant", "leggings", "legging", "long-sleeve"])

                        if is_long_pants_query:
                            if name_has_shorts or name_has_boxer:
                                continue
                            # Lọc chi tiết hơn cho quần dài cụ thể
                            has_pajama_word = any(_contains_word(pt_clean, w) for w in ["pajama", "pajamas"])
                            has_leggings_word = any(_contains_word(pt_clean, w) for w in ["leggings", "legging"])
                            has_sweatpant_word = any(_contains_word(pt_clean, w) for w in ["sweatpant", "sweatpants"])

                            name_has_pajama = any(w in name_lower for w in ["pajama", "pajamas"])
                            name_has_leggings = any(w in name_lower for w in ["leggings", "legging"])
                            name_has_sweatpant = any(w in name_lower for w in ["sweatpant", "sweatpants"])

                            if has_pajama_word and not name_has_pajama:
                                continue
                            if has_leggings_word and not name_has_leggings:
                                continue
                            if has_sweatpant_word and not name_has_sweatpant:
                                continue
                        elif is_shorts_query:
                            if name_has_long or name_has_boxer:
                                continue
                        elif is_boxer_query:
                            if name_has_long or name_has_shorts:
                                continue
                        else:
                            if name_has_boxer:
                                continue
                        filtered_products.append(p)
                products = filtered_products
            elif has_shirt_query and not has_pants_query and not has_mug_query:
                for p in products:
                    name_lower = (p.name or "").lower()
                    cat_lower = (p.category or "").lower()
                    is_shirt = cat_lower in ["t-shirts", "hoodies", "sweatshirts", "tank tops"] or any(w in name_lower for w in ["tank top", "jersey", "t-shirt", "tshirt", "tee", "hoodie", "sweatshirt", "sweater", "shirt", "onesie", "áo", "ao", "ba lỗ", "ba lo", "apparel"])
                    is_bottom = cat_lower == "bottoms" or any(w in name_lower for w in ["pants", "shorts", "leggings", "pajamas", "pajama", "boxer briefs", "sweatpant", "bottoms"])
                    is_pet_apparel = "pet" in cat_lower or any(_contains_word(name_lower, w) for w in ["pet", "dog", "cat"])
                    if is_shirt and not is_bottom and not is_pet_apparel:
                        filtered_products.append(p)
                products = filtered_products
            elif has_mug_query and not has_pants_query and not has_shirt_query:
                for p in products:
                    name_lower = (p.name or "").lower()
                    cat_lower = (p.category or "").lower()
                    is_mug = cat_lower == "mugs" or any(w in name_lower for w in ["mug", "mugs", "cốc", "coc", "ly", "tách", "tach"])
                    if is_mug:
                        filtered_products.append(p)
                products = filtered_products

            # Áp dụng bộ lọc giới tính và độ tuổi
            from app.services.catalog_search import filter_products_by_gender_and_age
            products = filter_products_by_gender_and_age(search_query, products)

        product_ids = [p.id for p in products] if products else []
        variants = []
        if product_ids:
            variants = session.exec(select(ProductVariant).where(ProductVariant.product_id.in_(product_ids))).all()

        is_eu_market = country_code in ["DE", "FR", "EU"]
        is_au_nz_market = country_code in ["AU", "NZ"]
        is_za_market = country_code == "ZA"
        if is_eu_market:
            variants = [v for v in variants if v.location_name == "EU" or (v.shipping_cost_ww is not None and v.shipping_cost_ww > 0)]
        elif is_au_nz_market:
            local_variants = [v for v in variants if (v.location_name or "").upper() in ["AU", "NZ", "AU/NZ", "AU_NZ", "SOUTHERN HEMISPHERE"]]
            variants = local_variants or [v for v in variants if v.shipping_cost_ww is not None and v.shipping_cost_ww > 0]
        elif is_za_market:
            variants = [v for v in variants if (v.location_name or "").upper() in ["ZA", "SOUTH AFRICA", "AFRICA"] or (v.shipping_cost_ww is not None and v.shipping_cost_ww > 0)]

        # Gom nhóm theo xưởng để so sánh
        partners = {}
        for var in variants:
            partner_name = var.partner_name or "BurgerPrints"
            location_name = var.location_name or "US"

            # Tính toán base cost thực tế dựa trên số mặt in
            base_cost_value = var.base_cost
            if print_sides == "both":
                second_cost = var.second_item_price or 0.0
                base_cost_value += second_cost

            if partner_name not in partners:
                partners[partner_name] = {
                    "partner_name": partner_name,
                    "location_name": location_name,
                    "min_base_cost": base_cost_value,
                    "second_item_price": var.second_item_price,
                    "clone_price": var.clone_price,
                    "shipping_cost_us": var.shipping_cost_us,
                    "shipping_adding_us": var.shipping_adding_us,
                    "shipping_cost_ww": var.shipping_cost_ww,
                    "shipping_adding_ww": var.shipping_adding_ww,
                    "color": var.color or "Default",
                    "size": var.size or "OS",
                    "sku": var.sku
                }
            else:
                if base_cost_value < partners[partner_name]["min_base_cost"]:
                    partners[partner_name]["min_base_cost"] = base_cost_value
                    partners[partner_name]["color"] = var.color or "Default"
                    partners[partner_name]["size"] = var.size or "OS"
                    partners[partner_name]["sku"] = var.sku

        compare_results = []
        for partner_name, p_info in partners.items():
            tax_rate = get_tax_rate(country_code)
            tax_fee = p_info["min_base_cost"] * tax_rate
            fees = _shipping_fees_for_partner(session, country_code, partner_name)
            shipping_fee, carrier_name, del_time, api_sync_required, available_carriers = _optimized_shipping_result(
                fees,
                p_info["min_base_cost"],
                tax_fee
            )
            selected_shipping = _selected_shipping_option(available_carriers)
            min_landed_cost = p_info["min_base_cost"] + shipping_fee + tax_fee

            # Tìm variant tương ứng để lấy mockup_url và image_url
            var_sku = p_info["sku"]
            matching_var = next((v for v in variants if v.sku == var_sku), None)
            prod_image_url = None
            if matching_var:
                prod = next((p for p in products if p.id == matching_var.product_id), None)
                if prod:
                    prod_image_url = prod.image_url

            compare_results.append({
                "display_name": f"{product_type or 'Product'} ({p_info['color']} / {p_info['size']})",
                "partner_name": partner_name,
                "location_name": p_info["location_name"],
                "carrier": carrier_name,
                "base_cost": round(p_info["min_base_cost"], 2),
                "shipping_fee": round(shipping_fee, 2),
                "zone_id": selected_shipping.get("zone_id"),
                "shipping_partner_name": selected_shipping.get("partner_name"),
                "first_item_fee": selected_shipping.get("first_item_fee"),
                "additional_item_fee": selected_shipping.get("additional_item_fee"),
                "total_shipping": selected_shipping.get("total_shipping"),
                "second_item_price": round(p_info["second_item_price"] or 0.0, 2),
                "tax_fee": round(tax_fee, 2),
                "landed_cost": round(min_landed_cost, 2),
                "delivery_time": del_time,
                "available_carriers": available_carriers,
                "candidate_shipping_options": available_carriers,
                "api_sync_required": api_sync_required,
                "color": p_info["color"],
                "size": p_info["size"],
                "sku": p_info["sku"],
                "mockup_url": matching_var.mockup_url if matching_var else None,
                "image_url": prod_image_url
            })

        # Sắp xếp theo landed cost tăng dần
        compare_results.sort(key=lambda x: x["landed_cost"])
        return compare_results


def calculate_landed_cost_tool(
    sku: str,
    country: str,
    quantity: int = 1,
    selling_price: Optional[float] = None,
    print_sides: str = "front"
) -> Dict[str, Any]:
    """
    Tính toán landed cost chi tiết cho 1 SKU cụ thể và tính toán Margin / Profit nếu có giá bán.
    """
    country_code = _normalize_shipping_country(country)

    with Session(db.engine) as session:
        variant = session.exec(select(ProductVariant).where(ProductVariant.sku == sku)).first()
        if not variant:
            from sqlalchemy import or_
            variant = session.exec(
                select(ProductVariant)
                .where(
                    or_(
                        ProductVariant.sku.ilike(f"{sku}%"),
                        ProductVariant.product_id.ilike(f"%{sku}%"),
                    )
                )
                .order_by(ProductVariant.base_cost)
            ).first()
        if not variant:
            return {"error": f"Không tìm thấy biến thể với SKU: {sku}"}

        product = session.exec(select(Product).where(Product.id == variant.product_id)).first()
        product_name = product.name if product else "Product"

        # Tính base cost dựa vào tùy chọn in
        base_cost_value = variant.base_cost
        if print_sides == "both":
            second_cost = variant.second_item_price or 0.0
            base_cost_value += second_cost

        # Thuế
        tax_rate = get_tax_rate(country_code)
        total_base = base_cost_value * quantity
        tax_fee = total_base * tax_rate

        fees = _shipping_fees_for_partner(session, country_code, variant.partner_name)
        shipping_fee, carrier_name, delivery_time, api_sync_required, available_carriers = _optimized_shipping_result(
            fees,
            total_base,
            tax_fee,
            quantity
        )
        selected_shipping = _selected_shipping_option(available_carriers)

        # Landed cost = Total Base + Shipping + Tax
        landed_cost = total_base + shipping_fee + tax_fee

        result = {
            "sku": variant.sku,
            "product_name": product_name,
            "display_name": f"{product_name} ({variant.color} / {variant.size})",
            "color": variant.color,
            "size": variant.size,
            "partner_name": variant.partner_name or "BurgerPrints",
            "location_name": variant.location_name or "US",
            "quantity": quantity,
            "base_cost": round(variant.base_cost, 2),
            "total_base_cost": round(total_base, 2),
            "second_item_price": round(variant.second_item_price or 0.0, 2),
            "clone_price": round(variant.clone_price or 0.0, 2),
            "shipping_fee": round(shipping_fee, 2),
            "zone_id": selected_shipping.get("zone_id"),
            "shipping_partner_name": selected_shipping.get("partner_name"),
            "first_item_fee": selected_shipping.get("first_item_fee"),
            "additional_item_fee": selected_shipping.get("additional_item_fee"),
            "total_shipping": selected_shipping.get("total_shipping"),
            "tax_fee": round(tax_fee, 2),
            "tax_rate": tax_rate,
            "landed_cost": round(landed_cost, 2),
            "delivery_time": delivery_time,
            "carrier": [carrier_name],
            "available_carriers": available_carriers,
            "candidate_shipping_options": available_carriers,
            "api_sync_required": api_sync_required,
            "mockup_url": variant.mockup_url,
            "image_url": product.image_url if product else None,
            "print_sides": print_sides
        }

        # Nếu có giá bán, tính Profit và Margin
        if selling_price is not None:
            total_selling_price = selling_price * quantity
            profit = total_selling_price - landed_cost
            margin_percent = (profit / total_selling_price) * 100 if total_selling_price > 0 else 0

            result["selling_price"] = round(selling_price, 2)
            result["total_selling_price"] = round(total_selling_price, 2)
            result["profit"] = round(profit, 2)
            result["margin_percent"] = round(margin_percent, 2)

        return result


async def create_draft_order_tool(
    sku: str,
    quantity: int,
    country: str,
    full_name: str,
    address1: str,
    city: str,
    zip_code: str,
    print_sides: str = "front",
    shipping_carrier: Optional[str] = None,
    state: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    design_url_front: Optional[str] = None,
    mockup_url_front: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tạo đơn hàng nháp qua BurgerPrints API v2.0
    Các trường bắt buộc: shipping_name, shipping_address1, shipping_city, shipping_state,
    shipping_zip, shipping_country, shipping_email, shipping_phone, production_service, shipping_method, items
    """
    from app.models.order import Order
    import uuid

    client = BurgerPrintsClient()

    # Dựng cấu trúc item với design/mockup URLs
    item = {
        "catalog_sku": sku,
        "quantity": quantity,
        "print_sides": print_sides
    }
    # BurgerPrints yêu cầu design_url và mockup_url cho mỗi item
    default_design = "https://d1ud88wu9m1k4s.cloudfront.net/isp/2021/03/04/A2075_store_b7vinpbi8brtf.jpg"
    item["design_url_front"] = design_url_front or default_design
    item["mockup_url_front"] = mockup_url_front or default_design

    reference_order_id = f"REF-{sku}-{int(datetime.datetime.now().timestamp())}"

    # Dựng cấu trúc dữ liệu đơn hàng với TẤT CẢ các trường bắt buộc
    order_data = {
        "shipping_name": full_name or "Test Customer",
        "shipping_address1": address1 or "123 Main St",
        "shipping_city": city or "New York",
        "shipping_state": state or "NY",
        "shipping_zip": zip_code or "10001",
        "shipping_country": country.upper() if country else "US",
        "shipping_email": email or "test@example.com",
        "shipping_phone": phone or "0000000000",
        "reference_order_id": reference_order_id,
        "production_service": "standard",
        "shipping_method": shipping_carrier or "standard",
        "items": [item]
    }

    # Gọi API tạo đơn hàng
    result = await client.create_order(order_data)

    # Nếu tạo thành công, lưu vào database
    if result.get("success") and result.get("order_id"):
        try:
            # Tính total_amount từ landed_cost
            calc = calculate_landed_cost_tool(sku, country, quantity, print_sides=print_sides)
            total_amount = calc.get("landed_cost", 0.0) * quantity

            # Tạo Order object
            order = Order(
                id=str(uuid.uuid4()),
                burger_order_id=result["order_id"],
                reference_order_id=reference_order_id,
                sku=sku,
                customer_name=full_name or "Test Customer",
                total_amount=total_amount,
                status="created",
                created_at=datetime.datetime.utcnow()
            )

            # Lưu vào database
            with Session(db.engine) as session:
                session.add(order)
                session.commit()
                logger.info(f"Order {order.burger_order_id} saved to database")

        except Exception as e:
            logger.error(f"Failed to save order to database: {str(e)}")
            # Không raise exception vì đơn hàng đã tạo thành công trên BurgerPrints

    return result
