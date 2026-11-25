from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "SwarUtsav"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
