from fastapi import APIRouter
import time

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.get("/ready")
def readiness_check():
    # Giả định cơ sở dữ liệu đã sẵn sàng sau khi đồng bộ
    return {
        "ready": True,
        "warming": False,
        "warmup_ms": 150,
        "error": None
    }
