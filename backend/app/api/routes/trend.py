from fastapi import APIRouter, Query, Depends
from sqlmodel import Session
from app.schemas.trend import SuggestedQuestions
from app.services.trend import TrendService
from app.api.deps import get_db
import datetime

router = APIRouter()
trend_service = TrendService()

@router.get("/suggestions", response_model=SuggestedQuestions)
def get_suggestions(
    country: str = Query("US", description="Mã quốc gia đích (ví dụ: US, DE, VN)"),
    month: int = Query(None, description="Tháng cần gợi ý (1-12), mặc định là tháng hiện tại"),
    db: Session = Depends(get_db)
):
    if month is None:
        month = datetime.datetime.now().month

    return trend_service.get_seasonal_suggestions(db, country, month)
