import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "AI Resume Parser"

    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=(
            ".env",
            "backend/.env",
            os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        ),
        extra="ignore"
    )


settings = Settings()
