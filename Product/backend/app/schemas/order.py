from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class OrderAddress(BaseModel):
    full_name: str
    address_line1: str
    address_line2: Optional[str] = ""
    city: str
    state: str
    zip_code: str
    country: str
    phone: Optional[str] = "+12175550143"

class OrderDraftConfirmRequest(BaseModel):
    thread_id: str
    sku: str
    quantity: int
    shipping_address: OrderAddress
    selected_option_id: str

class OrderHistoryResponse(BaseModel):
    id: str
    order_id: str
    sku: str
    quantity: int
    total_cost: float
    shipping_address: Dict[str, Any]
    tracking_number: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
