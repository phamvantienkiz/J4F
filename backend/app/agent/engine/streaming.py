import json
import datetime
import asyncio
from typing import List, Dict, Any, AsyncGenerator
from sqlmodel import Session, select
import app.database as db
from app.config import settings
from app.models.session import ChatSession
from app.agent.prompt import AGENT_SYSTEM_PROMPT, AGENT_GENERATOR_PROMPT
from app.agent.tools import mask_pii
from app.agent.engine.intent import parse_intent_and_slots, normalize_slots, extract_country_explanation_code, get_shipping_country_option, is_global_availability_query, resolve_effective_language, language_runtime_instruction
from app.agent.engine.heuristic import build_active_item_state, execute_heuristic_flow, public_slots
from app.agent.engine.guardrails import check_guardrails
from app.agent.engine.tokens import add_usage_to_meta, empty_token_meta
from app.agent.engine.formatting import sanitize_markdown_layout

async def run_stream_logic(engine, session_id: str, message: str, history: List[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
    """SSE Streaming generator xử lý từng bước, stream tokens và yield kết quả cuối cùng."""
    history = history or []
    token_meta = empty_token_meta()

    # Kiểm tra guardrails ngay lập tức ở mức Heuristic/Engine layer để tiết kiệm token
    guardrail_response = check_guardrails(message)
    if guardrail_response:
        words = guardrail_response.split(" ")
        for word in words:
            yield {"text": word + " "}
            await asyncio.sleep(0.02)

        with Session(db.engine) as session:
            db_session = session.exec(select(ChatSession).where(ChatSession.session_id == session_id)).first()
            if not db_session:
                db_session = ChatSession(
                    session_id=session_id, history=[], slots={}, current_intent="general_chat"
                )
            else:
                db_session.updated_at = datetime.datetime.utcnow()
            session.add(db_session)
            session.commit()

        yield {
            "answer": guardrail_response,
            "intent": "general_chat",
            "session_id": session_id,
            "meta": token_meta,
            "confirmation_required": False,
            "params": {},
            "data": {
                "source": "database_cache",
                "match_type": "exact",
                "clarification_required": False,
                "missing_field": None,
                "question": None,
                "items": [],
                "status": None,
                "sandbox": settings.burgerprints_enable_sandbox_create_order,
                "id": None
            }
        }
        return

    # 1. Truy cập DB để lấy hoặc tạo ChatSession
    with Session(db.engine) as session:
        db_session = session.exec(select(ChatSession).where(ChatSession.session_id == session_id)).first()
        if not db_session:
            db_session = ChatSession(
                session_id=session_id, history=[], slots={}, current_intent="general_chat"
            )
            session.add(db_session)
            session.commit()
            session.refresh(db_session)
        current_slots = db_session.slots or {}
        _db_slots_snapshot = dict(current_slots)  # preserve original DB slots for category reset detection
        current_intent = db_session.current_intent
        persisted_history = db_session.history or []

    history = history or persisted_history
    lang = resolve_effective_language(message, history)
    runtime_language_instruction = language_runtime_instruction(lang)
    pending_shipping_location = (
        current_slots.get("_missing_field") == "shipping_location" or
        (current_intent in ["recommend", "compare", "calculate_margin"] and (current_slots.get("product_type") or current_slots.get("sku")) and not current_slots.get("country"))
    )
    explanation_code = extract_country_explanation_code(message)
    if pending_shipping_location and explanation_code:
        country_option = get_shipping_country_option(explanation_code)
        if country_option:
            if lang == "vi":
                answer = f"Mã {country_option['code']} là quốc gia {country_option['name']} đó bạn. Bạn có muốn chọn quốc gia này để tính phí ship không?"
            else:
                answer = f"{country_option['code']} is {country_option['name']}. Do you want to choose this destination for the shipping calculation?"
            for word in answer.split(" "):
                yield {"text": word + " "}
                await asyncio.sleep(0.03)
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": answer})
            session_slots = current_slots.copy()
            session_slots["_missing_field"] = "shipping_location"
            session_slots["_pending_country"] = country_option["code"]
            with Session(db.engine) as session:
                db_session = session.exec(select(ChatSession).where(ChatSession.session_id == session_id)).first()
                if db_session:
                    db_session.history = history
                    db_session.slots = session_slots
                    db_session.current_intent = current_intent or "recommend"
                    db_session.updated_at = datetime.datetime.utcnow()
                    session.add(db_session)
                    session.commit()
            yield {
                "answer": answer,
                "intent": current_intent or "recommend",
                "session_id": session_id,
                "meta": token_meta,
                "confirmation_required": False,
                "params": {k: v for k, v in current_slots.items() if not k.startswith("_")},
                "data": {
                    "source": "database_cache",
                    "match_type": "exact",
                    "clarification_required": True,
                    "missing_field": "shipping_location",
                    "question": answer,
                    "items": [],
                    "status": None,
                    "sandbox": settings.burgerprints_enable_sandbox_create_order,
                    "id": None,
                    "metadata": {"explained_country": country_option, "required_slots": ["country"]},
                    "margin_alert": False,
                    "custom_payload": {"suggested_countries": [country_option]}
                }
            }
            return

    # Phân tích thô trước để lấy country_code và product_type cho các câu thought process
    inferred_intent, updated_slots = parse_intent_and_slots(message, current_slots, current_intent, persisted_history)
    current_slots = updated_slots
    country_code = updated_slots.get("country")
    country_label = country_code or ("chưa xác định" if lang == "vi" else "unspecified destination")
    product_type_label = updated_slots.get("product_type") or ("sản phẩm" if lang == "vi" else "products")

    # 2. Phát ra 3 bước thought process định dạng ngôn ngữ động (Không chứa emoji)
    if inferred_intent == "get_system_metadata":
        if lang == "vi":
            steps = [
                {"step": "analyzing", "message": "Hệ thống: Đang kiểm tra kết nối API BurgerPrints..."},
                {"step": "fetching", "message": "Hệ thống: Đang kiểm tra trạng thái cơ sở dữ liệu và cache..."},
                {"step": "calculating", "message": "Hệ thống: Đang truy xuất thông tin cấu hình và siêu dữ liệu hệ thống..."}
            ]
        else:
            steps = [
                {"step": "analyzing", "message": "System: Checking BurgerPrints API connection..."},
                {"step": "fetching", "message": "System: Checking database and cache status..."},
                {"step": "calculating", "message": "System: Retrieving system metadata and configuration info..."}
            ]
    elif lang == "vi":
        steps = [
            {"step": "analyzing", "message": f"Đang phân tích thị trường {country_label}..."},
            {"step": "fetching", "message": f"Đang truy vấn danh sách sản phẩm {product_type_label} từ BurgerPrints Catalog..."},
            {"step": "calculating", "message": f"Đang kiểm tra yêu cầu logistics cho sản phẩm {product_type_label}..."}
        ]
    else:
        steps = [
            {"step": "analyzing", "message": f"Analyzing market context for {country_label}..."},
            {"step": "fetching", "message": f"Fetching {product_type_label} product listings from BurgerPrints Catalog..."},
            {"step": "calculating", "message": f"Checking logistics requirements for {product_type_label}..."}
        ]

    for step in steps:
        yield step
        await asyncio.sleep(0.4)

    history.append({"role": "user", "content": message})

    # 3. Phân tích LLM Intent và Slots nếu không dùng mock key
    llm_response = None
    if not engine.is_mock_key:
        try:
            system_prompt = (
                AGENT_SYSTEM_PROMPT
                + f"\n\n{runtime_language_instruction}"
                + f"\n\nTrạng thái các Slots đã thu thập từ trước trong DB của session này: {json.dumps(current_slots, ensure_ascii=False)}"
            )
            messages = [{"role": "system", "content": system_prompt}]
            for msg_hist in history[-6:]:
                messages.append({"role": msg_hist.get("role", "user"), "content": msg_hist.get("content", "")})

            response = await engine.client.chat.completions.create(
                model=engine.model_name,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
                timeout=15.0
            )
            add_usage_to_meta(token_meta, getattr(response, "usage", None))
            llm_response = json.loads(response.choices[0].message.content)
        except Exception:
            llm_response = None

    intent = llm_response.get("intent", inferred_intent) if llm_response else inferred_intent
    if inferred_intent == "general_knowledge_conversation":
        intent = "general_knowledge_conversation"

    parsed_slots = updated_slots.copy()
    if llm_response and intent != "get_system_metadata":
        for k, v in llm_response.get("slots", {}).items():
            if v is not None and v != "":
                parsed_slots[k] = v
    for functional_slot in ["product_type", "print_sides", "sku", "quantity", "country", "target_market", "max_base_cost", "max_shipping_days", "selling_price", "min_margin", "shipping_address", "shipping_carrier"]:
        if updated_slots.get(functional_slot) is not None:
            parsed_slots[functional_slot] = updated_slots[functional_slot]
    slots = updated_slots.copy()
    for k, v in parsed_slots.items():
        if v is not None and v != "":
            slots[k] = v
    slots = normalize_slots(slots)

    if is_global_availability_query(message):
        slots.pop("country", None)
        slots.pop("target_market", None)
        slots.pop("_missing_field", None)
        slots.pop("_pending_country", None)
        slots.pop("_active_items", None)
        slots.pop("_active_skus", None)
        slots.pop("_active_product_ids", None)
        intent = "global_availability"

    # Defensive post-merge purge: block LLM from re-introducing stale category params
    _final_pt = slots.get("product_type")
    _old_pt = _db_slots_snapshot.get("product_type")
    if _old_pt and _final_pt and _final_pt != _old_pt:
        print(f"[SLOT-DEBUG] CATEGORY SWITCH detected: {_old_pt} -> {_final_pt} | slots BEFORE purge: {json.dumps(slots, ensure_ascii=False)}")
        for _stale_key in ['max_base_cost', 'selling_price', 'min_margin', 'max_shipping_days', 'print_sides', 'sku', 'quantity', '_active_items', '_active_skus', '_active_product_ids']:
            slots.pop(_stale_key, None)

    print(f"[SLOT-DEBUG] FINAL slots before execute_heuristic_flow: {json.dumps(slots, ensure_ascii=False)}", flush=True)
    print(f"[SLOT-DEBUG] selling_price={slots.get('selling_price')} min_margin={slots.get('min_margin')}", flush=True)
    print(f"[SLOT-DEBUG] DB snapshot (pre-parse): product_type={_db_slots_snapshot.get('product_type')}", flush=True)

    country_code = slots.get("country")

    if _db_slots_snapshot.get("_missing_field") == "shipping_location" and country_code and (slots.get("product_type") or slots.get("sku")):
        if current_intent in ["recommend", "compare", "calculate_margin"]:
            intent = current_intent
        elif inferred_intent in ["recommend", "compare", "calculate_margin"]:
            intent = inferred_intent
        else:
            intent = "recommend"

    if intent in ["general_chat", "general_knowledge_conversation"] and inferred_intent in ["recommend", "compare", "calculate_margin"] and (slots.get("product_type") or slots.get("sku")):
        intent = inferred_intent

    if slots.get("sku") and slots.get("quantity") and any(word in message.lower() for word in ["total shipping", "shipping cost", "calculate"]):
        intent = "calculate_margin"
    elif slots.get("sku") and slots.get("max_shipping_days") is None and any(word in message.lower() for word in ["xưởng", "xuong", "hãng", "hang", "carrier", "ship được"]):
        intent = "compare"

    if intent == "create_order" and slots.get("max_shipping_days") is not None and slots.get("product_type") and not isinstance(slots.get("shipping_address"), dict):
        intent = "recommend"

    # Preserve create_order intent when confirmation is pending (user said "yes/confirm/xác nhận")
    if current_intent == "create_order" and slots.get("confirmed_order") and slots.get("sku"):
        intent = "create_order"

    if inferred_intent == "create_order" and slots.get("sku"):
        intent = "create_order"

    # 4. Thực thi logic nghiệp vụ Core/Heuristic
    import os
    try:
        log_path = os.path.join(os.getcwd(), "debug_trace.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[STREAMING-DEBUG] calling execute_heuristic_flow: intent={intent} slots={slots}\n")
            f.write(f"[STREAMING-DEBUG] CWD={os.getcwd()}\n")
    except Exception as e:
        print(f"DEBUG LOG ERROR: {e}")
    res = await execute_heuristic_flow(engine, intent, slots, message, lang, country_code, history, previous_slots=_db_slots_snapshot)
    answer = res["answer"]
    items = res["items"]
    tool_data = res["tool_data"]
    is_nearest = res["is_nearest"]
    clarification_required = res["clarification_required"]
    missing_field = res["missing_field"]
    question = res["question"]
    confirmation_required = res["confirmation_required"]
    status = res["status"]
    order_id = res["order_id"]
    metadata = res.get("metadata", {})
    margin_alert = res.get("margin_alert", False)
    custom_payload = res.get("custom_payload") or {"items": items, "metadata": metadata}

    # 5. Stream LLM tokens hoặc Mock tokens
    final_answer = ""
    # Luôn gọi LLM generator để tạo text analysis, ngay cả khi có product items
    # (Trước đây bỏ qua khi intent="recommend" và có items, khiến answer="" và UI thiếu text)
    # EXCEPTION: Skip generator for confirmation_required (order preview) - use deterministic answer from heuristic
    # to prevent LLM from hallucinating "SKU not found" errors when the SKU is actually valid
    should_call_generator = (
        not engine.is_mock_key and
        not confirmation_required and
        missing_field != "shipping_location" and
        (tool_data is not None or intent in ["general_knowledge_conversation", "capability_discovery", "get_system_metadata"] or clarification_required)
    )
    if should_call_generator:
        now = datetime.datetime.now()
        months_en = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        months_vi = ["Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"]
        server_time_context = f"Current Month: {months_en[now.month - 1]} ({months_vi[now.month - 1]}), Current Year: {now.year}"

        # Create a compact copy of tool_data for LLM.
        # CRITICAL: Preserve variants array with factory-level fields only.
        # Do NOT drop variants — they contain multi-factory/multi-supplier data
        # the LLM needs for direct factory comparison (e.g., Helia vs Truong Son).
        _VARIANT_FIELDS_FOR_LLM = {"sku", "partner_name", "location_name", "base_cost", "shipping_fee",
                                     "landed_cost", "delivery_time", "color", "size", "carrier"}
        def _slim_variant(var: dict) -> dict:
            return {k: var[k] for k in _VARIANT_FIELDS_FOR_LLM if k in var}

        tool_data_for_llm = None
        if tool_data is not None:
            if isinstance(tool_data, list):
                tool_data_for_llm = []
                for item in tool_data:
                    if isinstance(item, dict):
                        item_copy = item.copy()
                        if "variants" in item_copy and isinstance(item_copy["variants"], list):
                            item_copy["variants"] = [_slim_variant(v) for v in item_copy["variants"] if isinstance(v, dict)]
                        tool_data_for_llm.append(item_copy)
                    else:
                        tool_data_for_llm.append(item)
            elif isinstance(tool_data, dict):
                tool_data_for_llm = tool_data.copy()
                if "items" in tool_data_for_llm and isinstance(tool_data_for_llm["items"], list):
                    items_copy = []
                    for item in tool_data_for_llm["items"]:
                        if isinstance(item, dict):
                            item_copy = item.copy()
                            if "variants" in item_copy and isinstance(item_copy["variants"], list):
                                item_copy["variants"] = [_slim_variant(v) for v in item_copy["variants"] if isinstance(v, dict)]
                            items_copy.append(item_copy)
                        else:
                            items_copy.append(item)
                    tool_data_for_llm["items"] = items_copy
            else:
                tool_data_for_llm = tool_data

        # Kiểm tra xem danh sách sản phẩm có rỗng hay không (đối với recommend / compare)
        is_empty_state = False
        if intent in ["recommend", "compare"]:
            if not tool_data_for_llm or (isinstance(tool_data_for_llm, list) and len(tool_data_for_llm) == 0):
                is_empty_state = True
            elif isinstance(tool_data_for_llm, dict) and "items" in tool_data_for_llm and not tool_data_for_llm["items"]:
                is_empty_state = True

        resolved_input_json = json.dumps({
            "intent": intent,
            "slots": slots,
            "metadata": metadata,
            "margin_alert": margin_alert,
            "empty_state": is_empty_state
        }, ensure_ascii=False)
        calculated_products_json = json.dumps(tool_data_for_llm, ensure_ascii=False)

        generator_prompt = AGENT_GENERATOR_PROMPT.format(
            server_time_context=server_time_context,
            resolved_input_json=resolved_input_json,
            calculated_products_json=calculated_products_json
        )
        generator_prompt += f"\n\n{runtime_language_instruction}"

        if is_empty_state:
            generator_prompt += "\n\nCRITICAL SYSTEM RULES FOR EMPTY STATE:\n" \
                                "- The 'Raw Calculation Results' is EMPTY (Best Pick = None).\n" \
                                "- You are STRICTLY PROHIBITED from fabricating, inventing, suggesting or discussing any products, SKUs, colors, sizes, or base costs.\n" \
                                "- You must clearly and explicitly state to the seller in the text response that NO matching products or variants were found in the catalog.\n" \
                                "- Keep the response brief, professional and do not list any product names."

        try:
            messages = [{"role": "system", "content": generator_prompt}]
            for msg_hist in history[-5:]:
                if msg_hist.get("content", "") == "" and msg_hist.get("role", "assistant") == "assistant":
                    continue
                messages.append({"role": msg_hist.get("role", "user"), "content": msg_hist.get("content", "")})

            response_stream = await engine.client.chat.completions.create(
                model=engine.model_name,
                messages=messages,
                temperature=0.3,
                timeout=15.0,
                stream=True,
                stream_options={"include_usage": True}
            )
            async for chunk in response_stream:
                print(f"[Streaming SDK Raw Chunk]: {chunk}")
                add_usage_to_meta(token_meta, getattr(chunk, "usage", None))
                if not chunk.choices:
                    print("[Azure Content Safety Chunk Detected]")
                    continue
                choice = chunk.choices[0]
                if choice.delta is None:
                    continue
                token = choice.delta.content
                if token is None:
                    continue
                if token:
                    final_answer += token
            answer = final_answer.strip()
        except Exception:
            pass

    answer = sanitize_markdown_layout(mask_pii(answer))
    if answer:
        yield {"text": answer}

    history.append({"role": "assistant", "content": answer})

    # 6. Lưu lịch sử chat
    session_slots = slots.copy()
    if items:
        session_slots.update(build_active_item_state(items))
    elif intent in ["recommend", "compare", "calculate_margin"] and not missing_field:
        session_slots.pop("_active_items", None)
        session_slots.pop("_active_skus", None)
        session_slots.pop("_active_product_ids", None)
    if missing_field:
        session_slots["_missing_field"] = missing_field
    else:
        session_slots.pop("_missing_field", None)
        session_slots.pop("_pending_country", None)
    with Session(db.engine) as session:
        db_session = session.exec(select(ChatSession).where(ChatSession.session_id == session_id)).first()
        if db_session:
            db_session.history = history
            db_session.slots = session_slots
            db_session.current_intent = intent
            db_session.updated_at = datetime.datetime.utcnow()
            session.add(db_session)
            session.commit()

    # 7. Gửi kết quả cuối cùng
    yield {
        "answer": answer,
        "intent": intent,
        "session_id": session_id,
        "meta": token_meta,
        "confirmation_required": confirmation_required,
        "params": public_slots(slots),
        "data": {
            "source": "database_cache",
            "match_type": "exact" if items and not is_nearest else "partial",
            "clarification_required": clarification_required,
            "missing_field": missing_field,
            "question": question,
            "items": items,
            "status": status,
            "sandbox": settings.burgerprints_enable_sandbox_create_order,
            "id": order_id,
            "metadata": metadata,
            "margin_alert": margin_alert,
            "custom_payload": custom_payload
        }
    }
