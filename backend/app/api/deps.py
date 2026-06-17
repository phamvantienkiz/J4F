from sqlmodel import Session
from app.database import get_session

def get_db():
    """
    Dependency to get the database session.
    """
    yield from get_session()
