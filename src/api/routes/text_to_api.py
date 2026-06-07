import requests
from fastapi import APIRouter, HTTPException

from src.api.schemas.text_to_api import TextToApiRequest
from src.core.engine import run_text_to_api


router = APIRouter(prefix="/text-to-api", tags=["text-to-api"])


@router.post("")
def text_to_api(request: TextToApiRequest):
    try:
        return run_text_to_api(request.text)
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except requests.HTTPError as error:
        status_code = error.response.status_code if error.response is not None else 502
        detail = error.response.text if error.response is not None else str(error)
        raise HTTPException(status_code=status_code, detail=detail) from error
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
