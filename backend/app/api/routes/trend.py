from typing import Optional

from fastapi import APIRouter, Query, Depends, Request
from sqlmodel import Session
from app.schemas.trend import SuggestedQuestions
from app.services.trend import TrendService
from app.api.deps import get_db
import datetime

router = APIRouter()
trend_service = TrendService()

@router.get("/suggestions", response_model=SuggestedQuestions)
def get_suggestions(
    request: Request,
    country: Optional[str] = Query(None, description="Mã quốc gia đích (ví dụ: US, DE, VN)"),
    month: Optional[int] = Query(None, description="Tháng cần gợi ý (1-12), mặc định là tháng hiện tại"),
    db: Session = Depends(get_db)
):
    if month is None:
        month = datetime.date.today().month

    resolved_country = country
    if not resolved_country or resolved_country.strip().lower() in {"none", "null", "undefined"}:
        resolved_country = (
            request.headers.get("cf-ipcountry")
            or request.headers.get("x-vercel-ip-country")
            or request.headers.get("cloudfront-viewer-country")
            or request.headers.get("x-country-code")
        )

    return trend_service.get_seasonal_suggestions(db, resolved_country, month)
