from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    store_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class UserPreferenceUpdate(BaseModel):
    preferred_market: Optional[str] = None
    target_margin: Optional[float] = None
    max_shipping_days: Optional[int] = None
    fulfillment_priority: Optional[str] = None

class UserPreferenceResponse(BaseModel):
    preferred_market: str
    target_margin: float
    max_shipping_days: int
    fulfillment_priority: str
    updated_at: datetime

    class Config:
        from_attributes = True
