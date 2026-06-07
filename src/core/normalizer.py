PRODUCT_FIELDS = [
    "catalog_sku",
    "sku",
    "base_short_code",
    "price",
    "base_cost",
    "shipping_fee",
    "shipping_method",
    "size_name",
    "currency",
]


def to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def first_present(mapping, keys):
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def tax_fee(source):
    return to_float(first_present(source, ["tax_fee", "taxFee", "tax_amount", "taxAmount", "buyer_tax", "buyerTax", "tax", "sales_tax", "salesTax", "vat", "estimated_tax", "estimatedTax"]))


def tax_rate(source):
    return to_float(first_present(source, ["tax_rate", "taxRate"]))


def buyer_tax(source):
    return to_float(first_present(source, ["buyer_tax", "buyerTax"]))


def clone_price(source):
    return to_float(first_present(source, ["clone_price", "clonePrice"]))


def second_item_price(source):
    return to_float(first_present(source, ["second_item_price", "secondItemPrice", "2nd_price", "2ndPrice", "secondSidePrice", "second_side_price", "2price"]))


def addition_price(source):
    return to_float(first_present(source, ["addition_price", "additionPrice"]))


def first_media_url(source):
    for media in source.get("media") or []:
        value = media.get("url")
        if value not in (None, ""):
            return value
    return None


def first_printable_image_url(source):
    for printable in source.get("printable") or []:
        value = printable.get("imgUrl") or printable.get("img_url")
        if value not in (None, ""):
            return value
    return None


def normalize_image_links(source, inherited=None):
    links = dict(inherited or {})
    image_url = first_present(source, ["image_url", "imageUrl"]) or first_printable_image_url(source)
    mockup_url = first_present(source, ["mockup_url", "mockupUrl", "url"]) or first_media_url(source)
    design_url = first_present(source, ["design_url", "designUrl"])

    if image_url:
        links["image_url"] = image_url
    if mockup_url:
        links["mockup_url"] = mockup_url
    if design_url:
        links["design_url"] = design_url
    return links


def get_shipping_country(order):
    shipping = order.get("shipping") or {}
    address = shipping.get("address") or {}
    return address.get("country") or address.get("country_name")


def parse_sku_parts(sku):
    if not sku or "-" not in sku:
        return None, None
    parts = sku.split("-")
    if len(parts) < 3:
        return None, parts[-1] if len(parts) == 2 else None
    return parts[-2] or None, parts[-1] or None


def normalize_order_summary(order):
    return {
        "id": order.get("id"),
        "status": order.get("status"),
        "amount": to_float(order.get("amount")),
        "shipping_fee": to_float(order.get("shipping_fee")),
        "created_date": order.get("created_date"),
        "items_count": len(order.get("items") or []),
        "shipping_country": get_shipping_country(order),
    }


def normalize_sku_item(item, order=None):
    order = order or {}
    sku = item.get("catalog_sku") or item.get("sku")
    color, parsed_size = parse_sku_parts(sku)
    size = item.get("size_name") or parsed_size
    base_cost = to_float(item.get("base_cost") or item.get("price"))

    return {
        "sku": sku,
        "catalog_sku": item.get("catalog_sku") or sku,
        "base_short_code": item.get("base_short_code"),
        "size": size,
        "color": item.get("color") or color,
        "base_cost": base_cost,
        "price": to_float(item.get("price")),
        "amount": to_float(item.get("amount")),
        "sub_amount": to_float(item.get("sub_amount")),
        "clone_price": clone_price(item),
        "second_item_price": second_item_price(item),
        "addition_price": addition_price(item),
        "shipping_fee": to_float(item.get("shipping_fee")),
        "tax_fee": tax_fee(item),
        "tax_rate": tax_rate(item),
        "buyer_tax": buyer_tax(item),
        "payment_processing_fee": to_float(item.get("payment_processing_fee")),
        "currency": item.get("currency"),
        "shipping_country": get_shipping_country(order),
        "shipping_method": item.get("shipping_method") or order.get("shipping_method"),
        "order_id": order.get("id"),
        **normalize_image_links(item),
    }


def extract_sku_rows(orders):
    rows = []
    for order in orders:
        for item in order.get("items") or []:
            row = normalize_sku_item(item, order)
            if row["sku"]:
                rows.append(row)
    return rows


def normalize_order_detail(order):
    summary = normalize_order_summary(order)
    summary["shipping_method"] = order.get("shipping_method")
    summary["items"] = [normalize_sku_item(item, order) for item in order.get("items") or []]
    return summary


def normalize_product_summary(product):
    return {
        "short_code": product.get("short_code") or product.get("shortCode"),
        "name": product.get("name") or product.get("shortCodeName"),
        "display_name": product.get("display_name"),
        **normalize_image_links(product),
    }


def normalize_product_variation(variation, product=None):
    product = product or {}
    base_cost = to_float(variation.get("price"))
    image_links = normalize_image_links(variation, normalize_image_links(product))
    return {
        "source": "product_catalog",
        "short_code": product.get("short_code"),
        "product_name": product.get("name"),
        "display_name": product.get("display_name"),
        "sku": variation.get("sku"),
        "catalog_sku": variation.get("sku"),
        "base_short_code": product.get("short_code"),
        "size": variation.get("size"),
        "color": variation.get("color"),
        "color_hex": variation.get("color_hex"),
        "base_cost": base_cost,
        "price": base_cost,
        "amount": to_float(variation.get("amount")),
        "sub_amount": to_float(variation.get("sub_amount")),
        "clone_price": clone_price(variation),
        "second_item_price": second_item_price(variation),
        "addition_price": addition_price(variation),
        "shipping_fee": None,
        "tax_fee": tax_fee(variation),
        "tax_rate": tax_rate(variation),
        "buyer_tax": buyer_tax(variation),
        "payment_processing_fee": to_float(variation.get("payment_processing_fee")),
        "currency": "USD",
        "shipping_country": None,
        "shipping_method": None,
        "partner_id": variation.get("partner_id"),
        "partner_name": variation.get("partner_name"),
        "print_area": product.get("print_area") or [],
        "resolution_default": product.get("resolution_default"),
        **image_links,
    }


def extract_product_sku_rows(product):
    return [
        normalize_product_variation(variation, product)
        for variation in product.get("variations") or []
        if variation.get("sku")
    ]


def normalize_catalog_sku(base_sku, product=None):
    product = product or {}
    base_cost = to_float(base_sku.get("baseCost"))
    location_id = base_sku.get("location")
    image_links = normalize_image_links(base_sku, normalize_image_links(product))
    return {
        "source": "catalog_api",
        "short_code": base_sku.get("shortCode") or product.get("shortCode"),
        "product_name": product.get("name"),
        "display_name": product.get("displayName"),
        "sku": base_sku.get("sku"),
        "catalog_sku": base_sku.get("sku"),
        "base_short_code": base_sku.get("shortCode") or product.get("shortCode"),
        "size": base_sku.get("sizeName"),
        "color": base_sku.get("colorName"),
        "base_cost": base_cost,
        "price": base_cost,
        "amount": to_float(base_sku.get("amount")),
        "sub_amount": to_float(base_sku.get("sub_amount")),
        "clone_price": clone_price(base_sku),
        "second_item_price": second_item_price(base_sku),
        "addition_price": addition_price(base_sku),
        "shipping_cost_us": to_float(base_sku.get("shippingCostUs")),
        "shipping_adding_us": to_float(base_sku.get("shippingAddingUs")),
        "shipping_cost_ww": to_float(base_sku.get("shippingCostWW")),
        "shipping_adding_ww": to_float(base_sku.get("shippingAddingWW")),
        "shipping_fee": None,
        "tax_fee": tax_fee(base_sku),
        "tax_rate": tax_rate(base_sku),
        "buyer_tax": buyer_tax(base_sku),
        "payment_processing_fee": to_float(base_sku.get("payment_processing_fee")),
        "currency": product.get("currency") or "USD",
        "shipping_country": None,
        "shipping_method": None,
        "partner_id": location_id,
        "partner_name": base_sku.get("locationName"),
        "location_id": location_id,
        "location_name": base_sku.get("locationName"),
        **image_links,
    }


def extract_catalog_sku_rows(product):
    return [
        normalize_catalog_sku(base_sku, product)
        for base_sku in product.get("baseSku") or []
        if base_sku.get("sku")
    ]


def normalize_shipping_detail(country, detail):
    return {
        "shipping_country": country.get("countryCode"),
        "shipping_country_name": country.get("countryName"),
        "shipping_method": detail.get("method"),
        "shipping_service": detail.get("name"),
        "delivery_time": detail.get("description"),
        "carrier": detail.get("carriers"),
        "first_item_shipping": to_float(detail.get("firstItemPrice")),
        "additional_item_shipping": to_float(detail.get("additionalItemPrice")),
    }


def find_shipping_detail(shipping_payload, country_code):
    countries = shipping_payload.get("data") if isinstance(shipping_payload, dict) else shipping_payload
    countries = countries or []
    if country_code:
        for country in countries:
            if country.get("countryCode", "").upper() == country_code.upper():
                details = country.get("details") or []
                if details:
                    return normalize_shipping_detail(country, details[0])
        return None

    for country in countries:
        details = country.get("details") or []
        if details:
            return normalize_shipping_detail(country, details[0])
    return None
