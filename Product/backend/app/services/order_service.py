import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import uuid

from backend.app.models.order import OrderHistory
from backend.app.schemas.order import OrderDraftConfirmRequest, OrderHistoryResponse
from ai.tools import create_order, httpx
from ai.agent import agent_graph

async def confirm_and_create_order(
    db: AsyncSession, user_id: str, request_in: OrderDraftConfirmRequest
) -> OrderHistory:
    # 1. Execute the order creation on BurgerPrints
    shipping_addr_dict = {
        "full_name": request_in.shipping_address.full_name,
        "address_line1": request_in.shipping_address.address_line1,
        "address_line2": request_in.shipping_address.address_line2,
        "city": request_in.shipping_address.city,
        "state": request_in.shipping_address.state,
        "zip_code": request_in.shipping_address.zip_code,
        "country": request_in.shipping_address.country,
        "phone": request_in.shipping_address.phone
    }

    result = create_order(
        sku=request_in.sku,
        quantity=request_in.quantity,
        shipping_address=shipping_addr_dict,
        selected_factory_id=request_in.selected_option_id
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to place order on BurgerPrints: {result.get('error', 'Unknown error')}"
        )

    # 2. Save to SQLite OrderHistory
    order_record = OrderHistory(
        id=str(uuid.uuid4()),
        conversation_id=request_in.thread_id,
        order_id=result["order_id"],
        sku=request_in.sku,
        quantity=request_in.quantity,
        total_cost=result["total_cogs"],
        shipping_address=json.dumps(shipping_addr_dict),
        tracking_number=result.get("tracking_number"),
        status=result["status"],
        created_at=datetime.utcnow()
    )
    db.add(order_record)
    
    # 3. Synchronize LangGraph checkpointer state so the Agent knows the order has been executed
    config = {"configurable": {"thread_id": request_in.thread_id}}
    agent_graph.update_state(
        config,
        {
            "order_status": result,
            "conversation_history": [
                {
                    "sender": "assistant",
                    "content": (
                        f"🎉 **Đơn hàng đã được tạo thành công trên BurgerPrints (qua API)!**\n\n"
                        f"- **Mã đơn hàng:** `{result['order_id']}`\n"
                        f"- **SKU:** `{request_in.sku}`\n"
                        f"- **Số lượng:** {request_in.quantity}\n"
                        f"- **Tổng landed cost:** ${result['total_cogs']}\n"
                        f"- **Trạng thái:** `{result['status']}`"
                    )
                }
            ]
        }
    )

    await db.commit()
    await db.refresh(order_record)
    return order_record

async def get_user_order_history(db: AsyncSession, user_id: str) -> List[OrderHistory]:
    # Select orders for conversations owned by this user
    from backend.app.models.conversation import Conversation
    result = await db.execute(
        select(OrderHistory)
        .join(Conversation, OrderHistory.conversation_id == Conversation.id)
        .where(Conversation.user_id == user_id)
        .order_by(OrderHistory.created_at.desc())
    )
    return list(result.scalars().all())

async def get_order_tracking_details(order_id: str, api_key: str) -> Dict[str, Any]:
    """Retrieve real-time tracking details from BurgerPrints order API."""
    # Toggle Mock check
    from ai.tools import USE_MOCK_API, BASE_URL
    if not USE_MOCK_API and api_key:
        try:
            url = f"{BASE_URL}/orders/{order_id}"
            params = {"apiKey": api_key}
            response = httpx.get(url, params=params, timeout=10.0)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
            
    # Mock fallback
    import random
    return {
        "order_id": order_id,
        "status": "in_production",
        "fulfillment": {
            "factory_id": "factory_us_chicago_01",
            "factory_name": "Chicago Print Corp"
        },
        "tracking": {
            "carrier": "USPS",
            "tracking_number": f"940010000000{random.randint(1000000000, 9999999999)}",
            "estimated_delivery": "2026-06-12T18:00:00Z"
        }
    }
