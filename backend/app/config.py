"""
Application settings, loaded from environment variables (see .env.example).
Using pydantic-settings keeps this simple: one object, imported everywhere.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120
    upload_dir: str = "uploads"
    max_upload_mb: int = 5
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"
    port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
