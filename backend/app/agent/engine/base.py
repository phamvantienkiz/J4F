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
from app.agent.engine.intent import parse_intent_and_slots, detect_language, normalize_slots
from app.agent.engine.heuristic import execute_heuristic_flow
from app.agent.engine.streaming import run_stream_logic
from app.agent.engine.guardrails import check_guardrails

class AgentEngine:
    def __init__(self):
        self.openai_api_key = settings.openai_api_key
        self.azure_api_key = settings.azure_openai_api_key
        self.llm_timeout = float(settings.llm_timeout_seconds or 15.0)

        if settings.llm_enabled and settings.llm_api_key:
            self.client = AsyncOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url or None,
            )
            self.is_mock_key = False
            self.model_name = settings.llm_model or settings.openai_model
        elif self.azure_api_key:
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
                self.client = AsyncOpenAI(
                    api_key=self.openai_api_key,
                    base_url=settings.openai_base_url or None,
                )
            else:
                self.client = None
            self.model_name = settings.openai_model
        self.trend_service = TrendService()

    def _heuristic_parse(self, message: str, slots: Dict[str, Any], current_intent: Optional[str]) -> tuple[str, Dict[str, Any]]:
        return parse_intent_and_slots(message, slots, current_intent)

    def detect_language(self, message: str) -> str:
        return detect_language(message)

    async def run(self, session_id: str, message: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Xử lý hội thoại một cách đồng bộ."""
        history = history or []

        guardrail_response = check_guardrails(message)
        if guardrail_response:
            # Lưu lịch sử chat và trả về ngay lập tức để tiết kiệm token
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
            return {
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

        inferred_intent, updated_slots = self._heuristic_parse(message, current_slots, current_intent)
        if updated_slots.get("target_market") == "EU" and updated_slots.get("country") not in ["DE", "FR"]:
            updated_slots["country"] = "DE"
        country_code = updated_slots.get("country") or "US"
        lang = self.detect_language(message)

        history.append({"role": "user", "content": message})

        llm_response = None
        if not self.is_mock_key:
            try:
                system_prompt = AGENT_SYSTEM_PROMPT + f"\n\nTrạng thái các Slots: {json.dumps(current_slots, ensure_ascii=False)}"
                messages = [{"role": "system", "content": system_prompt}]
                for msg_hist in history[-6:]:
                    messages.append({"role": msg_hist.get("role", "user"), "content": msg_hist.get("content", "")})

                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                    timeout=self.llm_timeout
                )
                llm_response = json.loads(response.choices[0].message.content)
            except Exception:
                llm_response = None

        intent = llm_response.get("intent", inferred_intent) if llm_response else inferred_intent

        # Ép buộc định tuyến sang general_knowledge_conversation nếu heuristic xác định là câu hỏi kiến thức chung
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

        res = await execute_heuristic_flow(self, intent, slots, message, lang, country_code)
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

        should_call_generator = (
            not self.is_mock_key and
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

                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.3,
                    timeout=self.llm_timeout
                )
                answer = response.choices[0].message.content.strip()
            except Exception:
                pass

        answer = mask_pii(answer)
        history.append({"role": "assistant", "content": answer})

        with Session(db.engine) as session:
            db_session = session.exec(select(ChatSession).where(ChatSession.session_id == session_id)).first()
            if db_session:
                db_session.history = history
                db_session.slots = slots
                db_session.current_intent = intent
                db_session.updated_at = datetime.datetime.utcnow()
                session.add(db_session)
                session.commit()

        return {
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

    async def run_stream(self, session_id: str, message: str, history: List[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming response dưới dạng Server-Sent Events."""
        async for chunk in run_stream_logic(self, session_id, message, history):
            yield chunk
