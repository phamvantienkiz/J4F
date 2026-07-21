import json
import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI, AsyncAzureOpenAI
from sqlmodel import Session, select
import app.database as db
from app.config import settings
from app.models.session import ChatSession
from app.agent.prompt import AGENT_SYSTEM_PROMPT, AGENT_GENERATOR_PROMPT
from app.agent.tools import mask_pii
from app.services.trend import TrendService
from app.agent.engine.intent import parse_intent_and_slots, detect_language, normalize_slots, extract_country_explanation_code, get_shipping_country_option, is_global_availability_query, resolve_effective_language, language_runtime_instruction
from app.agent.engine.heuristic import build_active_item_state, execute_heuristic_flow, public_slots
from app.agent.engine.streaming import run_stream_logic
from app.agent.engine.guardrails import check_guardrails
from app.agent.engine.tokens import add_usage_to_meta, empty_token_meta
from app.agent.engine.formatting import sanitize_markdown_layout

class AgentEngine:
    def __init__(self):
        self.openai_api_key = settings.openai_api_key
        self.azure_api_key = settings.azure_openai_api_key

        if self.azure_api_key:
            self.client = AsyncAzureOpenAI(
                api_key=self.azure_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version
            )
            self.is_mock_key = False
            self.model_name = settings.azure_openai_chat_deployment or "gpt-4.1-mini"
        else:
            self.is_mock_key = self.openai_api_key == "mock-key" or not self.openai_api_key
            if not self.is_mock_key:
                self.client = AsyncOpenAI(api_key=self.openai_api_key)
            else:
                self.client = None
            self.model_name = "gpt-4o-mini"
        self.trend_service = TrendService()

    def _heuristic_parse(self, message: str, slots: Dict[str, Any], current_intent: Optional[str], history: List[Dict[str, Any]] = None) -> tuple[str, Dict[str, Any]]:
        return parse_intent_and_slots(message, slots, current_intent, history)

    def detect_language(self, message: str) -> str:
        return detect_language(message)

    async def run(self, session_id: str, message: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Xử lý hội thoại một cách đồng bộ."""
        history = history or []
        token_meta = empty_token_meta()

        guardrail_response = check_guardrails(message)
        if guardrail_response:
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
            return {
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
                return {
                    "answer": answer,
                    "intent": current_intent or "recommend",
                    "session_id": session_id,
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

        inferred_intent, updated_slots = self._heuristic_parse(message, current_slots, current_intent, persisted_history)
        current_slots = updated_slots
        country_code = updated_slots.get("country")

        history.append({"role": "user", "content": message})

        llm_response = None
        if not self.is_mock_key:
            try:
                system_prompt = (
                    AGENT_SYSTEM_PROMPT
                    + f"\n\n{runtime_language_instruction}"
                    + f"\n\nTrạng thái các Slots: {json.dumps(current_slots, ensure_ascii=False)}"
                )
                messages = [{"role": "system", "content": system_prompt}]
                for msg_hist in history[-6:]:
                    messages.append({"role": msg_hist.get("role", "user"), "content": msg_hist.get("content", "")})

                response = await self.client.chat.completions.create(
                    model=self.model_name,
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

        # Ép buộc định tuyến sang general_knowledge_conversation nếu heuristic xác định là câu hỏi kiến thức chung
        if inferred_intent == "general_knowledge_conversation":
            intent = "general_knowledge_conversation"

        parsed_slots = updated_slots.copy()
        if llm_response and intent != "get_system_metadata":
            for k, v in llm_response.get("slots", {}).items():
                if v is not None and v != "":
                    parsed_slots[k] = v
        for functional_slot in ["product_type", "print_sides", "sku", "quantity", "max_base_cost", "max_shipping_days", "selling_price", "min_margin", "shipping_address", "shipping_carrier"]:
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

        print(f"[SLOT-DEBUG] FINAL slots before execute_heuristic_flow: {json.dumps(slots, ensure_ascii=False)}")

        country_code = slots.get("country")

        if _db_slots_snapshot.get("_missing_field") == "shipping_location" and country_code and (slots.get("product_type") or slots.get("sku")):
            if current_intent in ["recommend", "compare", "calculate_margin"]:
                intent = current_intent
            elif inferred_intent in ["recommend", "compare", "calculate_margin"]:
                intent = inferred_intent
            else:
                intent = "recommend"

        if intent in ["general_chat", "general_knowledge_conversation"] and inferred_intent == "recommend" and slots.get("product_type"):
            intent = "recommend"

        if inferred_intent == "create_order" and slots.get("sku"):
            intent = "create_order"

        res = await execute_heuristic_flow(
            self,
            intent,
            slots,
            message,
            lang,
            country_code,
            history,
            previous_slots=_db_slots_snapshot,
        )
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

        should_call_generator = (
            not self.is_mock_key and
            (tool_data is not None or intent in ["general_knowledge_conversation", "capability_discovery", "get_system_metadata"] or clarification_required or confirmation_required)
        )
        if should_call_generator:
            now = datetime.datetime.now()
            months_en = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            months_vi = ["Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"]
            server_time_context = f"Current Month: {months_en[now.month - 1]} ({months_vi[now.month - 1]}), Current Year: {now.year}"

            # Kiểm tra xem danh sách sản phẩm có rỗng hay không (đối với recommend / compare)
            is_empty_state = False
            if intent in ["recommend", "compare"]:
                if not tool_data or (isinstance(tool_data, list) and len(tool_data) == 0):
                    is_empty_state = True
                elif isinstance(tool_data, dict) and "items" in tool_data and not tool_data["items"]:
                    is_empty_state = True

            resolved_input_json = json.dumps({
                "intent": intent,
                "slots": slots,
                "metadata": metadata,
                "margin_alert": margin_alert,
                "empty_state": is_empty_state
            }, ensure_ascii=False)
            calculated_products_json = json.dumps(tool_data, ensure_ascii=False)

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

                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.3,
                    timeout=15.0
                )
                add_usage_to_meta(token_meta, getattr(response, "usage", None))
                answer = response.choices[0].message.content.strip()
            except Exception:
                pass

        answer = sanitize_markdown_layout(mask_pii(answer))
        history.append({"role": "assistant", "content": answer})

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

        return {
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

    async def run_stream(self, session_id: str, message: str, history: List[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming response dưới dạng Server-Sent Events."""
        async for chunk in run_stream_logic(self, session_id, message, history):
            yield chunk
