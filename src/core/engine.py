from src.core.normalizer import (
    extract_catalog_sku_rows,
    extract_product_sku_rows,
    extract_sku_rows,
    find_shipping_detail,
    normalize_order_detail,
    normalize_order_summary,
    normalize_product_summary,
)
from src.core.text_parser import detect_intent, normalize_text
from src.services.burgerprints_client import BurgerPrintsClient
from src.services.catalog_client import CatalogApiClient
from src.services.ranking import rank_skus


CATALOG_API_NOTE = "SKU/product, supplier, shipping fee, and delivery time are retrieved from BurgerPrints Catalog API."
CATALOG_SLA_UNAVAILABLE_NOTE = "SLA API was checked, but it did not report SLA for the recommended partner(s)."
PROFIT_REQUIRES_PRICE_NOTE = "Profit/lãi ranking needs selling_price; current ranking uses fulfillment cost/delivery until a selling price is provided."
PRODUCT_CATALOG_NOTE = "SKU/product data is retrieved from BurgerPrints Product API."
PRODUCT_SHIPPING_UNAVAILABLE_NOTE = "Shipping fee and delivery time are not available in the tested Product API endpoints, so margin excludes shipping fee unless Catalog locations enrichment succeeds."
PRODUCT_SHIPPING_ENRICHED_NOTE = "Shipping fee and delivery time were enriched from BurgerPrints Catalog locations API."
PRODUCT_DELIVERY_NOTE = "Delivery time filter was requested, but the tested Product API endpoints do not return estimated delivery time."
CATALOG_DETAIL_SCAN_LIMIT = 8

_CATALOG_CACHE = {}
_PRODUCT_DETAIL_CACHE = {}
_OUT_OF_STOCK_CACHE = {}
_CATALOG_API_LIST_CACHE = {}
_CATALOG_API_DETAIL_CACHE = {}
_CATALOG_API_SHIPPING_CACHE = {}
_CATALOG_API_SLA_CACHE = {}


def cache_key(client):
    return (getattr(client, "base_url", None), hash(getattr(client, "api_key", "")))


def public_cache_key(client):
    return getattr(client, "base_url", None)


def api_meta(meta):
    return {
        "method": meta["method"],
        "path": meta["path"],
        "url": meta["url"],
        "params": meta.get("params", {}),
    }


def list_all_products(client, page_size=200):
    key = cache_key(client)
    if key in _CATALOG_CACHE:
        return _CATALOG_CACHE[key]

    products = []
    page = 1
    last_meta = None
    while True:
        data, meta = client.list_products(page=page, page_size=page_size)
        last_meta = meta
        payload = data.get("data") if isinstance(data, dict) else {}
        result = payload.get("result") or []
        products.extend(result)
        total = payload.get("total") or len(products)
        if len(products) >= total or not result:
            break
        page += 1

    _CATALOG_CACHE[key] = (products, last_meta)
    return products, last_meta


def get_cached_product(client, short_code):
    key = (cache_key(client), short_code)
    if key not in _PRODUCT_DETAIL_CACHE:
        _PRODUCT_DETAIL_CACHE[key] = client.get_product(short_code)
    return _PRODUCT_DETAIL_CACHE[key]


def list_out_of_stock_skus(client, page_size=200):
    key = cache_key(client)
    if key in _OUT_OF_STOCK_CACHE:
        return _OUT_OF_STOCK_CACHE[key]

    skus = set()
    page = 1
    while True:
        data, _ = client.list_out_of_stock(page=page, page_size=page_size)
        payload = data.get("data") if isinstance(data, dict) else {}
        result = payload.get("result") or []
        for item in result:
            skus.update(item.get("sku") or [])
        total = payload.get("total") or len(skus)
        if page * page_size >= total or not result:
            break
        page += 1

    _OUT_OF_STOCK_CACHE[key] = skus
    return skus


def find_sku_row(client, sku):
    products, meta = list_all_products(client)
    for product in products:
        short_code = product.get("short_code")
        if not short_code:
            continue
        detail, detail_meta = get_cached_product(client, short_code)
        for row in extract_product_sku_rows(detail):
            if row.get("sku", "").lower() == sku.lower():
                return row, detail, detail_meta
    return None, None, meta


def product_matches(product, text, country=None):
    short_code = product.get("short_code") or ""
    name = product.get("name") or ""
    display_name = product.get("display_name") or ""
    haystack = normalize_text(" ".join([short_code, name, display_name]))

    if country and not (short_code.upper().startswith(country.upper()) or f"({country.upper()})" in display_name.upper()):
        return False

    normalized = normalize_text(text)
    product_words = {
        "mug": ["mug"],
        "hoodie": ["hoodie"],
        "sweatshirt": ["sweatshirt"],
        "tank": ["tank"],
        "ao thun": ["shirt", "t-shirt"],
        "t-shirt": ["shirt", "t-shirt"],
        "shirt": ["shirt", "t-shirt"],
    }
    for word, keywords in product_words.items():
        if word in normalized:
            return any(keyword in haystack for keyword in keywords)

    return True


def catalog_product_matches(product, text):
    short_code = product.get("shortCode") or ""
    name = product.get("name") or ""
    display_name = product.get("displayName") or ""
    alias_name = product.get("aliasName") or ""
    haystack = normalize_text(" ".join([short_code, name, display_name, alias_name]))
    normalized = normalize_text(text)
    product_words = {
        "mug": ["mug"],
        "hoodie": ["hoodie"],
        "sweatshirt": ["sweatshirt"],
        "tank": ["tank"],
        "ao thun": ["shirt", "t-shirt"],
        "t-shirt": ["shirt", "t-shirt"],
        "shirt": ["shirt", "t-shirt"],
    }
    for word, keywords in product_words.items():
        if word in normalized:
            return any(keyword in haystack for keyword in keywords)
    return True


def list_catalog_api_products(catalog_client):
    key = public_cache_key(catalog_client)
    if key in _CATALOG_API_LIST_CACHE:
        return _CATALOG_API_LIST_CACHE[key]

    data, meta = catalog_client.list_catalogs()
    payload = data.get("data") if isinstance(data, dict) else {}
    products = []
    seen = set()
    for group_name in ["baseNews", "baseBestSellers", "baseSuggest"]:
        group = payload.get(group_name) or {}
        for product in group.get("content") or []:
            identity = product.get("aliasName") or product.get("shortCode")
            if identity and identity not in seen:
                seen.add(identity)
                products.append(product)

    _CATALOG_API_LIST_CACHE[key] = (products, meta)
    return products, meta


def get_cached_catalog_detail(catalog_client, alias_name):
    key = (public_cache_key(catalog_client), alias_name)
    if key not in _CATALOG_API_DETAIL_CACHE:
        _CATALOG_API_DETAIL_CACHE[key] = catalog_client.get_by_alias(alias_name)
    return _CATALOG_API_DETAIL_CACHE[key]


def get_cached_shipping(catalog_client, short_code, location_id):
    key = (public_cache_key(catalog_client), short_code, location_id)
    if key not in _CATALOG_API_SHIPPING_CACHE:
        _CATALOG_API_SHIPPING_CACHE[key] = catalog_client.get_shipping_locations(short_code, location_id)
    return _CATALOG_API_SHIPPING_CACHE[key]


def get_cached_sla(catalog_client, location_id):
    key = (public_cache_key(catalog_client), location_id)
    if key not in _CATALOG_API_SLA_CACHE:
        _CATALOG_API_SLA_CACHE[key] = catalog_client.get_location_sla(location_id)
    return _CATALOG_API_SLA_CACHE[key]


def first_sla_row(sla_data):
    payload = sla_data.get("data") if isinstance(sla_data, dict) else sla_data
    if isinstance(payload, list):
        return payload[0] if payload else {}
    if isinstance(payload, dict):
        return payload
    return {}


def enrich_catalog_rows_with_shipping(rows, catalog_client, country):
    enriched = []
    shipping_cache = {}
    sla_cache = {}
    for row in rows:
        location_id = row.get("location_id") or row.get("partner_id")
        short_code = row.get("short_code")
        if location_id and short_code:
            shipping_key = (short_code, location_id)
            if shipping_key not in shipping_cache:
                try:
                    shipping_data, _ = get_cached_shipping(catalog_client, short_code, location_id)
                except Exception:
                    continue
                shipping_cache[shipping_key] = shipping_data
            shipping_detail = find_shipping_detail(shipping_cache[shipping_key], country)
            if country and not shipping_detail:
                if country.upper() != "EU" or row.get("shipping_cost_ww") is None:
                    continue
                row["shipping_country"] = "EU"
                row["shipping_country_name"] = "Europe / Worldwide"
                row["shipping_service"] = "Worldwide"
            if shipping_detail:
                row.update(shipping_detail)

            if location_id not in sla_cache:
                try:
                    sla_data, _ = get_cached_sla(catalog_client, location_id)
                except Exception:
                    sla_data = {}
                sla_cache[location_id] = first_sla_row(sla_data)
            row["processing_time"] = sla_cache[location_id].get("processingTime")
            row["sla"] = sla_cache[location_id].get("sla")
        elif country:
            continue
        enriched.append(row)
    return enriched


def search_catalog_api(prompt, intent, catalog_client):
    products, meta = list_catalog_api_products(catalog_client)
    matched_products = [product for product in products if catalog_product_matches(product, prompt)]
    if not matched_products:
        matched_products = products[:CATALOG_DETAIL_SCAN_LIMIT]

    rows = []
    for product in matched_products[:CATALOG_DETAIL_SCAN_LIMIT]:
        alias_name = product.get("aliasName")
        if not alias_name:
            continue
        try:
            detail, _ = get_cached_catalog_detail(catalog_client, alias_name)
        except Exception:
            continue
        rows.extend(extract_catalog_sku_rows(detail))

    rows = enrich_catalog_rows_with_shipping(rows, catalog_client, intent.get("country"))
    quantity = intent.get("quantity", 1)
    ranked = rank_skus(
        rows,
        country=intent.get("country"),
        max_base_cost=intent.get("max_base_cost"),
        max_shipping_fee=intent.get("max_shipping_fee"),
        selling_price=intent.get("selling_price"),
        min_margin=intent.get("min_margin"),
        platform=intent.get("platform", "generic"),
        quantity=quantity,
        max_delivery_days=intent.get("max_delivery_days"),
        color=intent.get("color"),
        size=intent.get("size"),
        product_type=intent.get("product_type"),
        sort_by=intent.get("sort_by"),
    )
    notes = [CATALOG_API_NOTE]
    if intent.get("sort_by") == "profit" and intent.get("selling_price") is None:
        notes.append(PROFIT_REQUIRES_PRICE_NOTE)
    match_type = "exact" if ranked else "none"
    has_relaxable_filters = any(intent.get(key) is not None for key in ["max_base_cost", "max_shipping_fee", "max_delivery_days"])
    if not ranked and rows and has_relaxable_filters:
        alternatives = rank_skus(
            rows,
            country=intent.get("country"),
            max_base_cost=intent.get("max_base_cost"),
            max_shipping_fee=intent.get("max_shipping_fee"),
            selling_price=intent.get("selling_price"),
            min_margin=intent.get("min_margin"),
            platform=intent.get("platform", "generic"),
            quantity=quantity,
            max_delivery_days=intent.get("max_delivery_days"),
            color=intent.get("color"),
            size=intent.get("size"),
            product_type=intent.get("product_type"),
            sort_by=intent.get("sort_by"),
            nearest_alternatives=True,
        )
        if alternatives:
            ranked = alternatives
            match_type = "nearest_alternatives"
            notes.append("Không có SKU khớp hoàn toàn các filter. Danh sách dưới đây là lựa chọn gần nhất và có ghi rõ filter bị vượt.")
        else:
            notes.append("Không có SKU khớp các filter hiện tại. Thử nới giá vốn, số ngày ship hoặc bỏ bớt filter.")

    if not ranked and intent.get("product_type"):
        notes.append(f"Không có SKU khớp chính xác {intent['product_type']} trong Catalog API; không tự động chuyển sang product type khác.")

    limit = intent.get("limit", 10)
    output_items = diversify_by_partner(ranked, limit) if intent.get("compare_factories") else ranked[:limit]
    if intent.get("compare_factories") and len(output_items) > 1:
        notes.append("Kết quả so sánh đã chọn mỗi xưởng/partner một SKU tốt nhất để tránh lặp nhiều size cùng xưởng.")

    if output_items and all(item.get("sla") is None for item in output_items):
        notes.append(CATALOG_SLA_UNAVAILABLE_NOTE)

    return {
        "intent": "search_order_items",
        "api": api_meta(meta),
        "params": {key: value for key, value in intent.items() if key != "name"},
        "result": {"source": "catalog_api", "match_type": match_type, "count": len(output_items), "items": output_items},
        "notes": notes,
    }


DESTINATION_CLARIFICATION_NOTE = "Destination country is required before ranking shipping/delivery recommendations."
DESTINATION_CLARIFICATION_QUESTION = "Bạn muốn ship/fulfill tới nước nào? Ví dụ: US, CA, UK, AU, VN."


COUNTRY_REQUIRED_TERMS = [
    "ship",
    "shipping",
    "delivery",
    "giao",
    "van chuyen",
    "xuong",
    "factory",
    "supplier",
    "partner",
    "profit",
    "margin",
    "lai",
    "loi nhuan",
    "base cost",
    "gia von",
    "shipping fee",
    "phi ship",
]


COUNTRY_REQUIRED_FILTERS = [
    "max_shipping_fee",
    "max_delivery_days",
    "selling_price",
    "min_margin",
    "sort_by",
]


def get_order_client(client):
    return client or BurgerPrintsClient()


def search_needs_country_clarification(prompt, intent):
    if intent.get("name") != "search_order_items" or intent.get("country"):
        return False
    normalized = normalize_text(prompt)
    if any(term in normalized for term in COUNTRY_REQUIRED_TERMS):
        return True
    return any(intent.get(key) is not None for key in COUNTRY_REQUIRED_FILTERS)


def diversify_by_partner(items, limit):
    diversified = []
    seen = set()
    for item in items:
        partner = item.get("partner_id") or item.get("partner_name") or item.get("location_id") or item.get("location_name")
        if not partner:
            partner = item.get("sku")
        if partner in seen:
            continue
        seen.add(partner)
        diversified.append(item)
        if len(diversified) >= limit:
            break
    return diversified


def country_clarification_result(intent):
    return {
        "intent": "search_order_items",
        "api": None,
        "params": {key: value for key, value in intent.items() if key != "name"},
        "result": {
            "source": "clarification",
            "clarification_required": True,
            "missing_field": "country",
            "question": DESTINATION_CLARIFICATION_QUESTION,
        },
        "notes": [DESTINATION_CLARIFICATION_NOTE],
    }


def run_text_to_api(prompt, client=None, catalog_client=None, intent_override=None):
    intent = intent_override or detect_intent(prompt)
    name = intent["name"]

    if name == "unknown":
        return {
            "intent": name,
            "api": None,
            "params": {},
            "result": None,
            "notes": ["Không hiểu yêu cầu. Thử: 'lấy 5 order', 'xem balance', 'xem order A30558-CT-5604773', hoặc 'tìm SKU ship US'."],
        }

    if name == "tracking_unsupported":
        return {
            "intent": name,
            "api": None,
            "params": {"order_id": intent["order_id"]},
            "result": None,
            "notes": ["Tracking endpoint is not part of the verified core yet. Use order detail first or verify /order/{id}/tracking before enabling it."],
        }

    if name == "list_orders":
        client = get_order_client(client)
        data, meta = client.list_orders(page_size=intent.get("limit", 10), sandbox=True)
        orders = data.get("data") if isinstance(data, dict) else []
        return {
            "intent": name,
            "api": api_meta(meta),
            "params": {"page_size": intent.get("limit", 10), "sandbox": True},
            "result": {"total": data.get("total") if isinstance(data, dict) else None, "orders": [normalize_order_summary(order) for order in orders]},
            "notes": [],
        }

    if name == "get_order":
        client = get_order_client(client)
        order, meta = client.get_order(intent["order_id"])
        return {
            "intent": name,
            "api": api_meta(meta),
            "params": {"order_id": intent["order_id"]},
            "result": normalize_order_detail(order),
            "notes": [],
        }

    if name == "get_balance":
        client = get_order_client(client)
        data, meta = client.get_balance()
        return {
            "intent": name,
            "api": api_meta(meta),
            "params": {},
            "result": data,
            "notes": [],
        }

    if name == "get_product":
        client = get_order_client(client)
        product, meta = get_cached_product(client, intent["short_code"])
        rows = extract_product_sku_rows(product)
        summary = normalize_product_summary(product)
        return {
            "intent": name,
            "api": api_meta(meta),
            "params": {"short_code": intent["short_code"]},
            "result": {
                "source": "product_catalog",
                **summary,
                "variations_count": len(rows),
                "items": rows[:intent.get("limit", 10)],
            },
            "notes": [PRODUCT_CATALOG_NOTE],
        }

    if name == "get_sku":
        client = get_order_client(client)
        row, _, meta = find_sku_row(client, intent["sku"])
        return {
            "intent": name,
            "api": api_meta(meta),
            "params": {"sku": intent["sku"]},
            "result": {"source": "product_catalog", "item": row},
            "notes": [PRODUCT_CATALOG_NOTE] if row else ["Không tìm thấy SKU này trong BurgerPrints Product API catalog."],
        }

    if search_needs_country_clarification(prompt, intent):
        return country_clarification_result(intent)

    if name == "search_order_items":
        use_default_product_client = catalog_client is None and client is None
        if catalog_client is not None or client is None:
            try:
                catalog_result = search_catalog_api(prompt, intent, catalog_client or CatalogApiClient())
                if catalog_client is not None or catalog_result.get("result", {}).get("items") or not intent.get("product_type"):
                    return catalog_result
            except Exception:
                if client is None:
                    raise

        try:
            client = get_order_client(client)
        except RuntimeError:
            if "catalog_result" in locals():
                return catalog_result
            raise
        try:
            products, meta = list_all_products(client)
            matched_products = [product for product in products if product_matches(product, prompt, intent.get("country"))]
            if not matched_products and intent.get("product_type"):
                return {
                    "intent": name,
                    "api": api_meta(meta),
                    "params": {key: value for key, value in intent.items() if key != "name"},
                    "result": {"source": "product_catalog", "count": 0, "items": []},
                    "notes": [PRODUCT_CATALOG_NOTE, f"Không có product khớp chính xác {intent['product_type']} trong Product API; không tự động chuyển sang product type khác."],
                }
            if not matched_products:
                matched_products = products[:5]

            out_of_stock_skus = list_out_of_stock_skus(client)
            rows = []
            for product in matched_products[:5]:
                short_code = product.get("short_code")
                if not short_code:
                    continue
                detail, _ = get_cached_product(client, short_code)
                rows.extend(row for row in extract_product_sku_rows(detail) if row["sku"] not in out_of_stock_skus)
            if use_default_product_client and intent.get("country"):
                enriched_rows = enrich_catalog_rows_with_shipping(rows, CatalogApiClient(), intent.get("country"))
                if enriched_rows:
                    rows = enriched_rows

            ranked = rank_skus(
                rows,
                country=intent.get("country"),
                max_base_cost=intent.get("max_base_cost"),
                max_shipping_fee=None,
                selling_price=intent.get("selling_price"),
                min_margin=intent.get("min_margin"),
                platform=intent.get("platform", "generic"),
                quantity=intent.get("quantity", 1),
                color=intent.get("color"),
                size=intent.get("size"),
                product_type=intent.get("product_type"),
                sort_by=intent.get("sort_by"),
            )
            limit = intent.get("limit", 10)
            output_items = diversify_by_partner(ranked, limit) if intent.get("compare_factories") else ranked[:limit]
            notes = [PRODUCT_CATALOG_NOTE]
            if ranked and any(item.get("shipping_fee") is not None for item in ranked):
                notes.append(PRODUCT_SHIPPING_ENRICHED_NOTE)
            else:
                notes.append(PRODUCT_SHIPPING_UNAVAILABLE_NOTE)
            if intent.get("compare_factories") and len(output_items) > 1:
                notes.append("Kết quả so sánh đã chọn mỗi xưởng/partner một SKU tốt nhất để tránh lặp nhiều size cùng xưởng.")
            if intent.get("sort_by") == "profit" and intent.get("selling_price") is None:
                notes.append(PROFIT_REQUIRES_PRICE_NOTE)
            if intent.get("max_delivery_days") is not None:
                notes.append(PRODUCT_DELIVERY_NOTE)
            if intent.get("max_shipping_fee") is not None:
                notes.append("Shipping fee filter was requested, but the tested Product API endpoints do not return shipping fee.")
            return {
                "intent": name,
                "api": api_meta(meta),
                "params": {key: value for key, value in intent.items() if key != "name"},
                "result": {"source": "product_catalog", "count": len(output_items), "items": output_items},
                "notes": notes,
            }
        except Exception:
            data, meta = client.list_orders(page_size=intent.get("limit", 10), sandbox=True)
            orders = data.get("data") if isinstance(data, dict) else []
            rows = extract_sku_rows(orders)
            ranked = rank_skus(
                rows,
                country=intent.get("country"),
                max_base_cost=intent.get("max_base_cost"),
                max_shipping_fee=intent.get("max_shipping_fee"),
                selling_price=intent.get("selling_price"),
                min_margin=intent.get("min_margin"),
                platform=intent.get("platform", "generic"),
                quantity=intent.get("quantity", 1),
                color=intent.get("color"),
                size=intent.get("size"),
                product_type=intent.get("product_type"),
                sort_by=intent.get("sort_by"),
            )
            limit = intent.get("limit", 10)
            output_items = diversify_by_partner(ranked, limit) if intent.get("compare_factories") else ranked[:limit]
            notes = ["Product API search failed, so SKU/product search fell back to historical order items."]
            if intent.get("compare_factories") and len(output_items) > 1:
                notes.append("Kết quả so sánh đã chọn mỗi xưởng/partner một SKU tốt nhất để tránh lặp nhiều size cùng xưởng.")
            if intent.get("sort_by") == "profit" and intent.get("selling_price") is None:
                notes.append(PROFIT_REQUIRES_PRICE_NOTE)
            return {
                "intent": name,
                "api": api_meta(meta),
                "params": {key: value for key, value in intent.items() if key != "name"},
                "result": {"source": "order_items_fallback", "count": len(output_items), "items": output_items},
                "notes": notes,
            }

    return {
        "intent": name,
        "api": None,
        "params": {},
        "result": None,
        "notes": ["Intent detected but no core handler exists yet."],
    }
