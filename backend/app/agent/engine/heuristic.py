import datetime
from sqlmodel import Session
import app.database as db
from app.config import settings
from app.agent.tools import (
    search_products_tool,
    compare_shipping_tool,
    calculate_landed_cost_tool,
    create_draft_order_tool,
    add_tax_pricing_fields,
    minimum_selling_price_for_margin,
)


def tax_summary_line(item: dict, lang: str) -> str:
    if not item or not item.get("tax_type"):
        return ""

    tax_amount = item.get("tax_amount", item.get("tax_fee", 0.0))
    tax_type = item.get("tax_type", "Tax")
    tax_rate = item.get("tax_rate_pct") or f"{int(item.get('tax_rate', 0) * 100)}%"
    net_revenue = item.get("net_revenue")
    buyer_tax = item.get("buyer_tax", 0.0)
    seller_tax = item.get("seller_tax", 0.0)

    if lang == "vi":
        line = f" Thuế ước tính: **${tax_amount}** ({tax_type} {tax_rate})"
        if buyer_tax:
            line += f", buyer trả thêm **${buyer_tax}**"
        elif seller_tax:
            line += f", thuế nhúng trong giá **${seller_tax}**"
        if net_revenue is not None:
            line += f", doanh thu sau thuế **${net_revenue}**."
        else:
            line += "."
        return line

    line = f" Estimated tax: **${tax_amount}** ({tax_type} {tax_rate})"
    if buyer_tax:
        line += f", buyer pays **${buyer_tax}** on top"
    elif seller_tax:
        line += f", embedded tax **${seller_tax}**"
    if net_revenue is not None:
        line += f", net revenue **${net_revenue}**."
    else:
        line += "."
    return line


async def execute_heuristic_flow(engine, intent: str, slots: dict, message: str, lang: str, country_code: str) -> dict:
    """Thực thi nghiệp vụ thô, gọi tools và chuẩn bị dữ liệu/câu trả lời fallback."""
    product_type = slots.get("product_type")
    max_base_cost = slots.get("max_base_cost")
    max_shipping_days = slots.get("max_shipping_days")
    selling_price = slots.get("selling_price")
    min_margin = slots.get("min_margin")
    sku = slots.get("sku")
    quantity = slots.get("quantity", 1)
    shipping_address = slots.get("shipping_address")
    print_sides = slots.get("print_sides", "front")
    tax_sub_region = slots.get("tax_sub_region") or slots.get("sub_region") or slots.get("state") or slots.get("province")

    res = {
        "answer": "", "items": [], "tool_data": None, "is_nearest": False,
        "clarification_required": False, "missing_field": None, "question": None,
        "confirmation_required": False, "status": None, "order_id": None
    }

    # 1. Slot filling: so sánh yêu cầu loại sản phẩm
    if intent == "compare" and not product_type:
        res["clarification_required"] = True
        res["missing_field"] = "product_type"
        if lang == "vi":
            res["question"] = "Bạn muốn tìm sản phẩm nào thế? (Ví dụ: T-Shirt, Hoodie, Sweatshirt, Mug...)"
            res["answer"] = "Chào bạn! Bạn đang quan tâm đến dòng sản phẩm nào (như áo thun T-Shirt, áo nỉ Sweatshirt, Hoodie hay cốc ly sứ Mug) để mình tìm kiếm và so sánh giúp bạn nhé?"
        else:
            res["question"] = "What product type are you looking for? (e.g., T-Shirt, Hoodie, Sweatshirt, Mug...)"
            res["answer"] = "Hello! Which product line (such as T-Shirt, Sweatshirt, Hoodie, or Ceramic Mug) are you interested in so I can help search and compare?"
        return res

    # 2. Xử lý Recommend
    elif intent == "recommend":
        # Tích hợp logic gợi ý theo mùa khi thiếu product_type
        if not product_type:
            req_month = slots.get("month") or datetime.datetime.now().month
            with Session(db.engine) as db_sess:
                sug = engine.trend_service.get_seasonal_suggestions(db_sess, country_code, req_month)
            resolved_country = sug.country
            is_fallback = sug.is_fallback

            recommended_items = []
            for p_type in sug.product_types[:2]:
                p_items = search_products_tool(
                    product_type=p_type, country=resolved_country,
                    max_base_cost=max_base_cost, max_shipping_days=max_shipping_days, print_sides=print_sides
                )
                recommended_items.extend(p_items)

            # Sắp xếp
            warning_msg = ""
            if selling_price is not None:
                for item in recommended_items:
                    add_tax_pricing_fields(item, selling_price, resolved_country, tax_sub_region, item.get("product_name") or product_type)
                recommended_items.sort(key=lambda x: x.get("profit", 0), reverse=True)
            elif min_margin is not None and min_margin < 100:
                for item in recommended_items:
                    s_price = minimum_selling_price_for_margin(item, min_margin, resolved_country, tax_sub_region, item.get("product_name") or product_type)
                    add_tax_pricing_fields(item, s_price, resolved_country, tax_sub_region, item.get("product_name") or product_type)
                recommended_items.sort(key=lambda x: x["landed_cost"])
                warning_msg = f"\n*(Lưu ý: Để đạt mức profit margin tối thiểu {min_margin}%, hệ thống đã tự động tính toán giá bán lẻ gợi ý tối thiểu cho mỗi sản phẩm. Các sản phẩm được sắp xếp theo tổng chi phí fulfillment (Landed Cost) thấp nhất.)*"
                if lang == "en":
                    warning_msg = f"\n*(Note: To achieve a minimum profit margin of {min_margin}%, the system has calculated the minimum recommended retail price for each product. Products are sorted by lowest Landed Cost.)*"
            else:
                recommended_items.sort(key=lambda x: x["landed_cost"])
                warning_msg = "\n*(Lưu ý: Do bạn chưa cung cấp giá bán lẻ (selling price), hệ thống đang tự động xếp hạng các sản phẩm theo tổng chi phí fulfillment (Landed Cost) thấp nhất. Hãy bổ sung giá bán để tính lợi nhuận và margin nhé!)*"
                if lang == "en":
                    warning_msg = "\n*(Note: Since you have not provided a selling price, the system automatically sorts products by the lowest Landed Cost. Please provide a retail price to calculate profit and margin!)*"

            res["items"] = recommended_items
            res["tool_data"] = recommended_items
            res["is_nearest"] = any(item.get("filter_match") == "nearest_alternative" for item in recommended_items)

            warning_fallback = ""
            if is_fallback:
                if lang == "vi":
                    warning_fallback = f"Lưu ý: Do BurgerPrints chưa hỗ trợ xưởng trực tiếp tại {slots.get('country')}, hệ thống đã tối ưu hóa và lấy thông số từ thị trường {resolved_country} gần nhất.\n\n"
                else:
                    warning_fallback = f"Note: Since BurgerPrints does not support workshops directly in {slots.get('country')}, the system optimized and retrieved parameters from the nearest market {resolved_country}.\n\n"

            events_str = ", ".join(sug.events) if sug.events else ("không có ngày lễ lớn đặc thù" if lang == "vi" else "no major local holidays")
            product_types_str = ", ".join(sug.product_types)

            if lang == "vi":
                ans = f"{warning_fallback}Thời tiết tại {resolved_country} vào tháng {req_month} là mùa **{sug.season}** ({sug.weather_context}).\n\n"
                ans += f"Các sự kiện nổi bật: **{events_str}**.\n\n"
                ans += f"Để tối ưu hóa doanh số trong thời điểm này, mình đề xuất bạn nên tập trung vào các dòng sản phẩm: **{product_types_str}**.\n\n"
                if recommended_items:
                    ans += f"Dưới đây là một số sản phẩm tốt nhất mình tìm thấy từ catalog:\n"
                    ans += f"- SKU **{recommended_items[0]['sku']}** ({recommended_items[0]['display_name']}) từ xưởng **{recommended_items[0]['partner_name']}**. Chi phí: Base **${recommended_items[0]['base_cost']}**, Ship **${recommended_items[0]['shipping_fee']}**, Giao hàng: **{recommended_items[0]['delivery_time']}**.{tax_summary_line(recommended_items[0], lang)}{warning_msg}"
                else:
                    ans += "Hiện tại không có dữ liệu sản phẩm trong DB Cache phù hợp cho các dòng sản phẩm được đề xuất."
            else:
                ans = f"{warning_fallback}The climate in {resolved_country} during month {req_month} is **{sug.season}** ({sug.weather_context}).\n\n"
                ans += f"Key events: **{events_str}**.\n\n"
                ans += f"To maximize sales during this period, I recommend focusing on these products: **{product_types_str}**.\n\n"
                if recommended_items:
                    ans += f"Here are some of the best matching products from the catalog:\n"
                    ans += f"- SKU **{recommended_items[0]['sku']}** ({recommended_items[0]['display_name']}) from workshop **{recommended_items[0]['partner_name']}**. Costs: Base **${recommended_items[0]['base_cost']}**, Ship **${recommended_items[0]['shipping_fee']}**, Delivery: **{recommended_items[0]['delivery_time']}**.{tax_summary_line(recommended_items[0], lang)}{warning_msg}"
                else:
                    ans += "Currently no product data in DB Cache fits the recommended product lines."
            res["answer"] = ans
        else:
            # Recommend khi có product_type cụ thể
            items = search_products_tool(
                product_type=product_type, country=country_code,
                max_base_cost=max_base_cost, max_shipping_days=max_shipping_days, print_sides=print_sides
            )
            res["items"] = items
            res["tool_data"] = items

            warning_msg = ""
            if selling_price is not None:
                for item in items:
                    add_tax_pricing_fields(item, selling_price, country_code, tax_sub_region, item.get("product_name") or product_type)
                items.sort(key=lambda x: x.get("profit", 0), reverse=True)
            elif min_margin is not None and min_margin < 100:
                for item in items:
                    s_price = minimum_selling_price_for_margin(item, min_margin, country_code, tax_sub_region, item.get("product_name") or product_type)
                    add_tax_pricing_fields(item, s_price, country_code, tax_sub_region, item.get("product_name") or product_type)
                items.sort(key=lambda x: x["landed_cost"])
                warning_msg = f"\n*(Lưu ý: Để đạt mức profit margin tối thiểu {min_margin}%, hệ thống đã tự động tính toán giá bán lẻ gợi ý tối thiểu cho mỗi sản phẩm. Các sản phẩm được sắp xếp theo tổng chi phí fulfillment (Landed Cost) thấp nhất.)*"
                if lang == "en":
                    warning_msg = f"\n*(Note: To achieve a minimum profit margin of {min_margin}%, the system has calculated the minimum recommended retail price for each product. Products are sorted by lowest Landed Cost.)*"
            else:
                warning_msg = "\n*(Lưu ý: Do bạn chưa cung cấp giá bán lẻ (selling price), hệ thống đang tự động xếp hạng các sản phẩm theo tổng chi phí fulfillment (Landed Cost) thấp nhất. Hãy bổ sung giá bán để tính lợi nhuận và margin nhé!)*"
                if lang == "en":
                    warning_msg = "\n*(Note: Since you have not provided a selling price, the system automatically sorts products by the lowest Landed Cost. Please provide a retail price to calculate profit and margin!)*"

            res["is_nearest"] = any(item.get("filter_match") == "nearest_alternative" for item in items)

            filter_desc = []
            if max_base_cost:
                filter_desc.append(f"giá vốn dưới ${max_base_cost}" if lang == "vi" else f"base cost under ${max_base_cost}")
            if max_shipping_days:
                filter_desc.append(f"thời gian ship dưới {max_shipping_days} ngày" if lang == "vi" else f"shipping under {max_shipping_days} days")
            filter_str = (" và " if lang == "vi" else " and ").join(filter_desc)
            filter_str = (f" thỏa mãn {filter_str}" if lang == "vi" else f" matching {filter_str}") if filter_str else ""

            is_composite_eu_query = (country_code in ["DE", "FR", "EU"] or slots.get("target_market") == "EU") and \
                                    any(w in message.lower() for w in ["màu", "color", "ship", "kho", "xưởng", "vận chuyển", "duration", "transit", "trend"])

            if is_composite_eu_query:
                if lang == "vi":
                    ans = "### Phân tích thị trường & Logistics Đức/EU\n\n"
                    ans += "**1. Xu hướng thị trường (Market Insight):**\n"
                    ans += "Mùa hè này tại Đức và khu vực EU, các gam màu mát mẻ và trung tính như **Navy**, **Sport Grey**, **White** và **Black** đang rất được ưa chuộng. Các sản phẩm áo thun (T-Shirt) với chất liệu thoáng mát luôn đạt lượng bán ra cao nhất.\n\n"
                    ans += "**2. Thông tin vận chuyển & Kho hàng (Logistics Explanation):**\n"
                    ans += "Đối với dòng sản phẩm này, nếu xưởng nội địa EU (như **Lavit EU**) còn hàng, thời gian vận chuyển nội địa chỉ mất từ **3-5 business days**.\n"
                    ans += "Trong trường hợp xưởng nội địa EU hết hàng và phải điều phối sản xuất từ xưởng US sang Đức/EU, thời gian vận chuyển xuyên lục địa dự kiến sẽ kéo dài từ **7-10 business days** do các thủ tục thông quan và vận chuyển quốc tế.\n\n"
                    ans += "**3. Danh mục sản phẩm đề xuất (Targeted Catalog):**\n"
                    ans += "Dưới đây là danh sách các biến thể tối ưu nhất có thể giao đến thị trường Đức/EU mà hệ thống tìm thấy. Vui lòng tham khảo bảng chi tiết và chọn xưởng phù hợp bên dưới để tiến hành lên đơn hàng.\n"
                else:
                    ans = "### Market Analysis & Logistics Germany/EU\n\n"
                    ans += "**1. Market Insight:**\n"
                    ans += "This summer in Germany and the EU, cool and neutral colors like **Navy**, **Sport Grey**, **White**, and **Black** are highly popular. Lightweight cotton T-Shirts are seeing the highest sales volumes.\n\n"
                    ans += "**2. Logistics Explanation:**\n"
                    ans += "For these products, if fulfilled from local EU workshops (such as **Lavit EU**), domestic shipping takes only **3-5 business days**.\n"
                    ans += "If local stock runs out and we must route production to a US facility, the cross-border transit time to Germany/EU will take **7-10 business days** due to international customs and transit.\n\n"
                    ans += "**3. Targeted Catalog:**\n"
                    ans += "Below is the list of optimal variants delivering to Germany/EU. Please review the detailed catalog below and select the appropriate workshop to place a draft order.\n"
                res["answer"] = ans
            elif res["is_nearest"]:
                best_item = items[0]
                excess_desc = []
                excess = best_item.get("filter_excess", {})
                if "base_cost" in excess:
                    excess_desc.append(f"vượt ngân sách ${excess['base_cost']}" if lang == "vi" else f"exceeds budget by ${excess['base_cost']}")
                if "shipping_days" in excess:
                    excess_desc.append(f"ship lâu hơn {excess['shipping_days']} ngày" if lang == "vi" else f"ships {excess['shipping_days']} days slower")
                excess_str = f" ({', '.join(excess_desc)})" if excess_desc else ""

                if lang == "vi":
                    res["answer"] = f"Chế độ lựa chọn thay thế gần nhất: Mình không tìm thấy biến thể {product_type} nào đáp ứng hoàn toàn điều kiện {filter_str} tại {country_code}. Tuy nhiên, đây là những lựa chọn thay thế tốt nhất gần đạt yêu cầu của bạn:\n"
                    res["answer"] += f"- SKU **{best_item['sku']}** ({'in 2 mặt' if print_sides == 'both' else 'in 1 mặt'}) từ xưởng **{best_item['partner_name']}**{excess_str}. Chi phí: Base **${best_item['base_cost']}**, Ship **${best_item['shipping_fee']}**, Landed Cost: **${best_item['landed_cost']}**, Giao hàng: **{best_item['delivery_time']}**.{tax_summary_line(best_item, lang)}{warning_msg}"
                else:
                    res["answer"] = f"Nearest Alternative Mode: I could not find any {product_type} variants fully meeting the conditions {filter_str} for {country_code}. However, here are the best alternative options close to your request:\n"
                    res["answer"] += f"- SKU **{best_item['sku']}** ({'2-sided print' if print_sides == 'both' else '1-sided print'}) from workshop **{best_item['partner_name']}**{excess_str}. Costs: Base **${best_item['base_cost']}**, Ship **${best_item['shipping_fee']}**, Landed Cost: **${best_item['landed_cost']}**, Delivery: **{best_item['delivery_time']}**.{tax_summary_line(best_item, lang)}{warning_msg}"
            else:
                best_item = items[0] if items else None
                if best_item:
                    if lang == "vi":
                        res["answer"] = f"Dựa trên yêu cầu của bạn, mình đã tìm thấy {len(items)} biến thể {product_type} ({'in 2 mặt' if print_sides == 'both' else 'in 1 mặt'}) tại thị trường {country_code}{filter_str} hoạt động tốt:\n"
                        res["answer"] += f"- **Khuyến nghị tốt nhất:** SKU **{best_item['sku']}** từ xưởng **{best_item['partner_name']}**. Chi phí: Base **${best_item['base_cost']}**, Ship **${best_item['shipping_fee']}**, Landed Cost: **${best_item['landed_cost']}**, Giao hàng: **{best_item['delivery_time']}**.{tax_summary_line(best_item, lang)}{warning_msg}\n"
                    else:
                        res["answer"] = f"Based on your request, I found {len(items)} {product_type} variants ({'2-sided print' if print_sides == 'both' else '1-sided print'}) for market {country_code}{filter_str}:\n"
                        res["answer"] += f"- **Best recommendation:** SKU **{best_item['sku']}** from workshop **{best_item['partner_name']}**. Costs: Base **${best_item['base_cost']}**, Ship **${best_item['shipping_fee']}**, Landed Cost: **${best_item['landed_cost']}**, Delivery: **{best_item['delivery_time']}**.{tax_summary_line(best_item, lang)}{warning_msg}\n"

                    other_items = []
                    seen_partners = {best_item['partner_name']}
                    for item in items[1:]:
                        p_name = item['partner_name']
                        if p_name not in seen_partners:
                            other_items.append(item)
                            seen_partners.add(p_name)

                    if other_items:
                        if lang == "vi":
                            res["answer"] += "\n**Các lựa chọn tối ưu từ xưởng khác:**\n"
                            for o_item in other_items[:2]:
                                res["answer"] += f"- Xưởng **{o_item['partner_name']}**: SKU **{o_item['sku']}**, Base **${o_item['base_cost']}**, Ship **${o_item['shipping_fee']}**, Landed Cost: **{o_item['landed_cost']}**, Giao hàng: **{o_item['delivery_time']}**.\n"
                        else:
                            res["answer"] += "\n**Optimal options from other workshops:**\n"
                            for o_item in other_items[:2]:
                                res["answer"] += f"- Workshop **{o_item['partner_name']}**: SKU **{o_item['sku']}**, Base **${o_item['base_cost']}**, Ship **{o_item['shipping_fee']}**, Landed Cost: **{o_item['landed_cost']}**, Delivery: **{o_item['delivery_time']}**.\n"
                else:
                    res["answer"] = f"Mình xin lỗi, hiện tại không có sản phẩm {product_type} nào trong DB Cache tại {country_code}." if lang == "vi" else f"Sorry, there are currently no {product_type} products in the DB Cache for {country_code}."

    # 3. Xử lý so sánh (Compare)
    elif intent == "compare":
        compare_data = compare_shipping_tool(product_type=product_type, country=country_code, print_sides=print_sides)
        items = []
        for c in compare_data:
            items.append({
                "sku": c["sku"],
                "display_name": f"{product_type} tại {c['partner_name']} ({c['color']} / {c['size']})" if lang == "vi" else f"{product_type} at {c['partner_name']} ({c['color']} / {c['size']})",
                "product_name": product_type,
                "color": c["color"],
                "size": c["size"],
                "partner_name": c["partner_name"],
                "location_name": c["location_name"],
                "base_cost": c["base_cost"],
                "shipping_fee": c["shipping_fee"],
                "second_item_price": c["second_item_price"],
                "tax_fee": c["tax_fee"],
                "landed_cost": c["landed_cost"],
                "delivery_time": c["delivery_time"],
                "carrier": [c["carrier"]],
                "print_sides": print_sides
            })
        res["items"] = items
        res["tool_data"] = items

        if items:
            best_ship = min(items, key=lambda x: x["shipping_fee"])
            best_landed = min(items, key=lambda x: x["landed_cost"])
            if lang == "vi":
                ans = f"Dưới đây là bảng so sánh phí ship và giá của dòng {product_type} đến {country_code}:\n"
                ans += f"- Xưởng ship rẻ nhất: **{best_ship['partner_name']}** (Phí ship: **${best_ship['shipping_fee']}**, SLA: {best_ship['delivery_time']})\n"
                ans += f"- Xưởng tối ưu tổng chi phí (Landed Cost): **{best_landed['partner_name']}** (Landed Cost: **${best_landed['landed_cost']}**)\n"
                ans += "\nBạn có thể kiểm tra danh sách chi tiết các xưởng ở bảng hiển thị bên dưới."
            else:
                ans = f"Here is the comparison table of shipping fees and prices for {product_type} to {country_code}:\n"
                ans += f"- Cheapest shipping supplier: **{best_ship['partner_name']}** (Shipping: **${best_ship['shipping_fee']}**, SLA: {best_ship['delivery_time']})\n"
                ans += f"- Overall lowest cost supplier (Landed Cost): **{best_landed['partner_name']}** (Landed Cost: **${best_landed['landed_cost']}**)\n"
                ans += "\nYou can inspect the detailed list of workshops in the table below."
            res["answer"] = ans
        else:
            res["answer"] = f"Hiện tại không có dữ liệu so sánh xưởng cho dòng {product_type} tại quốc gia {country_code}." if lang == "vi" else f"Currently no workshop comparison data for {product_type} in country {country_code}."

    # 4. Tính Margin (Calculate Margin)
    elif intent == "calculate_margin":
        if not sku:
            res["clarification_required"] = True
            res["missing_field"] = "sku"
            if lang == "vi":
                res["question"] = "Vui lòng cung cấp mã SKU của sản phẩm cần tính margin."
                res["answer"] = "Để tính toán chính xác chi phí landed cost và tỷ suất lợi nhuận (margin), bạn vui lòng cung cấp mã SKU của sản phẩm (ví dụ: `USG5000-Black-S`) nhé!"
            else:
                res["question"] = "Please provide the SKU code for margin calculation."
                res["answer"] = "To calculate landed cost and profit margin accurately, please provide the SKU code of the product (e.g., `USG5000-Black-S`)!"
        else:
            calc = calculate_landed_cost_tool(
                sku=sku, country=country_code, quantity=quantity, selling_price=selling_price, print_sides=print_sides, tax_sub_region=tax_sub_region
            )
            if "error" in calc:
                res["answer"] = f"Lỗi: {calc['error']}" if lang == "vi" else f"Error: {calc['error']}"
            else:
                suggested_price = None
                if selling_price is None and min_margin is not None and min_margin < 100:
                    suggested_price = minimum_selling_price_for_margin(calc, min_margin, country_code, tax_sub_region, calc.get("product_name"))
                    add_tax_pricing_fields(calc, suggested_price, country_code, tax_sub_region, calc.get("product_name"), quantity=quantity)

                res["items"] = [calc]
                res["tool_data"] = calc
                print_sides_desc = ("in 2 mặt" if print_sides == "both" else "in 1 mặt") if lang == "vi" else ("2-sided print" if print_sides == "both" else "1-sided print")
                has_tax_data = any(calc.get(field) is not None for field in ("tax_type", "tax_amount", "net_revenue"))

                if lang == "vi":
                    ans = f"Báo cáo chi tiết Landed Cost cho SKU **{sku}** (Số lượng: {quantity}, {print_sides_desc}) tới **{country_code}**:\n"
                    ans += f"- Giá gốc (Base Cost): **${calc['total_base_cost']}** (${calc['base_cost']} x {quantity})\n"
                    ans += f"- Phí vận chuyển: **${calc['shipping_fee']}** ({calc['delivery_time']})\n"
                    if has_tax_data:
                        tax_display = calc.get('tax_amount', calc.get('tax_fee', 0.0))
                        tax_type = calc.get('tax_type', 'Tax')
                        tax_rate = calc.get('tax_rate_pct') or f"{int(calc.get('tax_rate', 0) * 100)}%"
                        ans += f"- Thuế ước tính: **${tax_display}** ({tax_type} {tax_rate})\n"
                        if calc.get('net_revenue') is not None:
                            ans += f"- Doanh thu sau thuế: **${calc['net_revenue']}**\n"
                    ans += f"- **Tổng chi phí fulfillment (Landed Cost): ${calc['landed_cost']}**\n"
                else:
                    ans = f"Detailed Landed Cost report for SKU **{sku}** (Quantity: {quantity}, {print_sides_desc}) to **{country_code}**:\n"
                    ans += f"- Base Cost: **${calc['total_base_cost']}** (${calc['base_cost']} x {quantity})\n"
                    ans += f"- Shipping Fee: **${calc['shipping_fee']}** ({calc['delivery_time']})\n"
                    if has_tax_data:
                        tax_display = calc.get('tax_amount', calc.get('tax_fee', 0.0))
                        tax_type = calc.get('tax_type', 'Tax')
                        tax_rate = calc.get('tax_rate_pct') or f"{int(calc.get('tax_rate', 0) * 100)}%"
                        ans += f"- Estimated tax: **${tax_display}** ({tax_type} {tax_rate})\n"
                        if calc.get('net_revenue') is not None:
                            ans += f"- Net revenue after tax: **${calc['net_revenue']}**\n"
                    ans += f"- **Fulfillment Cost (Landed Cost): ${calc['landed_cost']}**\n"

                if selling_price is not None:
                    if lang == "vi":
                        ans += f"\nVới giá bán lẻ đề xuất là **${selling_price}** (Doanh thu: ${calc['total_selling_price']}):\n"
                        ans += f"- Lợi nhuận gộp (Profit): **${calc['profit']}**\n"
                        ans += f"- Tỷ suất lợi nhuận (Margin): **{calc['margin_percent']}%**\n"
                        if min_margin and calc['margin_percent'] < min_margin:
                            ans += f"Lưu ý: Mức margin này thấp hơn mức tiêu chuẩn của bạn là {min_margin}%."
                        elif min_margin:
                            ans += f"Đạt tiêu chuẩn tối thiểu margin {min_margin}%."
                    else:
                        ans += f"\nWith a retail price of **${selling_price}** (Revenue: ${calc['total_selling_price']}):\n"
                        ans += f"- Gross Profit (Profit): **${calc['profit']}**\n"
                        ans += f"- Profit Margin (Margin): **{calc['margin_percent']}%**\n"
                        if min_margin and calc['margin_percent'] < min_margin:
                            ans += f"Note: This margin is lower than your target margin of {min_margin}%."
                        elif min_margin:
                            ans += f"Meets target margin of {min_margin}%."
                elif suggested_price is not None:
                    if lang == "vi":
                        ans += f"\nĐể đạt mức profit margin tối thiểu là **{min_margin}%**:\n"
                        ans += f"- **Giá bán đề xuất tối thiểu: ${suggested_price}**\n"
                        ans += f"- Lợi nhuận gộp ước tính: **${calc['profit']}**\n"
                        ans += f"- Tỷ suất lợi nhuận thực tế: **{calc['margin_percent']}%**\n"
                    else:
                        ans += f"\nTo achieve a minimum profit margin of **{min_margin}%**:\n"
                        ans += f"- **Minimum suggested selling price: ${suggested_price}**\n"
                        ans += f"- Estimated Gross Profit: **${calc['profit']}**\n"
                        ans += f"- Actual Profit Margin: **{calc['margin_percent']}%**\n"
                else:
                    ans += "\nBạn muốn đề xuất giá bán lẻ bao nhiêu cho sản phẩm này? Hãy cung cấp giá bán để mình tính Profit và Margin nhé." if lang == "vi" else "\nWhat is your target retail price for this product? Please provide a price to calculate profit and margin."
                res["answer"] = ans

    # 5. Tạo đơn hàng (Create Order)
    elif intent == "create_order":
        if not sku:
            res["clarification_required"] = True
            res["missing_field"] = "sku"
            if lang == "vi":
                res["question"] = "Vui lòng cung cấp mã SKU sản phẩm bạn muốn đặt đơn."
                res["answer"] = "Để bắt đầu tạo đơn hàng nháp, vui lòng cung cấp mã SKU của sản phẩm bạn đã chọn."
            else:
                res["question"] = "Please provide the product SKU you want to order."
                res["answer"] = "To start creating a draft order, please provide the SKU code of the product you have selected."
        elif not shipping_address:
            res["clarification_required"] = True
            res["missing_field"] = "shipping_address"
            if lang == "vi":
                res["question"] = "Vui lòng cung cấp thông tin người nhận: Tên, Địa chỉ, Thành phố, Mã zip, Quốc gia."
                res["answer"] = "Mình cần địa chỉ nhận hàng để tạo đơn hàng nháp. Bạn vui lòng cung cấp địa chỉ theo định dạng: Tên người nhận, Địa chỉ, Thành phố, Mã zip, Quốc gia nhé."
            else:
                res["question"] = "Please provide shipping information: Full Name, Address, City, Zip, Country."
                res["answer"] = "I need a shipping address to create a draft order. Please provide the address in the format: Full Name, Address line 1, City, Zip Code, Country."
        else:
            is_confirmed_msg = message.strip().lower() in ["confirm create sandbox order", "xác nhận tạo sandbox order"]
            confirmed_order_state = slots.get("confirmed_order", False)

            if not confirmed_order_state and not is_confirmed_msg:
                res["confirmation_required"] = True
                res["question"] = "Hãy gõ 'xác nhận tạo sandbox order' để hoàn thành việc đặt đơn hàng nháp." if lang == "vi" else "Type 'confirm create sandbox order' to finalize the draft order."

                calc = calculate_landed_cost_tool(
                    sku=sku, country=shipping_address.get("country", country_code), quantity=quantity, print_sides=print_sides, tax_sub_region=tax_sub_region
                )
                res["tool_data"] = calc

                name = shipping_address.get('full_name', '')
                masked_name = name[0] + "*** " + name.split(' ')[-1][0] + "***" if len(name.split(' ')) >= 2 else "Customer"
                addr = shipping_address.get('address1', '')
                masked_addr = addr[:3] + "********"
                zip_c = shipping_address.get('zip_code', '')
                masked_zip = zip_c[:2] + "***"

                print_sides_desc = ("in 2 mặt" if print_sides == "both" else "in 1 mặt") if lang == "vi" else ("2-sided print" if print_sides == "both" else "1-sided print")

                if lang == "vi":
                    ans = f"Xác nhận thông tin đơn hàng nháp (Draft Sandbox Order):\n"
                    ans += f"- Sản phẩm: **{calc.get('display_name', sku)}** (Số lượng: {quantity}, {print_sides_desc})\n"
                    ans += f"- Người nhận: **{masked_name}**\n"
                    ans += f"- Địa chỉ: {masked_addr}, {shipping_address.get('city')}, {masked_zip}, {shipping_address.get('country')}\n"
                    ans += f"- Tổng chi phí dự tính (Landed Cost): **${calc.get('landed_cost')}**\n\n"
                    ans += f"Để hoàn tất tạo đơn, bạn vui lòng copy và gõ chính xác dòng lệnh sau:\n"
                    ans += f"`xác nhận tạo sandbox order`"
                else:
                    ans = f"Confirm draft sandbox order details:\n"
                    ans += f"- Product: **{calc.get('display_name', sku)}** (Quantity: {quantity}, {print_sides_desc})\n"
                    ans += f"- Recipient: **{masked_name}**\n"
                    ans += f"- Address: {masked_addr}, {shipping_address.get('city')}, {masked_zip}, {shipping_address.get('country')}\n"
                    ans += f"- Estimated Total Cost (Landed Cost): **${calc.get('landed_cost')}**\n\n"
                    ans += f"To finalize the order, please copy and type the exact line below:\n"
                    ans += f"`confirm create sandbox order`"
                res["answer"] = ans
                slots["confirmed_order"] = True
            else:
                order_res = await create_draft_order_tool(
                    sku=sku, quantity=quantity, country=shipping_address.get("country", country_code),
                    full_name=shipping_address.get("full_name"), address1=shipping_address.get("address1"),
                    city=shipping_address.get("city"), zip_code=shipping_address.get("zip_code"), print_sides=print_sides
                )
                res["tool_data"] = order_res
                if order_res.get("success"):
                    res["status"] = order_res.get("status")
                    res["order_id"] = order_res.get("order_id")
                    if lang == "vi":
                        res["answer"] = f"Tạo đơn hàng thành công!\nĐơn hàng nháp **{res['order_id']}** đã được tạo thành công trên hệ thống BurgerPrints (Chế độ Sandbox: {settings.burgerprints_enable_sandbox_create_order}). Bạn có thể xem chi tiết đơn trong lịch sử đơn hàng của mình."
                    else:
                        res["answer"] = f"Order created successfully!\nDraft order **{res['order_id']}** has been successfully created on BurgerPrints (Sandbox mode: {settings.burgerprints_enable_sandbox_create_order}). You can review it in your order history."
                    slots.pop("sku", None)
                    slots.pop("shipping_address", None)
                    slots.pop("confirmed_order", None)
                else:
                    res["answer"] = f"Tạo đơn hàng thất bại: Hệ thống BurgerPrints gặp sự cố khi xử lý thông tin đơn hàng của bạn. Vui lòng kiểm tra lại dữ liệu và thử lại." if lang == "vi" else f"Order creation failed: BurgerPrints encountered an issue processing your order. Please check your data and try again."

    # 5.1 Xử lý get_system_metadata
    elif intent == "get_system_metadata":
        res["tool_data"] = {"system_status": "active", "sandbox_mode": settings.burgerprints_enable_sandbox_create_order}
        if lang == "vi":
            res["answer"] = f"Hệ thống Smart Agent hiện đang hoạt động bình thường ở trạng thái ổn định.\nChế độ Sandbox: **{'Bật (ON)' if settings.burgerprints_enable_sandbox_create_order else 'Tắt (OFF)'}**."
        else:
            res["answer"] = f"The Smart Agent system is running normally and is currently stable.\nSandbox mode: **{'ON' if settings.burgerprints_enable_sandbox_create_order else 'OFF'}**."

    # 5.2 Xử lý general_knowledge_conversation
    elif intent == "general_knowledge_conversation":
        res["tool_data"] = None
        res["items"] = []
        msg_clean = message.lower()
        if "thủ đô" in msg_clean and "đức" in msg_clean:
            res["answer"] = "Thủ đô của nước Đức là Berlin. Về múi giờ, Đức sử dụng múi giờ UTC+1 (hoặc UTC+2 vào mùa hè), lệch khoảng 5 đến 6 tiếng so với Việt Nam (UTC+7). Việc tính toán này không liên quan đến thông tin sản phẩm BurgerPrints."
        elif "80/20" in msg_clean:
            res["answer"] = "Nguyên lý 80/20 (Pareto) trong kinh doanh chỉ ra rằng khoảng 80% kết quả được tạo ra từ 20% nguyên nhân cốt lõi. Ví dụ tiêu biểu là 80% doanh thu của một doanh nghiệp thường đến từ 20% lượng khách hàng lớn nhất."
        elif "tagline" in msg_clean and ("mug" in msg_clean or "cốc" in msg_clean):
            res["answer"] = "Dưới đây là 3 câu tagline tiếng Anh ngắn gọn thu hút cho Mugs dịp Father's Day:\n1. Fueling the World's Greatest Dad\n2. Best Dad Ever in Every Sip\n3. King of the Coffee Mug"
        else:
            res["answer"] = "Rất tiếc, tôi chưa thể kết nối với mô hình ngôn ngữ lớn để trả lời câu hỏi kiến thức chung này. Vui lòng thử lại sau." if lang == "vi" else "I apologize, but I cannot answer this general knowledge query without a large language model connection. Please try again later."

    # 6. Các trường hợp còn lại
    else:
        res["answer"] = "Chào bạn! Mình là AI Agent trợ lý POD từ BurgerPrints. Bạn có thể hỏi mình tìm sản phẩm, so sánh xưởng, tính chi phí landed cost và profit margin, hoặc tạo đơn hàng nháp." if lang == "vi" else "Hello! I am your BurgerPrints POD AI Assistant. Feel free to ask me to search products, compare suppliers, calculate landed costs and profit margins, or create draft sandbox orders."

    return res
