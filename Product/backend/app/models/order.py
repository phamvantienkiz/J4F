from sqlalchemy import Column, String, ForeignKey, Integer, Float, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.db.session import Base
import uuid

class OrderHistory(Base):
    __tablename__ = "order_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(String, unique=True, nullable=False)
    sku = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    total_cost = Column(Float, nullable=False)
    shipping_address = Column(Text, nullable=False) # JSON String
    tracking_number = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="orders")
