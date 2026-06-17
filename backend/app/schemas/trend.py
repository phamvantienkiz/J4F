from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ClimateType(str, Enum):
    WINTER = "winter"
    SUMMER = "summer"
    SPRING = "spring"
    AUTUMN = "autumn"
    DRY_COOL = "dry_cool"
    RAINY_HOT = "rainy_hot"

class EventMetadata(BaseModel):
    name: str = Field(..., description="Tên ngày lễ hoặc sự kiện")
    description: Optional[str] = Field(None, description="Mô tả sự kiện")
    target_niches: List[str] = Field(default_factory=list, description="Các ngách thiết kế đề xuất")
    suggested_categories: List[str] = Field(default_factory=list, description="Danh mục sản phẩm đề xuất")

class SuggestedQuestions(BaseModel):
    country: str = Field(..., description="Mã quốc gia đã giải quyết (sau fallback nếu có)")
    original_country: Optional[str] = Field(None, description="Mã quốc gia gốc trước khi fallback")
    is_fallback: bool = Field(default=False, description="Đánh dấu nếu có fallback quốc gia")
    month: int = Field(..., description="Tháng truy vấn")
    season: str = Field(..., description="Mùa khí hậu")
    weather_context: str = Field(..., description="Mô tả thời tiết/bối cảnh bán hàng")
    events: List[str] = Field(default_factory=list, description="Danh sách các lễ hội lớn")
    product_types: List[str] = Field(default_factory=list, description="Các loại sản phẩm đề xuất")
    suggestions: List[str] = Field(default_factory=list, description="Các câu hỏi gợi ý cho seller")
