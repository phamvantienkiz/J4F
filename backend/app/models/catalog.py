from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, Relationship, JSON

class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, index=True)
    image_url: Optional[str] = None

    variants: List["ProductVariant"] = Relationship(back_populates="product", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class ProductVariant(SQLModel, table=True):
    __tablename__ = "product_variants"

    id: str = Field(primary_key=True)
    product_id: str = Field(foreign_key="products.id", index=True)
    sku: str = Field(index=True)
    color: Optional[str] = Field(default=None, index=True)
    size: Optional[str] = Field(default=None, index=True)
    base_cost: float = Field(default=0.0)
    second_item_price: float = Field(default=0.0)
    addition_price: float = Field(default=0.0)
    clone_price: float = Field(default=0.0)
    weight: float = Field(default=0.0)
    mockup_url: Optional[str] = None
    catalog_variant_id: Optional[str] = None
    partner_name: Optional[str] = Field(default="BurgerPrints", index=True)
    location_name: Optional[str] = Field(default="US", index=True)

    # Biểu phí ship lưu trực tiếp để tăng tốc truy vấn
    shipping_cost_us: float = Field(default=4.5)
    shipping_adding_us: float = Field(default=1.5)
    shipping_cost_ww: float = Field(default=5.99)
    shipping_adding_ww: float = Field(default=2.0)

    product: Product = Relationship(back_populates="variants")


class ShippingZone(SQLModel, table=True):
    __tablename__ = "shipping_zones"

    id: int = Field(default=None, primary_key=True)
    country_code: str = Field(index=True, unique=True)
    country_name: str = Field(index=True)

    fees: List["ShippingFee"] = Relationship(back_populates="zone", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class ShippingFee(SQLModel, table=True):
    __tablename__ = "shipping_fees"

    id: int = Field(default=None, primary_key=True)
    zone_id: int = Field(foreign_key="shipping_zones.id", index=True)
    carrier: str = Field(index=True)
    first_item_fee: float = Field(default=0.0)
    additional_item_fee: float = Field(default=0.0)
    delivery_time: Optional[str] = None # E.g., "3-5 business days"

    zone: ShippingZone = Relationship(back_populates="fees")
