import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

# Đường dẫn gốc tới thư mục backend/
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    burgerprints_api_key: str = "147a7d53-f1ed-0203-e065-00b14e8ebbf6"
    burgerprints_api_base_url: str = "https://api.burgerprints.com/v2"
    burgerprints_enable_sandbox_create_order: bool = True
    supabase_db_url: str
    openai_api_key: str = "mock-key"
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_chat_deployment: Optional[str] = None
    azure_openai_api_version: str = "2024-08-01-preview"

    class Config:
        env_file = os.path.join(BASE_DIR, ".env")
        extra = "ignore"

settings = Settings()
