from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/ledger"
    redis_url: str = "redis://redis:6379/0"
    idempotency_ttl_seconds: int = 86400
    rate_limit_max_requests: int = 10
    rate_limit_window_seconds: int = 60

    class Config:
        env_file = ".env"

settings = Settings()
