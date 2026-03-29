from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = (
        "postgresql://polymarket:polymarket_pass_2024@localhost:5432/polymarket_trader"
    )
    SECRET_KEY: str = "polymarket_secret_key_change_in_production_2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    POLYMARKET_API_URL: str = "https://clob.polymarket.com"

    class Config:
        env_file = ".env"


settings = Settings()
