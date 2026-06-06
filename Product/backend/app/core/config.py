from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "BurgerPrints Agent"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "BURGERPRINTS_AGENT_SUPER_SECRET_KEY_2026_HACKATHON"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    DATABASE_URL: str = "sqlite+aiosqlite:///../ai/data/sqlite.db"
    
    USE_MOCK_API: bool = True
    BURGERPRINTS_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
