from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.scripts.e2e_regression_cases import CASES, E2ECase

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
REPORT_DIR = Path("app/tests/reports")
REPORT_JSON = REPORT_DIR / "e2e_regression_report.json"
REPORT_MD = REPORT_DIR / "e2e_regression_report.md"
HTTP_SSE_UNAVAILABLE = False


@dataclass
class SSEStreamReport:
    query: str
    tokens: List[str] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    raw_events: List[Dict[str, Any]] = field(default_factory=list)
    final_payload: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    raw_text_length: int = 0

    @property
    def token_text(self) -> str:
        return "".join(self.tokens)

    @property
    def items(self) -> List[Dict[str, Any]]:
        if not self.final_payload:
            return []
        data = self.final_payload.get("data") or {}
        items = data.get("items")
        return items if isinstance(items, list) else []

    @property
    def params(self) -> Dict[str, Any]:
        if not self.final_payload:
            return {}
        params = self.final_payload.get("params")
        return params if isinstance(params, dict) else {}

    @property
    def data(self) -> Dict[str, Any]:
        if not self.final_payload:
            return {}
        data = self.final_payload.get("data")
        return data if isinstance(data, dict) else {}

    @property
    def answer(self) -> str:
        if not self.final_payload:
            return self.token_text
        answer = self.final_payload.get("answer") or ""
        return str(answer) if answer else self.token_text

    @property
    def intent(self) -> Optional[str]:
        if not self.final_payload:
            return None
        intent = self.final_payload.get("intent")
        return str(intent) if intent is not None else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "token_chars": len(self.token_text),
            "step_count": len(self.steps),
            "tool_call_count": len(self.tool_calls),
            "raw_event_count": len(self.raw_events),
            "has_final_payload": self.final_payload is not None,
            "intent": self.intent,
            "item_count": len(self.items),
            "errors": self.errors,
            "raw_text_length": self.raw_text_length,
            "params": self.params,
            "items_preview": [summarize_item(item) for item in self.items[:5]],
        }


@dataclass
class CaseResult:
    case_id: str
    status: str
    query: str
    stream: SSEStreamReport
    reason: str = ""
    elapsed_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "query": self.query,
            "reason": self.reason,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "stream": self.stream.to_dict(),
        }


@dataclass
class ValidatedCaseResult:
    case_id: str
    status: str
    reason: str
    turn_results: List[CaseResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "reason": self.reason,
            "turn_results": [result.to_dict() for result in self.turn_results],
        }


def normalize_text(value: Any) -> str:
    return str(value or "").casefold().strip()


def recursive_values(value: Any) -> List[Any]:
    if isinstance(value, dict):
        values: List[Any] = []
        for item in value.values():
            values.extend(recursive_values(item))
        return values
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(recursive_values(item))
        return values
    return [value]


def recursive_text(value: Any) -> str:
    return normalize_text(" ".join(str(v) for v in recursive_values(value) if v is not None))


def recursive_has_key(value: Any, key_name: str) -> bool:
    if isinstance(value, dict):
        return any(normalize_text(k) == normalize_text(key_name) or recursive_has_key(v, key_name) for k, v in value.items())
    if isinstance(value, list):
        return any(recursive_has_key(item, key_name) for item in value)
    return False


def item_text(item: Dict[str, Any]) -> str:
    fields = [
        item.get("sku"),
        item.get("product_id"),
        item.get("id"),
        item.get("product_name"),
        item.get("display_name"),
        item.get("name"),
        item.get("category"),
        item.get("product_category"),
        item.get("color"),
        item.get("size"),
        item.get("partner_name"),
        item.get("location_name"),
        item.get("carrier"),
        item.get("zone_id"),
        item.get("zone_name"),
        item.get("country_code"),
        item.get("first_item_fee"),
        item.get("additional_item_fee"),
        item.get("shipping_fee"),
        item.get("total_shipping"),
        item.get("delivery_time"),
    ]
    return normalize_text(" ".join(str(field) for field in fields if field is not None))


def summarize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sku": item.get("sku"),
        "product_id": item.get("product_id") or item.get("id"),
        "name": item.get("product_name") or item.get("display_name") or item.get("name"),
        "category": item.get("category") or item.get("product_category"),
        "partner_name": item.get("partner_name"),
        "carrier": item.get("carrier"),
        "zone_id": item.get("zone_id"),
        "base_cost": item.get("base_cost"),
        "first_item_fee": item.get("first_item_fee"),
        "additional_item_fee": item.get("additional_item_fee"),
        "shipping_fee": item.get("shipping_fee"),
        "total_shipping": item.get("total_shipping"),
        "delivery_time": item.get("delivery_time"),
        "margin_percent": item.get("margin_percent"),
    }


def parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def parse_sse_stream(raw_text: str, query: str) -> SSEStreamReport:
    report = SSEStreamReport(query=query, raw_text_length=len(raw_text or ""))
    if not raw_text:
        report.errors.append("Empty SSE response")
        return report

    for block in raw_text.split("\n\n"):
        line = block.strip()
        if not line.startswith("data: "):
            continue
        try:
            payload = json.loads(line[6:])
        except json.JSONDecodeError as exc:
            report.errors.append(f"JSON decode error: {exc} in block: {line[:120]}")
            continue
        if not isinstance(payload, dict):
            report.errors.append(f"Non-object SSE payload: {payload!r}")
            continue

        report.raw_events.append(payload)
        if "token" in payload:
            report.tokens.append(str(payload.get("token") or ""))
        elif "step" in payload and "message" in payload:
            report.steps.append(payload)
        elif "tool_call" in payload:
            report.tool_calls.append(payload)
        elif isinstance(payload.get("session_id"), str):
            report.final_payload = payload

    return report


async def fetch_agent_chat_in_process(query: str, session_id: str) -> str:
    from app.agent.engine import AgentEngine

    engine = AgentEngine()
    chunks: List[str] = []
    async for event in engine.run_stream(session_id, query, []):
        chunks.append(f"data: {json.dumps(event, ensure_ascii=False)}\n\n")
    return "".join(chunks)


def fetch_agent_chat_sse(query: str, session_id: str, timeout: int = 90) -> str:
    global HTTP_SSE_UNAVAILABLE
    if not HTTP_SSE_UNAVAILABLE:
        body = json.dumps({"message": query, "history": [], "session_id": session_id}).encode("utf-8")
        request = urllib.request.Request(
            f"{BACKEND_URL}/agent/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise AssertionError(f"/agent/chat returned HTTP {response.status} for query {query!r}")
                chunks: List[bytes] = []
                try:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        chunks.append(chunk)
                except Exception as exc:
                    partial = getattr(exc, "partial", b"") or b""
                    if partial:
                        chunks.append(partial)
                    safe_query = query.encode("unicode_escape").decode("ascii")
                    print(f"[WARN] Stream read interrupted for {safe_query!r}: {exc}; using {len(chunks)} chunks")
                raw_bytes = b"".join(chunks)
                if raw_bytes:
                    raw_text = raw_bytes.decode("utf-8", errors="replace")
                    if '"session_id"' in raw_text:
                        return raw_text
                    HTTP_SSE_UNAVAILABLE = True
                    safe_query = query.encode("unicode_escape").decode("ascii")
                    print(f"[WARN] HTTP SSE returned no final payload for {safe_query!r}; falling back in-process")
        except (TimeoutError, OSError, urllib.error.URLError) as exc:
            HTTP_SSE_UNAVAILABLE = True
            safe_query = query.encode("unicode_escape").decode("ascii")
            print(f"[WARN] HTTP SSE unavailable for {safe_query!r}: {exc}; falling back in-process")

    result: Dict[str, Any] = {}

    def run_fallback() -> None:
        try:
            result["text"] = asyncio.run(fetch_agent_chat_in_process(query, session_id))
        except Exception as exc:
            result["error"] = exc

    thread = threading.Thread(target=run_fallback)
    thread.start()
    thread.join(timeout + 10)
    if thread.is_alive():
        raise TimeoutError(f"In-process fallback timed out for query {query!r}")
    if "error" in result:
        raise result["error"]
    return str(result.get("text") or "")


def has_graceful_empty_response(stream: SSEStreamReport) -> bool:
    answer = normalize_text(stream.answer)
    clarification_required = bool(stream.data.get("clarification_required"))
    markers = (
        "không tìm thấy",
        "không có dữ liệu",
        "not found",
        "no data",
        "unsupported",
        "không hỗ trợ",
        "clarify",
        "vui lòng",
        "please provide",
        "không đáp ứng",
        "rủi ro",
    )
    return clarification_required or any(marker in answer for marker in markers)


def is_clarification(stream: SSEStreamReport) -> bool:
    return bool(stream.data.get("clarification_required")) or any(
        marker in normalize_text(stream.answer)
        for marker in ("clarify", "please choose", "vui lòng chọn", "cần làm rõ", "bạn muốn", "which canvas")
    )


def stream_payload_text(stream: SSEStreamReport) -> str:
    payload_text = recursive_text(stream.final_payload or {})
    return normalize_text(" ".join([stream.answer, payload_text] + [item_text(item) for item in stream.items]))


def validate_items(case: E2ECase, items: List[Dict[str, Any]], stream: SSEStreamReport) -> str:
    normalized_searchable = stream_payload_text(stream)

    if case.allowed_categories:
        allowed = {normalize_text(category) for category in case.allowed_categories}
        top_items = items[: min(5, len(items))]
        for item in top_items:
            category = normalize_text(item.get("category") or item.get("product_category"))
            text = item_text(item)
            if category and category not in allowed:
                return f"Item {summarize_item(item)} has category {category!r}, expected one of {sorted(allowed)}"
            if not category and not any(allowed_category in text for allowed_category in allowed):
                return f"Item {summarize_item(item)} has no category evidence for {sorted(allowed)}"

    for term in case.required_terms:
        if normalize_text(term) not in normalized_searchable:
            return f"Required term {term!r} not found in answer/items"

    if case.required_any_terms and not any(normalize_text(term) in normalized_searchable for term in case.required_any_terms):
        return f"None of required_any_terms {list(case.required_any_terms)!r} found in answer/items"

    for term in case.forbidden_terms:
        if normalize_text(term) in normalized_searchable:
            return f"Forbidden term {term!r} found in answer/items"

    if case.required_color:
        expected_color = normalize_text(case.required_color)
        if not any(expected_color == normalize_text(item.get("color")) for item in items):
            return f"Required color {case.required_color!r} not found in items"

    if case.required_size:
        expected_size = normalize_text(case.required_size)
        if not any(expected_size == normalize_text(item.get("size")) for item in items):
            return f"Required size {case.required_size!r} not found in items"

    if case.max_base_cost is not None:
        costs = [parse_float(item.get("base_cost")) for item in items]
        valid_costs = [cost for cost in costs if cost is not None]
        if not valid_costs:
            return f"No parseable base_cost values for max_base_cost {case.max_base_cost}"
        if min(valid_costs) > case.max_base_cost:
            return f"No item with base_cost <= {case.max_base_cost}; costs={valid_costs[:10]}"

    if case.min_base_cost is not None:
        costs = [parse_float(item.get("base_cost")) for item in items]
        valid_costs = [cost for cost in costs if cost is not None]
        if not valid_costs:
            return f"No parseable base_cost values for min_base_cost {case.min_base_cost}"
        if max(valid_costs) < case.min_base_cost:
            return f"No item with base_cost >= {case.min_base_cost}; costs={valid_costs[:10]}"

    return ""


def validate_turn_terms(case: E2ECase, turn_results: List[CaseResult]) -> str:
    if not case.required_turn_any_terms:
        return ""
    if len(turn_results) < len(case.required_turn_any_terms):
        return f"Expected {len(case.required_turn_any_terms)} turns, got {len(turn_results)}"
    for index, terms in enumerate(case.required_turn_any_terms):
        text = stream_payload_text(turn_results[index].stream)
        if not any(normalize_text(term) in text for term in terms):
            return f"Turn {index + 1} missing expected context terms {list(terms)!r}"
    return ""


def validate_state_transition(case: E2ECase, turn_results: List[CaseResult]) -> str:
    turn_failure = validate_turn_terms(case, turn_results)
    if turn_failure:
        return turn_failure

    if not case.expected_country_terms and not case.require_zone_mapping:
        return ""

    observed_payload = [result.stream.final_payload for result in turn_results if result.stream.final_payload]
    observed = " ".join(
        json.dumps(payload, ensure_ascii=False) + " " + result.stream.answer
        for payload, result in zip(observed_payload, [r for r in turn_results if r.stream.final_payload])
    )
    normalized = normalize_text(observed)

    if case.expected_country_terms and not any(normalize_text(term) in normalized for term in case.expected_country_terms):
        return f"Expected country/location evidence {list(case.expected_country_terms)} not found in params/answer"

    if case.require_zone_mapping:
        has_zone_id = any(recursive_has_key(payload, "zone_id") for payload in observed_payload)
        if not has_zone_id and "zone_id" not in normalized and "zone id" not in normalized:
            return "Missing zone_id evidence; shipping lookup must map location through shipping_zones.id before shipping_fees"

    return ""


def validate_margin(case: E2ECase, stream: SSEStreamReport) -> str:
    if not case.require_margin_alert:
        return ""
    text = stream_payload_text(stream)
    if stream.data.get("margin_alert") is True:
        return ""
    if any(marker in text for marker in ("margin_alert", "không đạt", "không thể đạt", "below margin", "cannot reach")):
        return ""
    return "Expected data.margin_alert=true or explicit low-margin explanation"


def validate_carrier_partner(case: E2ECase, stream: SSEStreamReport) -> str:
    if not case.require_carrier_partner:
        return ""
    payload = stream.final_payload or {}
    text = stream_payload_text(stream)
    has_carrier = recursive_has_key(payload, "carrier") or any(normalize_text(term) in text for term in case.expected_carrier_terms)
    has_partner = recursive_has_key(payload, "partner_name") or "partner" in text or "xưởng" in text
    if not has_carrier:
        return "Missing carrier evidence for shipping fee selection"
    if not has_partner:
        return "Missing partner_name/factory evidence for carrier-partner shipping fee selection"
    return ""


def extract_candidate_options(value: Any) -> List[Dict[str, Any]]:
    options: List[Dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if normalize_text(key) in {"candidate_shipping_options", "shipping_options", "carrier_options"} and isinstance(item, list):
                options.extend(option for option in item if isinstance(option, dict))
            else:
                options.extend(extract_candidate_options(item))
    elif isinstance(value, list):
        for item in value:
            options.extend(extract_candidate_options(item))
    return options


def validate_cheapest_shipping(case: E2ECase, stream: SSEStreamReport) -> str:
    if not case.require_cheapest_shipping:
        return ""
    payload = stream.final_payload or {}
    options = extract_candidate_options(payload)
    if not options:
        return "Missing candidate shipping options; cannot prove cheapest carrier/partner was selected"
    option_costs = [parse_float(option.get("first_item_fee")) for option in options]
    valid_costs = [cost for cost in option_costs if cost is not None]
    if not valid_costs:
        return "Candidate shipping options do not include first_item_fee values"
    selected_candidates = [option for option in options if option.get("selected") is True or option.get("is_selected") is True]
    selected = selected_candidates[0] if selected_candidates else options[0]
    selected_fee = parse_float(selected.get("first_item_fee"))
    if selected_fee is None:
        return "Selected shipping option has no first_item_fee"
    if selected_fee > min(valid_costs) + 0.001:
        return f"Selected first_item_fee {selected_fee} is not cheapest available {min(valid_costs)}"
    return ""


def validate_shipping_formula(case: E2ECase, stream: SSEStreamReport) -> str:
    if not case.require_shipping_formula:
        return ""
    quantity = case.expected_quantity
    if quantity is None:
        return "Missing expected_quantity for shipping formula validation"
    candidates = stream.items or [stream.data]
    for item in candidates:
        first_fee = parse_float(item.get("first_item_fee"))
        additional_fee = parse_float(item.get("additional_item_fee"))
        total = parse_float(item.get("total_shipping") or item.get("shipping_total") or item.get("shipping_fee_total"))
        item_quantity = item.get("quantity") or item.get("qty") or quantity
        try:
            item_quantity = int(item_quantity)
        except (TypeError, ValueError):
            item_quantity = quantity
        if first_fee is None or additional_fee is None or total is None:
            continue
        expected = first_fee + (item_quantity - 1) * additional_fee
        if abs(total - expected) > 0.01:
            return f"Shipping formula mismatch: expected {expected}, got {total}"
        return ""
    return "Missing first_item_fee/additional_item_fee/total_shipping evidence for multi-item shipping formula"


def parse_delivery_max_days(value: str) -> Optional[int]:
    numbers = [int(match) for match in re.findall(r"\d+", value)]
    return max(numbers) if numbers else None


def validate_delivery_time(case: E2ECase, stream: SSEStreamReport) -> str:
    if not case.require_delivery_time:
        return ""
    payload = stream.final_payload or {}
    text = stream_payload_text(stream)
    if not recursive_has_key(payload, "delivery_time") and "delivery_time" not in text and "business days" not in text and "ngày" not in text:
        return "Missing delivery_time evidence from shipping_fees"
    if case.max_delivery_days is None:
        return ""
    max_days = [parse_delivery_max_days(str(value)) for value in recursive_values(payload)]
    max_days = [days for days in max_days if days is not None]
    has_fast_enough = any(days <= case.max_delivery_days for days in max_days)
    if not has_fast_enough and not is_clarification(stream):
        return f"No delivery_time <= {case.max_delivery_days} days and clarification_required was not set"
    return ""


def validate_logistics(case: E2ECase, stream: SSEStreamReport) -> str:
    for check in (
        validate_carrier_partner,
        validate_cheapest_shipping,
        validate_shipping_formula,
        validate_delivery_time,
    ):
        failure = check(case, stream)
        if failure:
            return failure
    return ""


def validate_case_result(case: E2ECase, turn_results: List[CaseResult]) -> ValidatedCaseResult:
    if not turn_results:
        return ValidatedCaseResult(case.case_id, "FAIL", "No turn results", [])

    failed_turn = next((result for result in turn_results if result.status == "FAIL"), None)
    if failed_turn:
        return ValidatedCaseResult(case.case_id, "FAIL", failed_turn.reason, turn_results)

    last = turn_results[-1].stream
    if case.require_final_payload and last.final_payload is None:
        return ValidatedCaseResult(case.case_id, "FAIL", "No final payload in SSE stream", turn_results)

    if last.final_payload is None:
        return ValidatedCaseResult(case.case_id, "PASS", "No final payload required", turn_results)

    if not isinstance(last.data, dict):
        return ValidatedCaseResult(case.case_id, "FAIL", "Final payload data is not an object", turn_results)

    if case.require_clarification and not is_clarification(last):
        return ValidatedCaseResult(case.case_id, "FAIL", "Expected clarification_required=true for ambiguous/SLA-risk query", turn_results)

    if case.expected_missing_field and last.data.get("missing_field") != case.expected_missing_field:
        return ValidatedCaseResult(case.case_id, "FAIL", f"Expected missing_field={case.expected_missing_field!r}, got {last.data.get('missing_field')!r}", turn_results)

    if case.expected_missing_field == "shipping_location":
        custom_payload = last.data.get("custom_payload") or {}
        suggested_countries = custom_payload.get("suggested_countries")
        if not isinstance(suggested_countries, list) or not suggested_countries:
            return ValidatedCaseResult(case.case_id, "FAIL", "Expected custom_payload.suggested_countries to be a non-empty list", turn_results)
        first_country = suggested_countries[0]
        if not isinstance(first_country, dict) or not all(isinstance(first_country.get(key), str) and first_country.get(key) for key in ["code", "name", "flag"]):
            return ValidatedCaseResult(case.case_id, "FAIL", "Expected custom_payload.suggested_countries items to include code, name, and flag", turn_results)

    items = last.items
    if case.max_items is not None and len(items) > case.max_items:
        return ValidatedCaseResult(case.case_id, "FAIL", f"Expected at most {case.max_items} items, got {len(items)}", turn_results)

    if case.require_partner_fallback and len(items) == 0:
        return ValidatedCaseResult(case.case_id, "FAIL", "Partner fallback failed: expected alternate partner instead of empty items", turn_results)

    if len(items) < case.min_items:
        if case.require_graceful_empty and has_graceful_empty_response(last):
            return ValidatedCaseResult(case.case_id, "PASS", "Graceful empty response accepted", turn_results)
        return ValidatedCaseResult(case.case_id, "FAIL", f"Expected at least {case.min_items} items, got {len(items)}", turn_results)

    margin_failure = validate_margin(case, last)
    if margin_failure:
        return ValidatedCaseResult(case.case_id, "FAIL", margin_failure, turn_results)

    if items:
        item_failure = validate_items(case, items, last)
        if item_failure:
            return ValidatedCaseResult(case.case_id, "FAIL", item_failure, turn_results)
    elif case.required_any_terms and not any(normalize_text(term) in stream_payload_text(last) for term in case.required_any_terms):
        return ValidatedCaseResult(case.case_id, "FAIL", f"None of required_any_terms {list(case.required_any_terms)!r} found in empty response", turn_results)

    state_failure = validate_state_transition(case, turn_results)
    if state_failure:
        return ValidatedCaseResult(case.case_id, "FAIL", state_failure, turn_results)

    logistics_failure = validate_logistics(case, last)
    if logistics_failure:
        return ValidatedCaseResult(case.case_id, "FAIL", logistics_failure, turn_results)

    return ValidatedCaseResult(case.case_id, "PASS", "All validations passed", turn_results)


def run_api_case(case: E2ECase) -> ValidatedCaseResult:
    session_id = f"e2e-{case.case_id.lower()}-{uuid.uuid4().hex[:6]}"
    turn_results: List[CaseResult] = []
    for query in case.turns:
        started = time.perf_counter()
        try:
            raw = fetch_agent_chat_sse(query, session_id=session_id)
            stream = parse_sse_stream(raw, query)
            elapsed = time.perf_counter() - started
            if stream.errors and stream.final_payload is None:
                turn_results.append(
                    CaseResult(
                        case_id=case.case_id,
                        status="FAIL",
                        query=query,
                        stream=stream,
                        reason="SSE parse errors without final payload: " + "; ".join(stream.errors[:3]),
                        elapsed_seconds=elapsed,
                    )
                )
            else:
                turn_results.append(CaseResult(case.case_id, "PASS", query, stream, elapsed_seconds=elapsed))
        except Exception as exc:
            elapsed = time.perf_counter() - started
            stream = SSEStreamReport(query=query)
            stream.errors.append(repr(exc))
            turn_results.append(CaseResult(case.case_id, "FAIL", query, stream, f"Execution error: {exc}", elapsed))
            break
    return validate_case_result(case, turn_results)


def run_ui_turns_on_page(case: E2ECase, page: Any) -> ValidatedCaseResult:
    turn_results: List[CaseResult] = []
    for query in case.turns:
        started = time.perf_counter()
        stream = SSEStreamReport(query=query)
        try:
            before_count = captured_response_count(page)
            before_messages = page.locator(".message").count()
            submit_chat_message(page, query)
            page.wait_for_function("count => window.__agentResponses && window.__agentResponses.length > count", arg=before_count, timeout=120000)
            raw = captured_response_text(page, before_count)
            stream = parse_sse_stream(raw, query)
            page.wait_for_function("count => document.querySelectorAll('.message').length >= count + 2", arg=before_messages, timeout=30000)
            page.wait_for_function("() => !document.querySelector('.thought-container.streaming, .skeleton-card')", timeout=30000)
            page.wait_for_function("() => !document.querySelector('.send-icon-button')?.disabled", timeout=30000)
            if case.group == "ui":
                page.wait_for_selector(".result-box", timeout=90000)
                page.wait_for_selector(".assistant-prose", timeout=30000)
            else:
                page.wait_for_selector(".assistant-prose, .result-box, .country-chips", timeout=30000)
            elapsed = time.perf_counter() - started
            turn_results.append(CaseResult(case.case_id, "PASS", query, stream, elapsed_seconds=elapsed))
        except Exception as exc:
            elapsed = time.perf_counter() - started
            stream.errors.append(repr(exc))
            turn_results.append(CaseResult(case.case_id, "FAIL", query, stream, f"UI execution error: {exc}", elapsed))
            break
    if case.group == "ui" and turn_results and not any(result.status == "FAIL" for result in turn_results):
        layout_error = inspect_layout(page)
        if layout_error:
            last = turn_results[-1]
            turn_results[-1] = CaseResult(case.case_id, "FAIL", last.query, last.stream, layout_error, last.elapsed_seconds)
    return validate_case_result(case, turn_results)


def run_ui_case(case: E2ECase) -> ValidatedCaseResult:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        stream = SSEStreamReport(query=case.turns[0])
        stream.errors.append(f"Playwright unavailable: {exc}")
        result = CaseResult(case.case_id, "FAIL", case.turns[0], stream, f"Playwright unavailable: {exc}")
        return ValidatedCaseResult(case.case_id, "FAIL", result.reason, [result])

    viewport_results: List[ValidatedCaseResult] = []
    viewports = case.ui_viewports or ({"width": 1440, "height": 1000},)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            for viewport in viewports:
                page = browser.new_page(viewport=viewport)
                try:
                    install_sse_capture(page)
                    page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60000)
                    ensure_chat_workspace(page)
                    viewport_results.append(run_ui_turns_on_page(case, page))
                finally:
                    page.close()
        finally:
            browser.close()

    failed = next((result for result in viewport_results if result.status == "FAIL"), None)
    if failed:
        return failed
    return viewport_results[-1] if viewport_results else ValidatedCaseResult(case.case_id, "FAIL", "No UI viewport results", [])


def run_ui_cases_continuous(cases: Sequence[E2ECase]) -> List[ValidatedCaseResult]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        results: List[ValidatedCaseResult] = []
        for case in cases:
            stream = SSEStreamReport(query=case.turns[0])
            stream.errors.append(f"Playwright unavailable: {exc}")
            result = CaseResult(case.case_id, "FAIL", case.turns[0], stream, f"Playwright unavailable: {exc}")
            results.append(ValidatedCaseResult(case.case_id, "FAIL", result.reason, [result]))
        return results

    results: List[ValidatedCaseResult] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            for case in cases:
                context = browser.new_context(viewport={"width": 1440, "height": 1000})
                page = context.new_page()
                try:
                    install_sse_capture(page)
                    page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=60000)
                    ensure_chat_workspace(page)
                    result = run_ui_turns_on_page(case, page)
                    if result.status == "FAIL":
                        save_ui_failure_screenshot(page, case.case_id)
                        result = attach_ui_state_evidence(page, result)
                    print(f"[{result.status}] {case.case_id}: {result.reason}")
                    results.append(result)
                finally:
                    context.close()
        finally:
            browser.close()
    return results


def install_sse_capture(page: Any) -> None:
    page.add_init_script(
        """
        (() => {
          const originalFetch = window.fetch.bind(window);
          window.__agentResponses = [];
          window.fetch = async (...args) => {
            const response = await originalFetch(...args);
            const rawUrl = args[0] && (args[0].url || args[0]);
            const url = String(rawUrl || '');
            if (url.includes('/agent/chat')) {
              const cloned = response.clone();
              cloned.text()
                .then(text => window.__agentResponses.push({ url, text }))
                .catch(error => window.__agentResponses.push({ url, text: '', error: String(error) }));
            }
            return response;
          };
        })();
        """
    )


def captured_response_count(page: Any) -> int:
    return int(page.evaluate("window.__agentResponses ? window.__agentResponses.length : 0"))


def captured_response_text(page: Any, index: int) -> str:
    return str(page.evaluate("index => window.__agentResponses[index]?.text || ''", index) or "")


def save_ui_failure_screenshot(page: Any, case_id: str) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(REPORT_DIR / f"{case_id.lower()}-ui-failure.png"), full_page=True)


def attach_ui_state_evidence(page: Any, result: ValidatedCaseResult) -> ValidatedCaseResult:
    state = page.evaluate(
        """
        () => ({
          activeHistory: document.querySelector('.history-item.active span')?.textContent?.trim() || '',
          inputPlaceholder: document.querySelector('.chat-input textarea')?.getAttribute('placeholder') || '',
          messageCount: document.querySelectorAll('.message').length,
          inspectorTitle: document.querySelector('.checkout-product-info h2')?.textContent?.trim() || '',
          inspectorSku: document.querySelector('.inspector-section small')?.textContent?.trim() || '',
          firstResultTitle: document.querySelector('.result-box h3')?.textContent?.trim() || '',
          assistantText: document.querySelector('.message.assistant:last-of-type .assistant-prose')?.textContent?.trim().slice(0, 180) || '',
        })
        """
    )
    reason = f"{result.reason} | UI state: {json.dumps(state, ensure_ascii=False)}"
    return ValidatedCaseResult(result.case_id, result.status, reason, result.turn_results)


def ensure_chat_workspace(page: Any) -> None:
    if page.locator(".login-form").count() > 0:
        page.locator(".login-form button[type='submit']").click()
    page.wait_for_selector(".chat-input textarea, input[type='text'], [contenteditable='true']", timeout=10000)


def start_new_chat(page: Any) -> None:
    page.wait_for_function("() => !document.querySelector('.send-icon-button')?.disabled", timeout=30000)
    page.locator(".history-sidebar .section-heading button").click()
    page.wait_for_function("() => document.querySelectorAll('.message').length === 0", timeout=10000)
    page.wait_for_selector(".order-empty", timeout=10000)
    page.wait_for_selector(".chat-input textarea, input[type='text'], [contenteditable='true']", timeout=10000)


def submit_chat_message(page: Any, query: str) -> None:
    selectors = ["textarea", "input[type='text']", "[contenteditable='true']"]
    textbox = None
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            textbox = locator.last
            break
    if textbox is None:
        raise AssertionError("No chat textbox found")
    textbox.fill(query)
    button = page.locator(".chat-input .send-icon-button, .chat-input button[type='submit'], .chat-input button:has-text('Send'), .chat-input button:has-text('Gửi')").last
    if button.count() == 0:
        raise AssertionError("No send button found")
    button.click()


def inspect_layout(page: Any) -> str:
    return page.evaluate(
        """
        () => {
          const resultBox = document.querySelector('.result-box');
          const bubble = resultBox?.closest('.message-bubble') || resultBox?.parentElement;
          const comparison = document.querySelector('.mini-comparison');
          const rows = Array.from(document.querySelectorAll('.mini-row'));
          const prose = document.querySelector('.assistant-prose');
          if (!resultBox) return 'Missing .result-box';
          if (!bubble) return 'Missing containing chat bubble';
          if (!comparison) return 'Missing .mini-comparison';
          if (!prose || prose.textContent.trim().length === 0) return 'Missing assistant prose text';
          if (rows.length < 2) return 'Expected header and at least one .mini-row data row';
          const resultRect = resultBox.getBoundingClientRect();
          const bubbleRect = bubble.getBoundingClientRect();
          if (resultRect.left < bubbleRect.left - 2 || resultRect.right > bubbleRect.right + 2) {
            return `.result-box overflows bubble: result=${resultRect.left},${resultRect.right} bubble=${bubbleRect.left},${bubbleRect.right}`;
          }
          const headerCells = Array.from(rows[0].children);
          if (headerCells.length !== 12) return `Expected 12 header columns, got ${headerCells.length}`;
          const dataCells = Array.from(rows[1].children);
          if (dataCells.length !== 12) return `Expected 12 data columns, got ${dataCells.length}`;
          if (comparison.scrollWidth <= 0 || comparison.clientWidth <= 0) return 'Invalid .mini-comparison dimensions';
          const rowRect = rows[1].getBoundingClientRect();
          if (rowRect.height <= 0) return 'Data row has zero height';
          return '';
        }
        """
    )


def run_cases(selected_groups: Sequence[str], selected_ids: Sequence[str], include_ui: bool, all_ui: bool = False) -> List[ValidatedCaseResult]:
    selected_group_set = {group for group in selected_groups if group}
    selected_id_set = {case_id for case_id in selected_ids if case_id}
    selected_cases = [
        case for case in CASES
        if (not selected_group_set or case.group in selected_group_set)
        and (not selected_id_set or case.case_id in selected_id_set)
    ]
    if all_ui:
        active_cases = [case for case in selected_cases if len(case.turns) > 1]
        return run_ui_cases_continuous(active_cases)

    results: List[ValidatedCaseResult] = []
    for case in selected_cases:
        if case.group == "ui":
            if include_ui:
                result = run_ui_case(case)
            else:
                result = ValidatedCaseResult(case.case_id, "SKIP", "UI case skipped; pass --include-ui to run", [])
        else:
            result = run_api_case(case)
        print(f"[{result.status}] {case.case_id}: {result.reason}")
        results.append(result)
    return results


def write_reports(results: List[ValidatedCaseResult]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for result in results if result.status == "PASS")
    failed = sum(1 for result in results if result.status == "FAIL")
    skipped = sum(1 for result in results if result.status == "SKIP")
    failures = [
        {
            "case_id": result.case_id,
            "phase": "validation",
            "reason": result.reason,
            "evidence": result.turn_results[-1].stream.to_dict() if result.turn_results else {},
        }
        for result in results
        if result.status == "FAIL"
    ]
    payload = {
        "summary": {"total": len(results), "passed": passed, "failed": failed, "skipped": skipped},
        "failures": failures,
        "results": [result.to_dict() for result in results],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# E2E Regression Report",
        "",
        f"- Total: {len(results)}",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        f"- Skipped: {skipped}",
        "",
        "| Case | Status | Reason |",
        "|---|---|---|",
    ]
    for result in results:
        reason = result.reason.replace("|", "\\|")
        lines.append(f"| {result.case_id} | {result.status} | {reason} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_csv_arg(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the 25-case focused E2E regression suite.")
    parser.add_argument("--group", default="", help="Comma-separated groups: api_sse,regression,taxonomy,logistics,ui")
    parser.add_argument("--case", default="", help="Comma-separated case IDs, for example REG-01,API-02")
    parser.add_argument("--include-ui", action="store_true", help="Run UI Playwright cases instead of skipping them")
    parser.add_argument("--all-ui", action="store_true", help="Run every selected case through the visible Playwright UI")
    args = parser.parse_args(argv)

    results = run_cases(parse_csv_arg(args.group), parse_csv_arg(args.case), include_ui=args.include_ui, all_ui=args.all_ui)
    write_reports(results)
    failures = [result for result in results if result.status == "FAIL"]
    print(f"Report written to {REPORT_JSON} and {REPORT_MD}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
