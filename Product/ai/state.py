from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field

class UserPreference(BaseModel):
    preferred_market: str = Field(default="US", description="Thị trường ưu tiên của seller (US, EU, VN...)")
    target_margin: float = Field(default=40.0, description="Mức lợi nhuận gộp mục tiêu tính theo %")
    max_shipping_days: int = Field(default=7, description="Thời gian giao hàng tối đa mong muốn (ngày)")
    fulfillment_priority: str = Field(default="margin", description="Ưu tiên tối ưu: 'margin' hoặc 'speed'")

class Requirements(BaseModel):
    product_type: Optional[str] = Field(None, description="Loại sản phẩm (ví dụ: Unisex T-Shirt, Ceramic Mug...)")
    color: Optional[str] = Field(None, description="Màu sắc sản phẩm")
    size: Optional[str] = Field(None, description="Kích thước sản phẩm")
    market: Optional[str] = Field(None, description="Thị trường đích vận chuyển")
    max_cogs: Optional[float] = Field(None, description="Giá vốn tối đa mong muốn (đã gồm in + ship)")
    print_method: Optional[str] = Field(None, description="Phương thức in ấn (DTG, Embroidery...)")

class CandidateOption(BaseModel):
    option_id: str
    factory_name: str
    factory_location: str
    base_cost: float
    printing_cost: float
    shipping_cost: float
    tax_cost: float
    landed_cost: float
    margin_percentage: float
    delivery_days_min: int
    delivery_days_max: int
    sla_risk_score: float  # Điểm rủi ro chậm trễ (0-100, càng thấp càng tốt)

class OrderDraft(BaseModel):
    sku: str
    quantity: int
    shipping_name: str
    shipping_address_line1: str
    shipping_city: str
    shipping_state: str
    shipping_zip: str
    shipping_country: str
    selected_option_id: str

class AgentState(TypedDict):
    thread_id: str                                      # Khóa duy nhất của phiên chat
    user_preferences: UserPreference                    # Bộ nhớ ưu tiên lâu dài của Seller
    conversation_history: List[Dict[str, Any]]         # Lịch sử chat (LangChain Messages format)
    requirements: Requirements                          # Các tham số trích xuất được từ yêu cầu hiện tại
    candidates: List[Dict[str, Any]]                    # Danh sách thô các sản phẩm/nhà in từ API
    calculated_options: List[CandidateOption]           # Danh sách các phương án đã được Pricing Engine tính toán
    ranking_results: List[CandidateOption]              # Top các phương án đã được xếp hạng
    last_missing_fields: List[str]                      # Danh sách các trường thông tin quan trọng còn thiếu
    order_draft: Optional[OrderDraft]                   # Đơn hàng nháp đang chuẩn bị xác nhận
    order_status: Optional[Dict[str, Any]]              # Trạng thái đơn hàng sau khi tạo (mã đơn, tracking...)
