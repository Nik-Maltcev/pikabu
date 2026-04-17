from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/pikabu_analyzer"

    # Google Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # LLM provider: "deepseek", "gemini", or "glm"
    llm_provider: str = "deepseek"

    # LLM settings (DeepSeek / OpenAI-compatible API)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_max_retries: int = 3
    llm_context_window: int = 100_000

    # Z.AI / GLM settings
    glm_api_key: str = ""
    glm_model: str = "GLM-4-Flash"

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

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
