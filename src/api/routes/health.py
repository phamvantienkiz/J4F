import time

from fastapi import APIRouter


router = APIRouter(tags=["health"])
_ready_state = {
    "ready": True,
    "warming": False,
    "warmup_started_at": None,
    "warmup_finished_at": None,
    "warmup_ms": None,
    "error": None,
}


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    return _ready_state


def is_ready():
    return bool(_ready_state.get("ready"))


def readiness_error():
    return _ready_state.get("error")


def mark_warmup_started():
    _ready_state.update(
        {
            "ready": False,
            "warming": True,
            "warmup_started_at": time.time(),
            "warmup_finished_at": None,
            "warmup_ms": None,
            "error": None,
        }
    )


def mark_warmup_finished(error: str | None = None):
    finished_at = time.time()
    started_at = _ready_state.get("warmup_started_at") or finished_at
    _ready_state.update(
        {
            "ready": error is None,
            "warming": False,
            "warmup_finished_at": finished_at,
            "warmup_ms": int((finished_at - started_at) * 1000),
            "error": error,
        }
    )
