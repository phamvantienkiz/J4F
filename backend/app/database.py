from sqlmodel import create_engine, SQLModel, Session
from app.config import settings
# Import all models to ensure they are registered with SQLModel.metadata
from app.models import Product, ProductVariant, ShippingZone, ShippingFee, ChatSession

engine = create_engine(settings.supabase_db_url, echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
