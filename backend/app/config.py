import os
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # Core settings with safe defaults for local runs/tests
    DATABASE_URL: str = Field(default="sqlite:////data/app.db", env="DATABASE_URL")
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000", env="ALLOWED_ORIGINS")
    LLM_API_KEYS: str = Field(default="dummy1,dummy2", env="LLM_API_KEYS")  # comma-separated placeholder keys
    ENABLE_FAILURE_SIMULATION: bool = Field(default=False, env="ENABLE_FAILURE_SIMULATION")
    DEFAULT_MODEL: str = Field(default="gpt-3.5-turbo", env="DEFAULT_MODEL")
    # Derived fields
    allowed_origins_list: List[str] = []
    api_keys_list: List[str] = []

    @validator("allowed_origins_list", pre=True, always=True)
    def split_origins(cls, v, values):
        origins = values.get("ALLOWED_ORIGINS", "")
        return [origin.strip() for origin in origins.split(",") if origin.strip()]

    @validator("api_keys_list", pre=True, always=True)
    def split_keys(cls, v, values):
        keys = values.get("LLM_API_KEYS", "")
        return [key.strip() for key in keys.split(",") if key.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
