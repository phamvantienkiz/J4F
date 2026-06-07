import re
import unicodedata
from urllib.parse import urlparse


PII_FIELDS = {
    "shipping_name",
    "shipping_address1",
    "shipping_address2",
    "shipping_email",
    "shipping_phone",
    "shipping_city",
}

FIELD_ALIASES = {
    "name": "shipping_name",
    "shipping_name": "shipping_name",
    "address1": "shipping_address1",
    "shipping_address1": "shipping_address1",
    "address2": "shipping_address2",
    "shipping_address2": "shipping_address2",
    "city": "shipping_city",
    "shipping_city": "shipping_city",
    "state": "shipping_state",
    "shipping_state": "shipping_state",
    "zip": "shipping_zip",
    "zipcode": "shipping_zip",
    "shipping_zip": "shipping_zip",
    "country": "shipping_country",
    "shipping_country": "shipping_country",
    "reference": "reference_order_id",
    "reference_order_id": "reference_order_id",
    "email": "shipping_email",
    "shipping_email": "shipping_email",
    "phone": "shipping_phone",
    "shipping_phone": "shipping_phone",
    "sku": "catalog_sku",
    "catalog_sku": "catalog_sku",
    "quantity": "quantity",
    "design_url": "design_url_front",
    "design_url_front": "design_url_front",
    "design_front": "design_url_front",
}

TOP_LEVEL_FIELDS = {
    "shipping_name",
    "shipping_address1",
    "shipping_address2",
    "shipping_city",
    "shipping_state",
    "shipping_zip",
    "shipping_country",
    "reference_order_id",
    "shipping_email",
    "shipping_phone",
}

ITEM_FIELDS = {"catalog_sku", "quantity", "design_url_front"}


_RESPONSE_TEMPLATE = {
    "intent": "create_order",
    "tool_calls": [],
    "api": None,
    "params": {},
    "data": None,
    "notes": ["Sandbox order draft only. No order is created before explicit final confirmation."],
}


def normalize_message(message: str) -> str:
    text = unicodedata.normalize("NFD", message or "")
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", text.lower()).strip()


def is_start_order_request(message: str) -> bool:
    text = normalize_message(message)
    return any(
        phrase in text
        for phrase in [
            "tao sandbox order",
            "len don sandbox",
            "tao don sandbox",
            "toi muon len don",
            "len don luon",
            "tao order",
            "create sandbox order",
            "create order",
        ]
    )


def is_cancel_order_request(message: str) -> bool:
    text = normalize_message(message)
    return any(
        phrase in text
        for phrase in [
            "cancel order draft",
            "huy draft",
            "huy don",
            "reset order draft",
            "khong muon tao nua",
            "khong muon mua nua",
            "khong tao nua",
            "khong mua nua",
            "thoi khong tao",
            "thoi khoi tao",
            "bo qua tao order",
        ]
    )


def is_final_confirmation(message: str) -> bool:
    text = normalize_message(message)
    return text in {"confirm create sandbox order", "xac nhan tao sandbox order"}


def base_response(answer: str, session_id: str | None = None, **updates):
    response = {**_RESPONSE_TEMPLATE, "answer": answer}
    response.update(updates)
    if session_id is not None:
        response["session_id"] = session_id
    return response


def recommendation_to_draft(recommendation: dict, params: dict) -> dict:
    quantity = params.get("quantity") or recommendation.get("quantity") or 1
    try:
        quantity = max(1, int(quantity))
    except (TypeError, ValueError):
        quantity = 1

    return {
        "sandbox": True,
        "shipping_country": params.get("country") or recommendation.get("shipping_country"),
        "items": [
            {
                "catalog_sku": recommendation.get("catalog_sku") or recommendation.get("sku"),
                "quantity": quantity,
            }
        ],
    }


def parse_order_fields(message: str) -> dict:
    fields: dict = {}
    item: dict = {}

    for raw_line in (message or "").splitlines():
        line = raw_line.strip()
        if not line or (":" not in line and "=" not in line):
            continue

        separator = ":" if ":" in line else "="
        key, value = line.split(separator, 1)
        normalized_key = re.sub(r"[^a-z0-9_]+", "_", key.strip().lower()).strip("_")
        mapped_key = FIELD_ALIASES.get(normalized_key)
        value = value.strip()
        if not mapped_key or not value:
            continue

        if mapped_key == "quantity":
            try:
                value = max(1, int(value))
            except ValueError:
                continue

        if mapped_key == "shipping_country":
            value = value.upper()

        if mapped_key in ITEM_FIELDS:
            item[mapped_key] = value
        elif mapped_key in TOP_LEVEL_FIELDS:
            fields[mapped_key] = value

    if item:
        fields["items"] = [item]
    if not fields:
        return {}
    fields["sandbox"] = True
    return fields


def merge_order_fields(draft: dict, fields: dict) -> dict:
    merged = {**(draft or {})}
    for key, value in fields.items():
        if key == "items":
            current_items = list(merged.get("items") or [{}])
            first_item = {**current_items[0], **value[0]}
            current_items[0] = first_item
            merged["items"] = current_items
        elif key == "sandbox":
            merged["sandbox"] = True
        else:
            merged[key] = value
    merged["sandbox"] = True
    return merged


def valid_url(value) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def missing_required_fields(draft: dict) -> list[str]:
    draft = draft or {}
    missing = []
    for field in ["shipping_name", "shipping_address1", "shipping_city", "shipping_zip", "shipping_country", "reference_order_id"]:
        if not draft.get(field):
            missing.append(field)

    country = str(draft.get("shipping_country") or "").upper()
    if country == "US" and not draft.get("shipping_state"):
        missing.append("shipping_state")

    items = draft.get("items") or []
    first_item = items[0] if items else {}
    if not first_item.get("catalog_sku"):
        missing.append("catalog_sku")
    if not first_item.get("quantity") or int(first_item.get("quantity", 0)) < 1:
        missing.append("quantity")
    if not valid_url(first_item.get("design_url_front")):
        missing.append("design_url_front")

    return missing


def build_create_order_payload(draft: dict) -> dict:
    payload = {
        "sandbox": True,
        "shipping_name": draft.get("shipping_name"),
        "shipping_address1": draft.get("shipping_address1"),
        "shipping_city": draft.get("shipping_city"),
        "shipping_zip": draft.get("shipping_zip"),
        "shipping_country": draft.get("shipping_country"),
        "reference_order_id": draft.get("reference_order_id"),
        "items": [],
    }

    for optional_field in ["shipping_address2", "shipping_state", "shipping_email", "shipping_phone"]:
        if draft.get(optional_field):
            payload[optional_field] = draft[optional_field]

    for item in draft.get("items") or []:
        payload_item = {
            "catalog_sku": item.get("catalog_sku"),
            "quantity": int(item.get("quantity") or 1),
        }
        for key, value in item.items():
            if key.startswith("design_url_") and value:
                payload_item[key] = value
        payload["items"].append(payload_item)

    return payload


def mask_zip(value):
    value = str(value or "")
    if not value:
        return None
    return f"{value[:2]}***"


def sanitize_draft_summary(draft: dict) -> dict:
    draft = draft or {}
    items = draft.get("items") or []
    first_item = items[0] if items else {}
    return {
        "sandbox": True,
        "shipping_name": "captured" if draft.get("shipping_name") else None,
        "shipping_address1": "captured" if draft.get("shipping_address1") else None,
        "shipping_city": "captured" if draft.get("shipping_city") else None,
        "shipping_state": draft.get("shipping_state"),
        "shipping_zip": mask_zip(draft.get("shipping_zip")),
        "shipping_country": draft.get("shipping_country"),
        "reference_order_id": "captured" if draft.get("reference_order_id") else None,
        "catalog_sku": first_item.get("catalog_sku"),
        "quantity": first_item.get("quantity"),
        "design_url_front": "captured" if first_item.get("design_url_front") else None,
    }


def format_missing_fields_prompt(missing: list[str]) -> str:
    fields = "\n".join(f"- {field}" for field in missing)
    return (
        "Tôi có thể tạo sandbox order draft, nhưng còn thiếu các field sau:\n"
        f"{fields}\n\n"
        "Vui lòng gửi theo dạng key-value, ví dụ:\n"
        "shipping_name: Jane Doe\n"
        "shipping_address1: 123 Main St\n"
        "shipping_city: Austin\n"
        "shipping_state: TX\n"
        "shipping_zip: 78701\n"
        "shipping_country: US\n"
        "reference_order_id: TEST-1001\n"
        "design_url_front: https://example.com/design.png"
    )


def format_confirmation_prompt(draft: dict) -> str:
    summary = sanitize_draft_summary(draft)
    lines = "\n".join(f"- {key}: {value}" for key, value in summary.items() if value is not None)
    return (
        "Draft sandbox order đã đủ thông tin. Đây là bản tóm tắt đã mask PII:\n"
        f"{lines}\n\n"
        "Nếu chắc chắn muốn tạo sandbox order, hãy gửi chính xác một trong hai câu sau:\n"
        "- confirm create sandbox order\n"
        "- xác nhận tạo sandbox order"
    )
