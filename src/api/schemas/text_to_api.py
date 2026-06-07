from pydantic import BaseModel, Field


class TextToApiRequest(BaseModel):
    text: str = Field(..., min_length=1)
