from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON
import datetime


class Order(SQLModel, table=True):
    """Model lưu thông tin đơn hàng thành công từ BurgerPrints API."""

    __tablename__ = "orders"

    # ID tự sinh (UUID text)
    id: str = Field(primary_key=True)

    # Mã đơn BurgerPrints trả về (ví dụ: "ASAMPLE-xxxx-xxxxx")
    burger_order_id: Optional[str] = Field(default=None, index=True)

    # Mã tham chiếu do backend tự sinh (ví dụ: "REF-SKU-1718900000")
    reference_order_id: str = Field(index=True)

    # SKU sản phẩm
    sku: str = Field(index=True)

    # Tên khách hàng
    customer_name: str

    # Tổng tiền (landed cost * quantity)
    total_amount: float

    # Trạng thái đơn: created, shipped, delivered, cancelled
    status: str = Field(default="created", index=True)

    # Thời gian tạo
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
