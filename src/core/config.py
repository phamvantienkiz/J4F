import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


class Settings:
    app_name = "BurgerPrints Text-to-API Core"
    burgerprints_api_base_url = os.getenv("BURGERPRINTS_API_BASE_URL", "https://api.burgerprints.com/v2")
    burgerprints_catalog_api_base_url = os.getenv("BURGERPRINTS_CATALOG_API_BASE_URL", "https://catalog-api.burgerprints.com/api/v1")
    burgerprints_enable_sandbox_create_order = os.getenv("BURGERPRINTS_ENABLE_SANDBOX_CREATE_ORDER", "false").lower() == "true"
    llm_provider = os.getenv("LLM_PROVIDER", "anthropic")
    llm_api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    llm_api_key_present = bool(llm_api_key)
    llm_base_url = os.getenv("ANTHROPIC_BASE_URL") or os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL")
    llm_model = os.getenv("ANTHROPIC_DEFAULT_OPUS_MODEL") or os.getenv("ANTHROPIC_MODEL") or os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-5.5")
    llm_intent_enabled = os.getenv("LLM_INTENT_ENABLED", "false").lower() == "true"
    llm_market_router_enabled = os.getenv("LLM_MARKET_ROUTER_ENABLED", "false").lower() == "true"
    cors_origins = ["*"]


settings = Settings()
