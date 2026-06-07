def money(value):
    if value is None:
        return "N/A"
    return f"${float(value):.2f}"


def percent(value):
    if value is None:
        return "N/A"
    return f"{float(value):.2f}%"


def cell(value):
    if value is None:
        return "N/A"
    return str(value).replace("|", "\\|")


def carrier_cell(value):
    if isinstance(value, list):
        return cell(", ".join(str(item) for item in value))
    return cell(value)


def image_link_lines(item):
    lines = []
    mockup_url = item.get("mockup_url")
    image_url = item.get("image_url")
    design_url = item.get("design_url")

    if mockup_url:
        lines.append(f"- Mockup/Image: {mockup_url}")
    if image_url and image_url != mockup_url:
        lines.append(f"- Image: {image_url}")
    if design_url:
        lines.append(f"- Design: {design_url}")
    return lines


def filter_excess_summary(item):
    excess = item.get("filter_excess") or {}
    parts = []
    if "base_cost" in excess:
        parts.append(f"Base cost vượt {money(excess['base_cost'].get('exceeded_by'))}")
    if "shipping_fee" in excess:
        parts.append(f"Shipping vượt {money(excess['shipping_fee'].get('exceeded_by'))}")
    if "delivery_days" in excess:
        parts.append(f"Delivery vượt {excess['delivery_days'].get('exceeded_by')} ngày")
    return "; ".join(parts)


def sku_table(items, limit=5):
    if not items:
        return "Không có SKU phù hợp trong dữ liệu hiện tại."

    if any(item.get("source") == "catalog_api" for item in items):
        display_items = items[:limit]
        has_filter_gaps = any(item.get("filter_excess") for item in display_items)
        has_margin_data = any(item.get("profit") is not None or item.get("margin_percent") is not None for item in display_items)
        header = "| SKU | Product | Color | Size | Supplier | Base cost | 2nd side | First ship | Add ship | Total ship | Total cost | Delivery | Carrier | SLA |"
        separator = "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|"
        if has_margin_data:
            header += " Profit | Gross Margin |"
            separator += "---:|---:|"
        if has_filter_gaps:
            header += " Filter gaps |"
            separator += "---|"
        rows = [header, separator]
        for item in display_items:
            row = "| {sku} | {product} | {color} | {size} | {supplier} | {base} | {second} | {first_ship} | {add_ship} | {ship} | {total} | {delivery} | {carrier} | {sla} |".format(
                sku=cell(item.get("sku")),
                product=cell(item.get("product_name") or item.get("display_name")),
                color=cell(item.get("color")),
                size=cell(item.get("size")),
                supplier=cell(item.get("partner_name") or item.get("location_name")),
                base=money(item.get("base_cost")),
                second=money(item.get("second_item_price")),
                first_ship=money(item.get("first_item_shipping")),
                add_ship=money(item.get("additional_item_shipping")),
                ship=money(item.get("shipping_fee")),
                total=money(item.get("total_cost")),
                delivery=cell(item.get("delivery_time")),
                carrier=carrier_cell(item.get("carrier")),
                sla=percent(item.get("sla")),
            )
            if has_margin_data:
                row += f" {money(item.get('profit'))} | {percent(item.get('margin_percent'))} |"
            if has_filter_gaps:
                row += f" {cell(filter_excess_summary(item))} |"
            rows.append(row)
        return "\n".join(rows)

    if any(item.get("source") == "product_catalog" for item in items):
        rows = ["| SKU | Product | Color | Size | Partner | Base price | 2nd price | Gross Margin |", "|---|---|---|---|---|---:|---:|---:|"]
        for item in items[:limit]:
            rows.append(
                "| {sku} | {product} | {color} | {size} | {partner} | {base} | {second} | {margin} |".format(
                    sku=cell(item.get("sku")),
                    product=cell(item.get("product_name") or item.get("display_name")),
                    color=cell(item.get("color")),
                    size=cell(item.get("size")),
                    partner=cell(item.get("partner_name")),
                    base=money(item.get("base_cost")),
                    second=money(item.get("second_item_price")),
                    margin=percent(item.get("margin_percent")),
                )
            )
        return "\n".join(rows)

    rows = ["| SKU | Base cost | Shipping | Total cost | Gross Margin |", "|---|---:|---:|---:|---:|"]
    for item in items[:limit]:
        rows.append(
            "| {sku} | {base} | {shipping} | {total} | {margin} |".format(
                sku=cell(item.get("sku")),
                base=money(item.get("base_cost")),
                shipping=money(item.get("shipping_fee")),
                total=money(item.get("total_cost")),
                margin=percent(item.get("margin_percent")),
            )
        )
    return "\n".join(rows)


def format_balance(result):
    return "\n".join([
        "Tôi đã kiểm tra balance BurgerPrints:",
        "",
        f"- Current balance: {money(result.get('current_balance'))}",
        f"- Fulfillment cost paid: {money(result.get('fulfillment_cost_paid'))}",
        f"- Fulfillment cost pending: {money(result.get('fulfillment_cost_pending'))}",
        f"- Pending deposit: {money(result.get('pending_deposit'))}",
    ])


def format_orders(result):
    orders = result.get("orders") or []
    if not orders:
        return "Không tìm thấy order nào trong dữ liệu hiện tại."

    lines = ["Tôi đã lấy danh sách order mới nhất:", "", "| Order ID | Status | Amount | Shipping | Items |", "|---|---|---:|---:|---:|"]
    for order in orders[:10]:
        lines.append(
            "| {id} | {status} | {amount} | {shipping} | {items} |".format(
                id=order.get("id") or "N/A",
                status=order.get("status") or "N/A",
                amount=money(order.get("amount")),
                shipping=money(order.get("shipping_fee")),
                items=order.get("items_count", 0),
            )
        )
    return "\n".join(lines)


def format_order_detail(result):
    items = result.get("items") or []
    lines = [
        f"Order {result.get('id')} có {len(items)} item fulfillment:",
        "",
        sku_table(items),
    ]
    image_lines = []
    for item in items:
        item_links = image_link_lines(item)
        if item_links:
            image_lines.append(f"- SKU {item.get('sku') or 'N/A'}:")
            image_lines.extend(f"  {line}" for line in item_links)
    if image_lines:
        lines.extend(["", "Image/design links:"] + image_lines)
    return "\n".join(lines)


def format_product_detail(result, notes):
    items = result.get("items") or []
    lines = [
        f"Product {result.get('short_code')} - {result.get('name') or 'N/A'}",
        f"- Variations/SKU count: {result.get('variations_count', 0)}",
    ]
    lines.extend(image_link_lines(result))
    lines.extend(["", sku_table(items)])
    if notes:
        lines.extend(["", "Lưu ý dữ liệu:"] + [f"- {note}" for note in notes])
    return "\n".join(lines)


def format_sku_detail(result, notes):
    item = result.get("item")
    if not item:
        return "\n".join(notes) if notes else "Không tìm thấy SKU này trong catalog hiện tại."
    lines = [
        f"Tôi tìm thấy SKU {item.get('sku')} trong BurgerPrints Product API:",
        "",
        sku_table([item]),
    ]
    item_links = image_link_lines(item)
    if item_links:
        lines.extend(["", "Image/design links:"] + item_links)
    if notes:
        lines.extend(["", "Lưu ý dữ liệu:"] + [f"- {note}" for note in notes])
    return "\n".join(lines)


def format_sku_search(result, notes):
    if result.get("clarification_required") and result.get("missing_field") == "country":
        return "\n".join([
            "Mình cần biết đơn này ship/fulfill tới nước nào để tính đúng shipping, delivery và xưởng.",
            result.get("question") or "Bạn muốn ship tới market nào? Ví dụ: US, CA, UK, AU, VN.",
        ])

    items = result.get("items") or []
    source = result.get("source")
    source_name = "BurgerPrints Catalog API" if source == "catalog_api" else "BurgerPrints Product API"
    if result.get("match_type") == "nearest_alternatives":
        heading = f"Không có SKU khớp hoàn toàn. Đây là các nearest alternatives từ {source_name}:"
    else:
        heading = f"Tôi tìm được các SKU phù hợp nhất từ {source_name}:"
    table_limit = 3 if source == "catalog_api" else 5
    lines = [heading, "", sku_table(items, limit=table_limit)]
    if len(items) > table_limit:
        lines.append(f"\nĐang hiển thị top {table_limit}/{len(items)} lựa chọn tốt nhất; bạn có thể hỏi thêm size/màu/market để lọc tiếp.")
    if items:
        best = items[0]
        details = [
            f"- SKU: {best.get('sku')}",
            f"- Product: {best.get('product_name') or best.get('display_name') or 'N/A'}",
            f"- Xưởng/partner: {best.get('partner_name') or best.get('location_name') or 'N/A'}",
            f"- Base price: {money(best.get('base_cost'))}",
            f"- 2nd side price: {money(best.get('second_item_price'))}",
        ]
        if source == "catalog_api":
            details.extend([
                f"- Shipping cho {best.get('quantity', 1)} item: {money(best.get('shipping_fee'))}",
                f"- Total fulfillment cost: {money(best.get('total_cost'))}",
                f"- Delivery time: {best.get('delivery_time') or 'N/A'}",
                f"- Carrier: {carrier_cell(best.get('carrier'))}",
                f"- SLA: {percent(best.get('sla'))}",
            ])
        alternative_reason = filter_excess_summary(best)
        if alternative_reason:
            details.append(f"- Alternative reason: {alternative_reason}")
        if best.get("profit") is not None:
            details.append(f"- Profit tạm tính: {money(best.get('profit'))}")
        if best.get("margin_percent") is not None:
            details.append(f"- Gross Profit Margin (Biên lợi nhuận gộp): {percent(best.get('margin_percent'))}")
        details.extend(image_link_lines(best))
        lines.extend(["", "Khuyến nghị:"] + details)
    if notes:
        lines.extend(["", "Lưu ý dữ liệu:"] + [f"- {note}" for note in notes])
    lines.extend(["", "Next action: bạn có thể hỏi lọc tiếp theo market, giá vốn, giá bán, margin, size hoặc màu."])
    return "\n".join(lines)
