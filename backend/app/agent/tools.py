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


def _shipping_fees_for_partner(session: Session, country_code: str, partner_name: Optional[str] = None) -> List[ShippingFee]:
    zone = session.exec(select(ShippingZone).where(ShippingZone.country_code == country_code)).first()
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

    return session.exec(
        select(ShippingFee).where(
            ShippingFee.zone_id == zone.id,
            ShippingFee.partner_name == None,
        )
    ).all()


def _carrier_options_from_fees(fees: List[ShippingFee], quantity: int = 1) -> List[Dict[str, Any]]:
    options = []
    for fee in fees:
        first_fee = fee.first_item_fee or 0.0
        additional_fee = fee.additional_item_fee or 0.0
        total_fee = first_fee + max(quantity - 1, 0) * additional_fee
        options.append({
            "carrier": fee.carrier,
            "fee": round(total_fee, 2),
            "sla": fee.delivery_time or SHIPPING_API_DATA_ERROR
        })
    options.sort(key=lambda option: option["fee"])
    return options


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
            "pajama", "pajamas", "đồ ngủ"
        ]
    },
    {
        "category": "Pajamas & Sleepwear",
        "priority": 3,
        "triggers": [
            "pajama", "pajamas", "sleepwear", "đồ ngủ", "do ngu",
            "satin pajama", "silk pajama", "pajama set"
        ],
        "tokens": [
            "pajama", "pajamas", "sleepwear", "đồ ngủ",
            "satin pajama", "silk pajama", "pajama set"
        ],
        "exclusion_blacklist": [
            "shorts", "basketball shorts", "hawaiian shorts",
            "t-shirt", "áo thun", "jersey", "đồ thể thao"
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
            "ornament", "ornaments", "trang trí", "trang tri", "quà tặng", "qua tang", "gift",
            "acrylic ornament", "ceramic ornament", "acrylic block", "plaque"
        ],
        "tokens": [
            "ornament", "ornaments", "trang trí", "quà tặng",
            "acrylic ornament", "ceramic ornament", "acrylic block", "plaque"
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
            "móc khóa", "moc khoa", "giày", "giay", "nón", "non", "cap", "hat"
        ],
        "tokens": [
            "accessories", "phụ kiện", "tất", "vớ", "socks",
            "sticker", "keychain", "canvas", "poster", "tumbler", "bottle",
            "doormat", "clock", "towel", "pillow", "sneaker", "shoes", "mouse pad", "suncatcher",
            "móc khóa", "giày", "nón", "cap", "hat"
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
SEARCH_PRODUCT_CANDIDATE_LIMIT = 12


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

    import re
    words = re.findall(r"\w+", keyword)

    # Match query against all PRODUCT_SEARCH_GROUPS
    matched_groups = []
    for group in PRODUCT_SEARCH_GROUPS:
        matched = False
        for trigger in group["triggers"]:
            if " " in trigger:
                if trigger in keyword:
                    matched = True
                    break
            else:
                if trigger in words:
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

    # Collect tokens from ALL matched groups
    tokens = []
    for group in matched_groups:
        tokens.extend(group["tokens"])

    # Apply exclusion blacklist from highest-priority group
    blacklist = highest_priority_group.get("exclusion_blacklist", [])
    blacklist_lower = [b.lower() for b in blacklist]

    filtered_tokens = []
    for token in tokens:
        token_lower = token.lower()
        # Check if token contains any blacklisted term
        should_exclude = False
        for blacklisted in blacklist_lower:
            if blacklisted in token_lower:
                should_exclude = True
                break
        if not should_exclude:
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
    country_code = country.strip().upper() if country else "US"

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
            if not products:
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
                    if is_shirt and not is_bottom:
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
            shipping_days = _shipping_days(del_time)

            # Tính Landed Cost = Base Cost + Shipping + Tax
            landed_cost = base_cost_value + shipping_cost + tax_fee

            prod = next((p for p in products if p.id == var.product_id), None)
            prod_name = prod.name if prod else "Product"

            item_data = {
                "sku": var.sku,
                "product_id": var.product_id,
                "product_name": prod_name,
                "display_name": f"{prod_name} ({var.color} / {var.size})",
                "color": var.color,
                "size": var.size,
                "partner_name": var.partner_name or "BurgerPrints",
                "location_name": var.location_name or "US",
                "base_cost": round(var.base_cost, 2),
                "second_item_price": round(var.second_item_price or 0.0, 2),
                "shipping_fee": round(shipping_cost, 2),
                "tax_fee": round(tax_fee, 2),
                "tax_rate": tax_rate,
                "landed_cost": round(landed_cost, 2),
                "delivery_time": del_time,
                "carrier": [carrier_name],
                "available_carriers": available_carriers,
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

        # Lọc matched_results và all_results để mỗi sản phẩm chỉ giữ lại 1 variant đại diện tốt nhất (rẻ nhất)
        def _keep_best_variant_per_product(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            best_by_product = {}
            for item in items:
                pid = item["product_id"]
                cost = item["landed_cost"]
                if pid not in best_by_product or cost < best_by_product[pid]["landed_cost"]:
                    best_by_product[pid] = item

            # Trả về danh sách được sắp xếp theo thứ tự xuất hiện ban đầu của product_id trong product_ids
            # để giữ nguyên độ khớp tìm kiếm (RRF score)
            ordered_pids = {pid: idx for idx, pid in enumerate(product_ids)}
            result_list = list(best_by_product.values())
            result_list.sort(key=lambda x: ordered_pids.get(x["product_id"], len(ordered_pids)))
            return result_list

        matched_representatives = _keep_best_variant_per_product(matched_results)
        all_representatives = _keep_best_variant_per_product(all_results)

        # Áp dụng đa dạng hóa xưởng sản xuất trên các đại diện sản phẩm
        diversified_matched = _diversify_results(matched_representatives, limit=10)
        diversified_all = _diversify_results(all_representatives, limit=10)

        # Chọn danh sách kết quả để trả về và đính kèm sister variants
        final_results = diversified_matched if diversified_matched else diversified_all

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
                    "tax_fee": round(tax_fee, 2),
                    "tax_rate": tax_rate,
                    "landed_cost": round(landed_cost, 2),
                    "delivery_time": del_time,
                    "carrier": [carrier_name],
                    "available_carriers": available_carriers,
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
            item["variants"] = sister_variants

        # Nếu có kết quả khớp 100%, trả về
        if diversified_matched:
            return diversified_matched

        # Nếu không có kết quả khớp, áp dụng Nearest Alternative Mode
        # Trả về các lựa chọn thay thế gần nhất
        logger.info("Chế độ Nearest Alternative được kích hoạt do không có kết quả khớp hoàn toàn.")
        return diversified_all


def compare_shipping_tool(product_type: str, country: str, print_sides: str = "front", query: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    So sánh phí vận chuyển và thời gian vận chuyển của các xưởng đến một quốc gia cụ thể.
    """
    country_code = country.strip().upper() if country else "US"

    with Session(db.engine) as session:
        # Lấy danh sách variants để so sánh xưởng
        stmt = select(Product)
        search_query = query or product_type
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
                    if is_shirt and not is_bottom:
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
                "second_item_price": round(p_info["second_item_price"] or 0.0, 2),
                "tax_fee": round(tax_fee, 2),
                "landed_cost": round(min_landed_cost, 2),
                "delivery_time": del_time,
                "available_carriers": available_carriers,
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
    country_code = country.strip().upper() if country else "US"

    with Session(db.engine) as session:
        # Tìm variant bằng SKU
        variant = session.exec(select(ProductVariant).where(ProductVariant.sku == sku)).first()
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
            "tax_fee": round(tax_fee, 2),
            "tax_rate": tax_rate,
            "landed_cost": round(landed_cost, 2),
            "delivery_time": delivery_time,
            "carrier": [carrier_name],
            "available_carriers": available_carriers,
            "api_sync_required": api_sync_required,
            "mockup_url": variant.mockup_url,
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
