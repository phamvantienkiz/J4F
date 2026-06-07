import re
import unicodedata

from src.services.margin import calculate_margin


def matches_country(item, country):
    if not country:
        return True
    item_country = item.get("shipping_country")
    if item_country:
        return item_country.upper() == country.upper()
    short_code = item.get("short_code") or item.get("base_short_code") or ""
    display_name = item.get("display_name") or ""
    return short_code.upper().startswith(country.upper()) or f"({country.upper()})" in display_name.upper()


def normalize_filter_value(value):
    value = str(value or "").replace("đ", "d").replace("Đ", "D")
    text = "".join(
        char for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def matches_color(item, color):
    if not color:
        return True
    return normalize_filter_value(item.get("color")) == normalize_filter_value(color)


def matches_size(item, size):
    if not size:
        return True
    return normalize_filter_value(item.get("size")) == normalize_filter_value(size)


def matches_product_type(item, product_type):
    if not product_type:
        return True
    aliases = {
        "hoodie": ["hoodie"],
        "sweatshirt": ["sweatshirt"],
        "tshirt": ["tshirt", "shirt", "tee"],
        "mug": ["mug"],
        "tanktop": ["tanktop", "tank"],
    }
    requested = normalize_filter_value(product_type)
    keywords = aliases.get(requested, [requested])
    haystack = normalize_filter_value(
        " ".join(
            str(item.get(key) or "")
            for key in ["product_name", "display_name", "name", "short_code", "base_short_code", "sku", "catalog_sku"]
        )
    )
    return any(keyword in haystack for keyword in keywords)


def delivery_days_max(value):
    if not value:
        return None
    numbers = [int(number) for number in re.findall(r"\d+", str(value))]
    return max(numbers) if numbers else None


def shipping_fee_for_quantity(item, quantity, country=None):
    quantity = max(1, int(quantity or 1))
    first = item.get("first_item_shipping")
    additional = item.get("additional_item_shipping")

    if first is None and country and country.upper() == "US":
        first = item.get("shipping_cost_us")
        additional = item.get("shipping_adding_us")
    if first is None and country and country.upper() != "US":
        first = item.get("shipping_cost_ww")
        additional = item.get("shipping_adding_ww")
    if first is None:
        return item.get("shipping_fee")

    additional = additional or 0.0
    return round(first + (quantity - 1) * additional, 2)


def sla_value(row):
    value = row.get("sla")
    return float(value) if str(value or "").replace(".", "", 1).isdigit() else 0.0


def add_filter_excess(excess, key, requested_max, actual):
    exceeded_by = round(actual - requested_max, 2)
    if exceeded_by > 0:
        excess[key] = {
            "requested_max": requested_max,
            "actual": actual,
            "exceeded_by": exceeded_by,
        }


def filter_excess_for_row(row, max_base_cost=None, max_shipping_fee=None, max_delivery_days=None):
    excess = {}
    if max_base_cost is not None:
        add_filter_excess(excess, "base_cost", max_base_cost, row["base_cost"])
    if max_shipping_fee is not None:
        add_filter_excess(excess, "shipping_fee", max_shipping_fee, row["shipping_fee"])
    if max_delivery_days is not None:
        add_filter_excess(excess, "delivery_days", max_delivery_days, row["delivery_days_max"])
    return excess


def filter_excess_score(excess):
    score = 0.0
    for detail in excess.values():
        requested = detail["requested_max"] or 1
        score += detail["exceeded_by"] / requested
    return round(score, 6)


def has_required_alternative_values(row, max_base_cost=None, max_shipping_fee=None, max_delivery_days=None):
    if max_base_cost is not None and row.get("base_cost") is None:
        return False
    if max_shipping_fee is not None and row.get("shipping_fee") is None:
        return False
    if max_delivery_days is not None and row.get("delivery_days_max") is None:
        return False
    return True


def rank_skus(items, country=None, max_base_cost=None, max_shipping_fee=None, selling_price=None, min_margin=None, platform="generic", quantity=1, max_delivery_days=None, color=None, size=None, product_type=None, sort_by=None, nearest_alternatives=False):
    ranked = []
    quantity = max(1, int(quantity or 1))
    for item in items:
        if not matches_country(item, country):
            continue
        if not matches_color(item, color):
            continue
        if not matches_size(item, size):
            continue
        if not matches_product_type(item, product_type):
            continue

        row = dict(item)
        row["quantity"] = quantity
        row["delivery_days_max"] = delivery_days_max(row.get("delivery_time"))

        shipping_fee = shipping_fee_for_quantity(row, quantity, country)
        base_cost = row.get("base_cost") or 0.0
        tax_fee = row.get("tax_fee")
        row["shipping_fee"] = shipping_fee
        row["total_cost"] = round(base_cost * quantity + (shipping_fee or 0.0) + (tax_fee or 0.0), 2)
        row["landed_cost"] = row["total_cost"]
        if tax_fee is None:
            row["tax_fee_missing"] = True

        if selling_price is not None:
            row["selling_price"] = float(selling_price)
            margin = calculate_margin(selling_price * quantity, base_cost * quantity, shipping_fee or 0.0, platform, tax_fee or 0.0)
            row.update(margin)
            if tax_fee is None:
                row["tax_fee_missing"] = True
            if shipping_fee is None:
                row["shipping_fee_missing"] = True
            if min_margin is not None and margin["margin_percent"] < min_margin * 100:
                continue

        if nearest_alternatives:
            if not has_required_alternative_values(row, max_base_cost, max_shipping_fee, max_delivery_days):
                continue
            excess = filter_excess_for_row(row, max_base_cost, max_shipping_fee, max_delivery_days)
            if not excess:
                continue
            row["filter_match"] = "nearest_alternative"
            row["filter_excess"] = excess
            row["filter_excess_score"] = filter_excess_score(excess)
            ranked.append(row)
            continue

        if max_base_cost is not None and (item.get("base_cost") is None or item["base_cost"] > max_base_cost):
            continue
        if max_delivery_days is not None and row["delivery_days_max"] is not None and row["delivery_days_max"] > max_delivery_days:
            continue
        if max_shipping_fee is not None and (shipping_fee is None or shipping_fee > max_shipping_fee):
            continue

        ranked.append(row)

    if nearest_alternatives:
        ranked.sort(key=lambda row: (
            row.get("filter_excess_score", 999999),
            len(row.get("filter_excess") or {}),
            row.get("delivery_days_max") if row.get("delivery_days_max") is not None else 999999,
            row.get("total_cost") if row.get("total_cost") is not None else 999999,
            -sla_value(row),
        ))
    elif selling_price is not None and sort_by == "profit":
        ranked.sort(key=lambda row: (row.get("profit", 0), row.get("margin_percent", 0), -row.get("total_cost", 0)), reverse=True)
    elif selling_price is not None:
        ranked.sort(key=lambda row: (row.get("margin_percent", 0), -row.get("total_cost", 0)), reverse=True)
    elif sort_by == "shipping_fee":
        ranked.sort(key=lambda row: (
            row.get("shipping_fee") if row.get("shipping_fee") is not None else 999999,
            row.get("total_cost") if row.get("total_cost") is not None else 999999,
            row.get("delivery_days_max") if row.get("delivery_days_max") is not None else 999999,
            -sla_value(row),
        ))
    else:
        ranked.sort(key=lambda row: (
            row.get("delivery_days_max") if row.get("delivery_days_max") is not None else 999999,
            row.get("total_cost") if row.get("total_cost") is not None else 999999,
            -sla_value(row),
        ))
    return ranked
