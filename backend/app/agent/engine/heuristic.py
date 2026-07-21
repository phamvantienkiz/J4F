import copy
import datetime
import re
from sqlmodel import Session, select
from sqlalchemy import distinct
import app.database as db
from app.config import settings
from app.models.catalog import Product, ProductVariant, ShippingZone, ShippingFee
from app.agent.tools import (
    search_products_tool,
    compare_shipping_tool,
    calculate_landed_cost_tool,
    create_draft_order_tool,
    _expand_search_tokens,
    _specific_product_matcher,
)
from app.services.catalog_search import hybrid_search_products, ranked_product_id

ACTIVE_MARKETS = ["US", "EU", "VN", "AU", "NZ", "ZA"]
SHIPPING_SYNC_TECHNICAL_NOTE = "Hệ thống phát hiện DB thiếu dữ liệu Shipping Fee từ BurgerPrints API. Vui lòng kiểm tra hoặc kéo thêm dữ liệu từ endpoint /shipping/."


def _debug_ascii(value) -> str:
    return str(value).encode("unicode_escape").decode("ascii")


def _base_response() -> dict:
    return {
        "answer": "",
        "items": [],
        "tool_data": None,
        "is_nearest": False,
        "clarification_required": False,
        "missing_field": None,
        "question": None,
        "confirmation_required": False,
        "status": None,
        "order_id": None,
        "metadata": {},
        "margin_alert": False
    }


def _payload_has_api_sync_required(payload) -> bool:
    if isinstance(payload, dict):
        if payload.get("api_sync_required") is True:
            return True
        return any(_payload_has_api_sync_required(value) for value in payload.values())
    if isinstance(payload, list):
        return any(_payload_has_api_sync_required(item) for item in payload)
    return False


def _apply_api_sync_metadata(res: dict) -> None:
    if _payload_has_api_sync_required(res.get("items")) or _payload_has_api_sync_required(res.get("tool_data")):
        res["metadata"]["api_sync_required"] = True
        res["metadata"]["technical_note"] = SHIPPING_SYNC_TECHNICAL_NOTE


def _delivery_max_days(value) -> int | None:
    numbers = [int(match) for match in re.findall(r"\d+", str(value or ""))]
    return max(numbers) if numbers else None


def _apply_shipping_metadata(res: dict, items: list[dict]) -> None:
    if not items:
        return
    first = items[0]
    for key in ["zone_id", "carrier", "partner_name", "shipping_partner_name", "first_item_fee", "additional_item_fee", "total_shipping", "delivery_time", "candidate_shipping_options"]:
        if first.get(key) is not None:
            res["metadata"][key] = first.get(key)


def build_active_item_state(items: list[dict]) -> dict:
    if not items:
        return {}

    active_items = copy.deepcopy(items[:25])
    skus = []
    product_ids = []

    def collect(item: dict) -> None:
        sku = item.get("sku")
        product_id = item.get("product_id")
        if sku:
            skus.append(sku)
        if product_id:
            product_ids.append(product_id)
        for variant in item.get("variants") or []:
            if isinstance(variant, dict):
                collect(variant)

    for item in active_items:
        if isinstance(item, dict):
            collect(item)

    return {
        "_active_items": active_items,
        "_active_skus": list(dict.fromkeys(skus)),
        "_active_product_ids": list(dict.fromkeys(product_ids)),
    }


def public_slots(slots: dict) -> dict:
    return {key: value for key, value in slots.items() if not key.startswith("_")}


def _country_flag(code: str) -> str:
    country_code = (code or "").strip().upper()
    if len(country_code) != 2 or not country_code.isalpha():
        return ""
    return "".join(chr(127397 + ord(char)) for char in country_code)


def _country_option(code: str, name: str | None) -> dict[str, str]:
    country_code = (code or "").strip().upper()
    country_name = (name or country_code).strip()
    return {"code": country_code, "name": country_name, "flag": _country_flag(country_code)}


def _candidate_product_ids_for_shipping(session: Session, product_type: str | None, sku: str | None) -> list[str]:
    if sku:
        variants = session.exec(select(ProductVariant).where(ProductVariant.sku == sku)).all()
        return list(dict.fromkeys(variant.product_id for variant in variants if variant.product_id))

    if not product_type:
        return []

    products = session.exec(select(Product).where(Product.category == product_type).limit(100)).all()
    if not products:
        products = session.exec(select(Product).where(Product.name.ilike(f"%{product_type}%")).limit(100)).all()

    if not products:
        search_tokens = _expand_search_tokens(product_type)
        product_matches = hybrid_search_products(session, product_type, search_tokens, limit=50)
        product_ids = [ranked_product_id(match) for match in product_matches]
        products = session.exec(select(Product).where(Product.id.in_(product_ids))).all() if product_ids else []
        matcher = _specific_product_matcher(product_type, product_type)
        if matcher is not None:
            products = [product for product in products if matcher(product)]

    return list(dict.fromkeys(product.id for product in products if product.id))


def _available_shipping_countries(product_type: str | None, sku: str | None) -> list[dict[str, str]]:
    with Session(db.engine) as session:
        product_ids = _candidate_product_ids_for_shipping(session, product_type, sku)
        if not product_ids:
            return []

        query = (
            select(distinct(ShippingZone.country_code), ShippingZone.country_name)
            .select_from(ProductVariant)
            .join(ShippingFee, (ShippingFee.partner_name == ProductVariant.partner_name) | (ShippingFee.partner_name == None))
            .join(ShippingZone, ShippingZone.id == ShippingFee.zone_id)
            .where(
                ProductVariant.product_id.in_(product_ids),
                ProductVariant.partner_name != None,
                ProductVariant.sku != None,
                ProductVariant.base_cost > 0,
                ShippingFee.first_item_fee > 0,
            )
        )

        options_by_code: dict[str, dict[str, str]] = {}
        for code, name in session.exec(query).all():
            country_code = str(code or "").strip().upper()
            if country_code:
                options_by_code[country_code] = _country_option(country_code, name)
        return [options_by_code[code] for code in sorted(options_by_code)]


def _shipping_location_clarification(res: dict, product_type: str | None, sku: str | None, lang: str) -> dict:
    countries = _available_shipping_countries(product_type, sku)
    country_codes = [country["code"] for country in countries]
    country_text = ", ".join(country_codes)
    subject = product_type or sku or ("sản phẩm này" if lang == "vi" else "this product")
    if lang == "vi":
        question = f"{subject} hiện hỗ trợ giao đến: {country_text}. Bạn muốn gửi đơn hàng này đến quốc gia nào?" if country_codes else f"Hiện tại chưa có tuyến ship hợp lệ cho {subject}. Bạn có muốn đổi sản phẩm hoặc mô tả cụ thể hơn không?"
    else:
        question = f"{subject} is currently available for shipping to: {country_text}. Which destination country should I use for this order?" if country_codes else f"There are no valid shipping routes for {subject} yet. Would you like to choose a different product or be more specific?"
    res["clarification_required"] = True
    res["missing_field"] = "shipping_location"
    res["question"] = question
    res["answer"] = question
    res["items"] = []
    res["tool_data"] = {"items": [], "missing_field": "shipping_location", "available_countries": country_codes, "suggested_countries": countries}
    res["custom_payload"] = {"items": [], "suggested_countries": countries}
    res["metadata"]["available_countries"] = country_codes
    res["metadata"]["available_country_options"] = countries
    res["metadata"]["required_slots"] = ["country"]
    return res


def _global_availability_response(res: dict, product_type: str | None, sku: str | None, lang: str) -> dict:
    countries = _available_shipping_countries(product_type, sku)
    country_codes = [country["code"] for country in countries]
    country_text = ", ".join(f"{country['code']} ({country['name']})" for country in countries)
    subject = product_type or sku or ("sản phẩm này" if lang == "vi" else "this product")
    if lang == "vi":
        answer = f"Hiện tại danh mục {subject} có tuyến ship hợp lệ cho các thị trường: {country_text}. Bạn muốn chuyển sang xem thị trường nào?" if country_codes else f"Hiện tại chưa có thị trường nào có tuyến ship hợp lệ cho {subject}."
    else:
        answer = f"{subject} currently has valid shipping routes for: {country_text}. Which market would you like to view?" if country_codes else f"No markets currently have valid shipping routes for {subject}."
    res["answer"] = answer
    res["items"] = []
    res["tool_data"] = None
    res["custom_payload"] = {"items": [], "suggested_countries": countries}
    res["metadata"]["global_availability"] = True
    res["metadata"]["available_countries"] = country_codes
    res["metadata"]["available_country_options"] = countries
    res["metadata"]["country"] = None
    res["metadata"]["target_market"] = None
    return res


def _apply_margin(items: list[dict], selling_price, min_margin) -> bool:
    print(f"[MARGIN-DEBUG] _apply_margin called: {len(items)} items, selling_price={selling_price}, min_margin={min_margin}", flush=True)
    threshold = float(min_margin) if min_margin is not None else None
    if selling_price is not None:
        valid_items = []
        for item in items:
            item["selling_price"] = selling_price
            item["profit"] = round(selling_price - item["landed_cost"], 2)
            margin_percent = round((item["profit"] / selling_price) * 100, 2)
            item["margin_percent"] = margin_percent

            if "variants" in item and isinstance(item["variants"], list):
                valid_variants = []
                for var in item["variants"]:
                    var["selling_price"] = selling_price
                    var["profit"] = round(selling_price - var["landed_cost"], 2)
                    var_margin = round((var["profit"] / selling_price) * 100, 2)
                    var["margin_percent"] = var_margin
                    if threshold is None or var_margin >= threshold:
                        valid_variants.append(var)
                item["variants"] = valid_variants

            if threshold is None or margin_percent >= threshold:
                valid_items.append(item)
            else:
                print(f"[MARGIN-DEBUG] DROPPED item {item.get('sku')}: margin={margin_percent}% < {threshold}", flush=True)

        items.clear()
        items.extend(valid_items)
        items.sort(key=lambda x: x["profit"], reverse=True)
        print(f"[MARGIN-DEBUG] After selling_price margin apply: {len(valid_items)} items remain", flush=True)
        return threshold is not None and not valid_items

    if min_margin is not None and min_margin < 100:
        valid_items = []
        for item in items:
            landed_cost = item["landed_cost"]
            suggested_price = round(landed_cost / (1 - min_margin / 100), 2)
            item["selling_price"] = suggested_price
            item["profit"] = round(suggested_price - landed_cost, 2)
            margin_percent = round((item["profit"] / suggested_price) * 100, 2)
            item["margin_percent"] = margin_percent

            # Lọc sister variants
            if "variants" in item and isinstance(item["variants"], list):
                valid_variants = []
                for var in item["variants"]:
                    var_landed = var["landed_cost"]
                    var_suggested = round(var_landed / (1 - min_margin / 100), 2)
                    var["selling_price"] = var_suggested
                    var["profit"] = round(var_suggested - var_landed, 2)
                    var_margin = round((var["profit"] / var_suggested) * 100, 2)
                    var["margin_percent"] = var_margin
                    if var_margin >= threshold:
                        valid_variants.append(var)
                item["variants"] = valid_variants

            if margin_percent >= threshold:
                valid_items.append(item)

        items.clear()
        items.extend(valid_items)
        items.sort(key=lambda x: x["landed_cost"])
        return True

    items.sort(key=lambda x: x["landed_cost"])
    return False


async def execute_heuristic_flow(engine, intent: str, slots: dict, message: str, lang: str, country_code: str, history: list = None, previous_slots: dict = None) -> dict:
    product_type = slots.get("product_type")
    max_base_cost = slots.get("max_base_cost")
    max_shipping_days = slots.get("max_shipping_days")
    selling_price = slots.get("selling_price")
    min_margin = slots.get("min_margin")
    sku = slots.get("sku")
    quantity = slots.get("quantity", 1)
    shipping_address = slots.get("shipping_address")
    shipping_carrier = slots.get("shipping_carrier")
    print_sides = slots.get("print_sides", "front")

    user_messages = []
    if history:
        for msg in history:
            if msg.get("role") == "user":
                user_messages.append(msg.get("content", ""))
    if message and (not user_messages or user_messages[-1] != message):
        user_messages.append(message)

    # Cô lập lịch sử tin nhắn khi có sự chuyển đổi phân khúc sản phẩm hoặc đối tượng nhân khẩu học
    from app.agent.engine.intent import get_message_domain, get_slots_domain, get_message_demographic, get_slots_demographic, is_pure_pricing_adjustment_fn
    is_pure_adjustment = is_pure_pricing_adjustment_fn(message)

    if is_pure_adjustment:
        # Pure pricing adjustments must keep the active product context.
        combined_query = slots.get("product_type") or message
    else:
        msg_domain = get_message_domain(message)
        # CRITICAL FIX: Use previous_slots (DB snapshot) for domain switch detection
        # slots is already post-parse, so slots_domain would equal msg_domain
        previous_slots = previous_slots or {}
        slots_domain = get_slots_domain(previous_slots)
        msg_demo = get_message_demographic(message)
        slots_demo = get_slots_demographic(previous_slots)

        is_domain_switch = (msg_domain is not None and slots_domain is not None and msg_domain != slots_domain)
        is_demo_switch = (msg_demo is not None and slots_demo is not None and msg_demo != slots_demo)
        explicit_keep = any(w in message.lower() for w in ["giữ nguyên", "giu nguyen", "keep target", "keep market", "keep margin", "như cũ", "nhu cu", "giữ lại", "giu lai"])

        print(f"[HEURISTIC-DEBUG] msg_domain={msg_domain} slots_domain={slots_domain} is_domain_switch={is_domain_switch}", flush=True)
        if (is_domain_switch or is_demo_switch) and not explicit_keep:
            if history is not None:
                history.clear()
            user_messages = [message] if message else []
            # CRITICAL FIX: Use product_type for search to avoid noise words in full message
            # Full message contains budget/shipping terms that pollute search results
            combined_query = product_type if product_type else message
            print(f"[HEURISTIC-DEBUG] DOMAIN SWITCH -> combined_query='{_debug_ascii(combined_query)}'", flush=True)
        else:
            combined_query = " ".join(user_messages) if user_messages else message
            print(f"[HEURISTIC-DEBUG] NO SWITCH -> combined_query='{_debug_ascii(combined_query[:100])}'", flush=True)

    res = _base_response()
    res["metadata"] = {
        "intent": intent,
        "country": country_code,
        "target_market": slots.get("target_market"),
        "product_type": product_type,
        "print_sides": print_sides,
        "language": lang
    }

    if intent == "global_availability":
        if not product_type and not sku:
            res["clarification_required"] = True
            res["missing_field"] = "product_type"
            res["question"] = "Bạn muốn kiểm tra thị trường cho loại sản phẩm nào?" if lang == "vi" else "Which product type should I check market availability for?"
            res["answer"] = res["question"]
            res["tool_data"] = None
            return res
        return _global_availability_response(res, product_type, sku, lang)

    message_lower = (message or "").lower()
    if intent == "recommend" and "canvas" in message_lower and "style" in message_lower:
        res["clarification_required"] = True
        res["missing_field"] = "product_type"
        res["question"] = "Bạn muốn canvas theo hướng nào: tranh canvas/wall art hay giày canvas/shoes?"
        res["answer"] = res["question"]
        res["tool_data"] = {"items": [], "missing_field": "product_type"}
        res["metadata"]["ambiguity"] = "canvas_style"
        return res

    if intent == "recommend" and not product_type:
        res["clarification_required"] = True
        res["missing_field"] = "product_type"
        res["metadata"]["required_slots"] = ["product_type"]
        res["tool_data"] = {"slots": slots, "missing_field": "product_type"}
        return res

    if intent in ["recommend", "compare", "calculate_margin"] and (product_type or sku) and not country_code:
        return _shipping_location_clarification(res, product_type, sku, lang)

    if intent == "recommend":
        if not product_type:
            req_month = slots.get("month") or datetime.datetime.now().month
            with Session(db.engine) as db_sess:
                suggestions = engine.trend_service.get_seasonal_suggestions(db_sess, country_code, req_month)

            recommended_items = []
            for suggested_product_type in suggestions.product_types[:2]:
                recommended_items.extend(search_products_tool(
                    product_type=suggested_product_type,
                    country=suggestions.country,
                    max_base_cost=max_base_cost,
                    max_shipping_days=max_shipping_days,
                    print_sides=print_sides,
                    query=combined_query
                ))

            res["answer"] = f"Dưới đây là một số sản phẩm gợi ý theo mùa cho bạn tại {country_code}:" if lang == "vi" else f"Here are some seasonal product suggestions for you in {country_code}:"
            res["items"] = recommended_items
            res["tool_data"] = {
                "seasonal_context": suggestions.model_dump(),
                "items": recommended_items
            }
            res["is_nearest"] = any(item.get("filter_match") == "nearest_alternative" for item in recommended_items)
            res["margin_alert"] = _apply_margin(recommended_items, selling_price, min_margin)
            res["metadata"].update({
                "resolved_country": suggestions.country,
                "original_country": suggestions.original_country,
                "is_fallback": suggestions.is_fallback,
                "month": req_month,
                "season": suggestions.season,
                "events": suggestions.events,
                "suggested_product_types": suggestions.product_types
            })
            _apply_api_sync_metadata(res)
            return res

        import logging
        _logger = logging.getLogger("heuristic")
        # Write to file directly to bypass uvicorn logging
        with open("debug_trace.log", "a", encoding="utf-8") as f:
            f.write(f"[HEURISTIC-DEBUG] recommend: pt='{product_type}' country='{country_code}' max_cost={max_base_cost} query='{combined_query}'\n")
        _logger.warning(f"[HEURISTIC-DEBUG] recommend: pt='{product_type}' country='{country_code}' max_cost={max_base_cost} query='{_debug_ascii(combined_query)}'")
        print(f"[HEURISTIC-DEBUG] recommend: pt='{product_type}' country='{country_code}' max_cost={max_base_cost} query='{_debug_ascii(combined_query)}'", flush=True)
        items = search_products_tool(
            product_type=product_type,
            country=country_code,
            max_base_cost=max_base_cost,
            max_shipping_days=max_shipping_days,
            print_sides=print_sides,
            query=combined_query
        )
        print(f"[HEURISTIC-DEBUG] search returned {len(items)} items", flush=True)
        with open("debug_trace.log", "a", encoding="utf-8") as f:
            f.write(f"[HEURISTIC-DEBUG] search returned {len(items)} items\n")
        _logger.warning(f"[HEURISTIC-DEBUG] search returned {len(items)} items")

        if max_base_cost is not None and product_type and not str(product_type).startswith("alternative") and not items:
            baseline_items = search_products_tool(
                product_type=product_type,
                country=country_code,
                max_base_cost=None,
                max_shipping_days=max_shipping_days,
                print_sides=print_sides,
                query=product_type
            )
            base_costs = [item.get("base_cost") for item in baseline_items if item.get("base_cost") is not None]
            if base_costs:
                min_base_cost = min(base_costs)
                if lang == "vi":
                    res["answer"] = f"Xin lỗi, hiện không có {product_type} ship {country_code} có giá vốn dưới ${max_base_cost:.2f}. Giá vốn thấp nhất hiện có là ${min_base_cost:.2f}."
                else:
                    res["answer"] = f"Sorry, there are no {product_type} items shipping to {country_code} with base cost under ${max_base_cost:.2f}. The current minimum base cost is ${min_base_cost:.2f}."
                res["items"] = []
                res["tool_data"] = None
                res["is_nearest"] = False
                res["metadata"].update({
                    "max_base_cost": max_base_cost,
                    "min_available_base_cost": round(min_base_cost, 2),
                    "empty_reason": "base_cost_below_catalog_floor"
                })
                _apply_api_sync_metadata(res)
                return res

        if product_type and product_type.startswith("alternative"):
            if "_" in product_type:
                excluded_cat = product_type.split("_", 1)[1]
                res["answer"] = f"Dưới đây là danh sách các loại sản phẩm khác ngoài {excluded_cat} đang có sẵn tại {country_code}:" if lang == "vi" else f"Here is the list of diverse products other than {excluded_cat} available in {country_code}:"
            else:
                res["answer"] = f"Dưới đây là danh sách các loại sản phẩm khác nhau đang có sẵn tại {country_code}:" if lang == "vi" else f"Here is the list of diverse products available in {country_code}:"
        else:
            res["answer"] = f"Dưới đây là các sản phẩm {product_type} được đề xuất cho bạn tại {country_code}:" if lang == "vi" else f"Here are the recommended {product_type} products for you in {country_code}:"
        res["items"] = items
        res["tool_data"] = items
        res["is_nearest"] = any(item.get("filter_match") == "nearest_alternative" for item in items)
        # CRITICAL: Don't filter items by margin in nearest alternative mode
        # When no exact matches exist, show all available options regardless of margin
        if not res["is_nearest"]:
            res["margin_alert"] = _apply_margin(items, selling_price, min_margin)
        else:
            # Just attach margin metadata without filtering
            if selling_price is not None:
                for item in items:
                    item["selling_price"] = selling_price
                    item["profit"] = round(selling_price - item["landed_cost"], 2)
                    margin_percent = round((item["profit"] / selling_price) * 100, 2) if selling_price > 0 else 0
                    item["margin_percent"] = margin_percent
            res["margin_alert"] = False
        res["metadata"].update({
            "max_base_cost": max_base_cost,
            "max_shipping_days": max_shipping_days,
            "selling_price": selling_price,
            "min_margin": min_margin,
            "is_nearest": res["is_nearest"]
        })
        if max_shipping_days is not None and items:
            observed_days = [_delivery_max_days(item.get("delivery_time")) for item in items]
            observed_days = [days for days in observed_days if days is not None]
            if observed_days and not any(days <= max_shipping_days for days in observed_days):
                fastest = min(observed_days)
                res["clarification_required"] = True
                res["question"] = f"Không có tuyến ship nào cam kết trong {max_shipping_days} ngày; nhanh nhất hiện là khoảng {fastest} ngày. Bạn có muốn nới deadline hoặc đổi thị trường không?"
                res["answer"] = res["question"]
                res["metadata"]["delivery_time"] = min((item.get("delivery_time") for item in items if item.get("delivery_time")), default=None)
                res["metadata"]["sla_risk"] = True
        _apply_shipping_metadata(res, items)
        _apply_api_sync_metadata(res)
        return res

    if intent == "compare":
        compare_data = compare_shipping_tool(product_type=product_type, country=country_code, print_sides=print_sides, query=sku or combined_query)
        items = []
        for item in compare_data:
            items.append({
                "sku": item["sku"],
                "display_name": item["display_name"],
                "product_name": product_type,
                "color": item["color"],
                "size": item["size"],
                "partner_name": item["partner_name"],
                "location_name": item["location_name"],
                "base_cost": item["base_cost"],
                "shipping_fee": item["shipping_fee"],
                "zone_id": item.get("zone_id"),
                "shipping_partner_name": item.get("shipping_partner_name"),
                "first_item_fee": item.get("first_item_fee"),
                "additional_item_fee": item.get("additional_item_fee"),
                "total_shipping": item.get("total_shipping"),
                "second_item_price": item["second_item_price"],
                "tax_fee": item["tax_fee"],
                "landed_cost": item["landed_cost"],
                "delivery_time": item["delivery_time"],
                "carrier": [item["carrier"]],
                "available_carriers": item.get("available_carriers", []),
                "candidate_shipping_options": item.get("candidate_shipping_options", []),
                "api_sync_required": item.get("api_sync_required", False),
                "print_sides": print_sides
            })
        res["items"] = items
        res["tool_data"] = items
        res["margin_alert"] = _apply_margin(items, selling_price, min_margin)
        _apply_shipping_metadata(res, items)
        _apply_api_sync_metadata(res)
        return res

    if intent == "calculate_margin":
        explicit_sku_in_message = bool(sku and re.search(rf"(?<!\w){re.escape(str(sku))}(?!\w)", message or "", re.IGNORECASE))
        use_catalog_matrix = bool(product_type and not str(product_type).startswith("alternative") and (not sku or (is_pure_adjustment and not explicit_sku_in_message)))
        if use_catalog_matrix:
            active_items = slots.get("_active_items")
            if is_pure_adjustment and isinstance(active_items, list) and active_items:
                items = copy.deepcopy(active_items)
                res["metadata"].update({
                    "state_locked": True,
                    "active_product_ids": slots.get("_active_product_ids", []),
                    "active_skus": slots.get("_active_skus", []),
                })
            else:
                items = search_products_tool(
                    product_type=product_type,
                    country=country_code,
                    max_base_cost=max_base_cost,
                    max_shipping_days=max_shipping_days,
                    print_sides=print_sides,
                    query=combined_query
                )
            res["items"] = items
            res["tool_data"] = items
            res["margin_alert"] = _apply_margin(items, selling_price, min_margin)
            if res["margin_alert"] and not items:
                res["answer"] = f"Không đạt yêu cầu margin {min_margin}% cho {product_type} với giá bán ${selling_price}." if lang == "vi" else f"Cannot reach {min_margin}% margin for {product_type} at selling price ${selling_price}."
            res["metadata"].update({
                "sku": sku if explicit_sku_in_message else None,
                "active_sku": sku,
                "quantity": quantity,
                "selling_price": selling_price,
                "min_margin": min_margin
            })
            _apply_shipping_metadata(res, items)
            _apply_api_sync_metadata(res)
            return res

        if not sku:
            res["clarification_required"] = True
            res["missing_field"] = "sku"
            res["metadata"]["required_slots"] = ["sku"]
            res["tool_data"] = {"slots": slots, "missing_field": "sku"}
            return res

        calc = calculate_landed_cost_tool(
            sku=sku,
            country=country_code,
            quantity=quantity,
            selling_price=selling_price,
            print_sides=print_sides
        )
        res["tool_data"] = calc
        if "error" not in calc:
            res["items"] = [calc]
            if selling_price is None and min_margin is not None and min_margin < 100:
                suggested_price = round(calc["landed_cost"] / (1 - min_margin / 100), 2)
                calc["selling_price"] = suggested_price
                calc["total_selling_price"] = round(suggested_price * quantity, 2)
                calc["profit"] = round(calc["total_selling_price"] - calc["landed_cost"], 2)
                calc["margin_percent"] = round((calc["profit"] / calc["total_selling_price"]) * 100, 2)
                res["margin_alert"] = True
        _apply_shipping_metadata(res, res["items"])
        res["metadata"].update({
            "sku": sku,
            "quantity": quantity,
            "selling_price": selling_price,
            "min_margin": min_margin
        })
        _apply_api_sync_metadata(res)
        return res

    if intent == "create_order":
        if not sku:
            res["clarification_required"] = True
            res["missing_field"] = "sku"
            res["metadata"]["required_slots"] = ["sku"]
            res["tool_data"] = {"slots": slots, "missing_field": "sku"}
            return res

        if not shipping_address:
            res["clarification_required"] = True
            res["missing_field"] = "shipping_address"
            res["metadata"]["required_slots"] = ["shipping_address"]
            res["tool_data"] = {"slots": slots, "missing_field": "shipping_address"}
            return res

        if not slots.get("confirmed_order"):
            res["confirmation_required"] = True
            calc = calculate_landed_cost_tool(
                sku=sku,
                country=shipping_address.get("country", country_code),
                quantity=quantity,
                print_sides=print_sides
            )
            res["tool_data"] = {"order_preview": calc, "shipping_address": shipping_address}
            _apply_api_sync_metadata(res)
            slots["confirmed_order"] = True

            # Generate deterministic preview answer to prevent LLM hallucination
            if "error" in calc:
                res["answer"] = calc["error"]
            else:
                display_name = calc.get("display_name", sku)
                partner = calc.get("partner_name", "BurgerPrints")
                landed = calc.get("landed_cost", 0)
                ship_country = shipping_address.get("country", country_code)
                ship_name = shipping_address.get("full_name", "")
                ship_addr = shipping_address.get("address1", "")
                ship_city = shipping_address.get("city", "")
                ship_zip = shipping_address.get("zip_code", "")
                res["answer"] = (
                    f"Order preview confirmed. SKU {sku} ({display_name}) is available from partner {partner}.\n\n"
                    f"Landed Cost: ${landed:.2f} (quantity: {quantity}, print: {print_sides})\n"
                    f"Ship to: {ship_name}, {ship_addr}, {ship_city} {ship_zip}, {ship_country}\n\n"
                    f"Please confirm to create this sandbox order."
                )
            return res

        order_res = await create_draft_order_tool(
            sku=sku,
            quantity=quantity,
            country=shipping_address.get("country", country_code),
            full_name=shipping_address.get("full_name"),
            address1=shipping_address.get("address1"),
            city=shipping_address.get("city"),
            zip_code=shipping_address.get("zip_code"),
            print_sides=print_sides,
            shipping_carrier=shipping_carrier,
            state=shipping_address.get("state"),
            email=shipping_address.get("email"),
            phone=shipping_address.get("phone")
        )
        res["tool_data"] = order_res
        if order_res.get("success"):
            res["status"] = order_res.get("status")
            res["order_id"] = order_res.get("order_id")
            res["answer"] = f"Đơn hàng đã được tạo thành công với Order ID: {order_res.get('order_id')}."
            slots.pop("sku", None)
            slots.pop("shipping_address", None)
            slots.pop("confirmed_order", None)
        else:
            error_msg = order_res.get("error", "Unknown error")
            res["status"] = "failed"
            res["answer"] = f"Không thể tạo đơn hàng. Lỗi: {error_msg}"
            logger.error(f"Create order failed for SKU {sku}: {error_msg}")
        return res

    if intent == "get_system_metadata":
        res["tool_data"] = {
            "system_status": "active",
            "sandbox_mode": settings.burgerprints_enable_sandbox_create_order
        }
        res["metadata"].update(res["tool_data"])
        return res

    if intent == "capability_discovery":
        res["tool_data"] = {
            "active_markets": ACTIVE_MARKETS,
            "market_count": len(ACTIVE_MARKETS),
            "coverage": {
                "EU": ["DE", "FR"],
                "AU_NZ": ["AU", "NZ"]
            }
        }
        res["metadata"].update(res["tool_data"])
        return res

    if intent == "general_knowledge_conversation":
        res["tool_data"] = None
        return res

    res["tool_data"] = {"slots": slots}
    return res
