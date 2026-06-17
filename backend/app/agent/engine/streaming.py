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
from app.agent.engine.intent import parse_intent_and_slots, detect_language, normalize_slots
from app.agent.engine.heuristic import execute_heuristic_flow
from app.agent.engine.guardrails import check_guardrails

async def run_stream_logic(engine, session_id: str, message: str, history: List[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
    """SSE Streaming generator xử lý từng bước, stream tokens và yield kết quả cuối cùng."""
    history = history or []

    # Kiểm tra guardrails ngay lập tức ở mức Heuristic/Engine layer để tiết kiệm token
    guardrail_response = check_guardrails(message)
    if guardrail_response:
        words = guardrail_response.split(" ")
        for word in words:
            yield {"token": word + " "}
            await asyncio.sleep(0.02)

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": guardrail_response})

        with Session(db.engine) as session:
            db_session = session.exec(select(ChatSession).where(ChatSession.session_id == session_id)).first()
            if not db_session:
                db_session = ChatSession(
                    session_id=session_id, history=history, slots={}, current_intent="general_chat"
                )
            else:
                db_session.history = history
                db_session.updated_at = datetime.datetime.utcnow()
            session.add(db_session)
            session.commit()

        yield {
            "answer": guardrail_response,
            "intent": "general_chat",
            "session_id": session_id,
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

    lang = detect_language(message)

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
        current_intent = db_session.current_intent

    # Phân tích thô trước để lấy country_code và product_type cho các câu thought process
    inferred_intent, updated_slots = parse_intent_and_slots(message, current_slots, current_intent)
    if updated_slots.get("target_market") == "EU" and updated_slots.get("country") not in ["DE", "FR"]:
        updated_slots["country"] = "DE"
    country_code = updated_slots.get("country") or "US"
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
            {"step": "analyzing", "message": f"Đang phân tích xu hướng thị trường {country_code}..."},
            {"step": "fetching", "message": f"Đang truy vấn danh sách sản phẩm {product_type_label} từ BurgerPrints Catalog..."},
            {"step": "calculating", "message": f"Đang tối ưu chi phí phôi và tính toán Profit Margin cho sản phẩm {product_type_label}..."}
        ]
    else:
        steps = [
            {"step": "analyzing", "message": f"Analyzing market trends for {country_code}..."},
            {"step": "fetching", "message": f"Fetching {product_type_label} product listings from BurgerPrints Catalog..."},
            {"step": "calculating", "message": f"Optimizing base costs and calculating Profit Margin for {product_type_label}..."}
        ]

    for step in steps:
        yield step
        await asyncio.sleep(0.4)

    history.append({"role": "user", "content": message})

    # 3. Phân tích LLM Intent và Slots nếu không dùng mock key
    llm_response = None
    if not engine.is_mock_key:
        try:
            system_prompt = AGENT_SYSTEM_PROMPT + f"\n\nTrạng thái các Slots đã thu thập từ trước trong DB của session này: {json.dumps(current_slots, ensure_ascii=False)}"
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
            llm_response = json.loads(response.choices[0].message.content)
        except Exception:
            llm_response = None

    intent = llm_response.get("intent", inferred_intent) if llm_response else inferred_intent
    if inferred_intent == "general_knowledge_conversation":
        intent = "general_knowledge_conversation"

    if intent == "get_system_metadata":
        parsed_slots = updated_slots
    else:
        parsed_slots = llm_response.get("slots", updated_slots) if llm_response else updated_slots
    slots = current_slots.copy()
    for k, v in parsed_slots.items():
        if v is not None and v != "":
            slots[k] = v
    slots = normalize_slots(slots)
    country_code = slots.get("country") or "US"

    if intent == "calculate_margin" and current_intent in ["recommend", "compare"] and not slots.get("sku"):
        intent = current_intent

    # 4. Thực thi logic nghiệp vụ Core/Heuristic
    res = await execute_heuristic_flow(engine, intent, slots, message, lang, country_code)
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

    # 5. Stream LLM tokens hoặc Mock tokens
    final_answer = ""
    should_call_generator = (
        not engine.is_mock_key and
        not clarification_required and
        intent != "get_system_metadata" and
        (tool_data is not None or intent == "general_knowledge_conversation")
    )
    if should_call_generator:
        now = datetime.datetime.now()
        months_en = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        months_vi = ["Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"]
        server_time_context = f"Current Month: {months_en[now.month - 1]} ({months_vi[now.month - 1]}), Current Year: {now.year}"

        resolved_input_json = json.dumps({"intent": intent, "slots": slots}, ensure_ascii=False)
        calculated_products_json = json.dumps(tool_data, ensure_ascii=False)

        generator_prompt = AGENT_GENERATOR_PROMPT.format(
            server_time_context=server_time_context,
            resolved_input_json=resolved_input_json,
            calculated_products_json=calculated_products_json
        )
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
                stream=True
            )
            async for chunk in response_stream:
                print(f"[Streaming SDK Raw Chunk]: {chunk}")
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
                    yield {"token": token}
            answer = final_answer.strip()
        except Exception:
            # Fallback mock streaming từ câu trả lời thô
            words = answer.split(" ")
            for word in words:
                yield {"token": word + " "}
                await asyncio.sleep(0.03)
    else:
        # Mock streaming cho câu trả lời thô/fallback
        words = answer.split(" ")
        for word in words:
            yield {"token": word + " "}
            await asyncio.sleep(0.03)

    # Che giấu PII
    answer = mask_pii(answer)
    history.append({"role": "assistant", "content": answer})

    # 6. Lưu lịch sử chat
    with Session(db.engine) as session:
        db_session = session.exec(select(ChatSession).where(ChatSession.session_id == session_id)).first()
        if db_session:
            db_session.history = history
            db_session.slots = slots
            db_session.current_intent = intent
            db_session.updated_at = datetime.datetime.utcnow()
            session.add(db_session)
            session.commit()

    # 7. Gửi kết quả cuối cùng
    yield {
        "answer": answer,
        "intent": intent,
        "session_id": session_id,
        "confirmation_required": confirmation_required,
        "params": slots,
        "data": {
            "source": "database_cache",
            "match_type": "exact" if items and not is_nearest else "partial",
            "clarification_required": clarification_required,
            "missing_field": missing_field,
            "question": question,
            "items": items,
            "status": status,
            "sandbox": settings.burgerprints_enable_sandbox_create_order,
            "id": order_id
        }
    }
