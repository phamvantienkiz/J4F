import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

# Đường dẫn gốc tới thư mục backend/
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    burgerprints_api_key: str = Field(default="")
    burgerprints_api_base_url: str = "https://api.burgerprints.com/v2"
    burgerprints_enable_sandbox_create_order: bool = True
    database_url: str = Field(default="sqlite:///./database.db")
    openai_api_key: str = "mock-key"
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_chat_deployment: Optional[str] = None
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_embed_endpoint: Optional[str] = None
    azure_openai_embed_api_key: Optional[str] = None
    azure_openai_embed_deployment: Optional[str] = None
    azure_openai_embed_api_version: str = "2024-12-01-preview"

    class Config:
        env_file = os.path.join(BASE_DIR, ".env")
        extra = "ignore"

settings = Settings()
