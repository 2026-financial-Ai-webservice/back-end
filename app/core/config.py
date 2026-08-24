from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "local"
    APP_NAME: str = "Financial-AI"

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    KIS_BASE_URL: str="https://openapi.koreainvestment.com:9443"
    DART_API_KEY: str = ""
    KIS_APP_KEY: str = ""
    KIS_APP_SECRET: str = ""
    KIS_ACCESS_TOKEN: str = ""
    KIS_ACCOUNT_NO: str = ""

    MARKET_DATA_BATCH_ENABLED: bool = True
    MARKET_DATA_BATCH_HOUR: int = 15
    MARKET_DATA_BATCH_MINUTE: int = 40
    MARKET_DATA_REQUEST_INTERVAL_SECONDS: float = 1.1

    OPENAI_API_KEY: str = ""

    SECRET_KEY: str = "change-me-in-production"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
