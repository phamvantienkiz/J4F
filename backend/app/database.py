from sqlmodel import create_engine, SQLModel, Session
from app.config import settings
# Import all models to ensure they are registered with SQLModel.metadata
from app.models import Product, ProductVariant, ShippingZone, ShippingFee, ChatSession, Order

# SQLite connect_args: cho phép transaction song song trong cùng thread
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=_connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
