"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://drtrial:drtrial@localhost:5432/drtrial"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    upload_dir: str = "data/uploads"
    use_dl_models: bool = False
    model_version: str = "drtrial-1.1.0"

    class Config:
        env_file = ".env"


settings = Settings()
