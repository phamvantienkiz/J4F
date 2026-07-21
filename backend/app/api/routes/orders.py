from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import logging

from app.database import get_session
from app.models.order import Order

logger = logging.getLogger(__name__)
router = APIRouter()


class OrderResponse(BaseModel):
    """Schema trả về cho API lịch sử đơn hàng"""
    id: str
    order_number: str
    sku: str
    quantity: int
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    shipping_address: dict
    total_amount: float
    status: str
    burgerprints_order_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


@router.get("/orders/history", response_model=List[OrderResponse])
async def get_order_history(
    limit: int = Query(default=50, ge=1, le=200, description="Số lượng đơn tối đa trả về"),
    status: Optional[str] = Query(default=None, description="Lọc theo trạng thái (created, shipped, delivered, cancelled)"),
    sku: Optional[str] = Query(default=None, description="Lọc theo SKU"),
    session: Session = Depends(get_session)
):
    """
    Lấy lịch sử đơn hàng từ database, sắp xếp theo thời gian tạo giảm dần.
    """
    try:
        # Build query
        query = select(Order)

        # Apply filters
        if status:
            query = query.where(Order.status == status)
        if sku:
            query = query.where(Order.sku == sku)

        # Sort by created_at DESC and limit
        query = query.order_by(Order.created_at.desc()).limit(limit)

        # Execute query
        orders = session.exec(query).all()

        response_orders = []
        for order in orders:
            response_orders.append(
                OrderResponse(
                    id=str(order.id),
                    order_number=order.burger_order_id or order.reference_order_id or "N/A",
                    sku=order.sku,
                    quantity=1,
                    customer_name=order.customer_name,
                    customer_email=None,
                    customer_phone=None,
                    shipping_address={"address1": "Unknown", "city": "Unknown", "country": "US"},
                    total_amount=float(order.total_amount),
                    status=order.status,
                    burgerprints_order_id=order.burger_order_id,
                    created_at=order.created_at,
                    updated_at=order.created_at
                )
            )

        logger.info(f"Retrieved {len(response_orders)} orders from history")
        return response_orders

    except Exception as e:
        logger.error(f"Error retrieving order history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy lịch sử đơn hàng: {str(e)}")


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: str,
    session: Session = Depends(get_session)
):
    """
    Lấy thông tin chi tiết một đơn hàng theo ID.
    """
    try:
        order = session.get(Order, order_id)

        if not order:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn hàng với ID: {order_id}")

        return OrderResponse(
            id=str(order.id),
            order_number=order.burger_order_id or order.reference_order_id or "N/A",
            sku=order.sku,
            quantity=1,
            customer_name=order.customer_name,
            customer_email=None,
            customer_phone=None,
            shipping_address={"address1": "Unknown", "city": "Unknown", "country": "US"},
            total_amount=float(order.total_amount),
            status=order.status,
            burgerprints_order_id=order.burger_order_id,
            created_at=order.created_at,
            updated_at=order.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy thông tin đơn hàng: {str(e)}")


@router.get("/orders/by-order-number/{order_number}", response_model=OrderResponse)
async def get_order_by_order_number(
    order_number: str,
    session: Session = Depends(get_session)
):
    """
    Lấy thông tin chi tiết một đơn hàng theo order_number (mã đơn từ BurgerPrints).
    """
    try:
        query = select(Order).where((Order.burger_order_id == order_number) | (Order.reference_order_id == order_number))
        order = session.exec(query).first()

        if not order:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn hàng với mã: {order_number}")

        return OrderResponse(
            id=str(order.id),
            order_number=order.burger_order_id or order.reference_order_id or "N/A",
            sku=order.sku,
            quantity=1,
            customer_name=order.customer_name,
            customer_email=None,
            customer_phone=None,
            shipping_address={"address1": "Unknown", "city": "Unknown", "country": "US"},
            total_amount=float(order.total_amount),
            status=order.status,
            burgerprints_order_id=order.burger_order_id,
            created_at=order.created_at,
            updated_at=order.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving order by order_number {order_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy thông tin đơn hàng: {str(e)}")
