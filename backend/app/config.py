from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/pikabu_analyzer"

    # Google Gemini API
    gemini_api_key: str = ""

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Cache
    cache_ttl_hours: int = 24

    # Pikabu parser
    pikabu_proxy_url: str = ""  # РФ прокси для pikabu.ru, например "socks5://user:pass@host:port"
    pikabu_retry_delay_429: int = 60
    pikabu_retry_count_5xx: int = 3
    pikabu_retry_delay_5xx: int = 10

    # Gemini API
    gemini_max_retries: int = 3
    gemini_context_window: int = 1_000_000

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
