from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from backend.app.api.deps import get_db, get_current_user
from backend.app.models.user import User
from backend.app.schemas.order import OrderDraftConfirmRequest, OrderHistoryResponse
from backend.app.services import order_service

router = APIRouter()

@router.post("/confirm", response_model=OrderHistoryResponse)
async def confirm_order(
    request_in: OrderDraftConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    order_record = await order_service.confirm_and_create_order(db, current_user.id, request_in)
    
    # Map to schema
    import json
    addr = {}
    if order_record.shipping_address:
        try:
            addr = json.loads(order_record.shipping_address)
        except Exception:
            pass
            
    return OrderHistoryResponse(
        id=order_record.id,
        order_id=order_record.order_id,
        sku=order_record.sku,
        quantity=order_record.quantity,
        total_cost=order_record.total_cost,
        shipping_address=addr,
        tracking_number=order_record.tracking_number,
        status=order_record.status,
        created_at=order_record.created_at
    )

@router.get("/history", response_model=List[OrderHistoryResponse])
async def list_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    orders = await order_service.get_user_order_history(db, current_user.id)
    
    import json
    response_orders = []
    for o in orders:
        addr = {}
        if o.shipping_address:
            try:
                addr = json.loads(o.shipping_address)
            except Exception:
                pass
        response_orders.append(OrderHistoryResponse(
            id=o.id,
            order_id=o.order_id,
            sku=o.sku,
            quantity=o.quantity,
            total_cost=o.total_cost,
            shipping_address=addr,
            tracking_number=o.tracking_number,
            status=o.status,
            created_at=o.created_at
        ))
    return response_orders

@router.get("/{order_id}/tracking", response_model=Dict[str, Any])
async def get_tracking(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Retrieve user preference for BurgerPrints API Key if needed
    from backend.app.services.auth_service import get_user_preference
    pref = await get_user_preference(db, current_user.id)
    api_key = pref.preferred_market or ""  # Mocking uses this
    
    tracking_data = await order_service.get_order_tracking_details(order_id, api_key)
    return tracking_data
