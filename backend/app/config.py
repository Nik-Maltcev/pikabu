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
    llm_model: str = "deepseek-v4-flash"
    llm_max_retries: int = 3
    llm_context_window: int = 131_072
    llm_max_tokens_chunk: int = 16384         # max_tokens для анализа чанков
    llm_max_tokens_aggregation: int = 16384   # max_tokens для агрегации
    llm_chunk_size: int = 100000               # макс. токенов входных данных на чанк

    # Z.AI / GLM settings
    glm_api_key: str = ""
    glm_model: str = "glm-4.7-flash"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # SMTP (email notifications)
    resend_api_key: str = ""
    resend_from_email: str = "BizMap <noreply@bizmap.space>"

    # Cache
    cache_ttl_hours: int = 24

    # Concurrency
    max_concurrent_analyses: int = 5  # How many analyses can run in parallel

    # Pikabu parser
    pikabu_proxy_url: str = ""  # РФ прокси для pikabu.ru, например "socks5://user:pass@host:port"
    pikabu_retry_delay_429: int = 60
    pikabu_retry_count_5xx: int = 3
    pikabu_retry_delay_5xx: int = 10

    # MiroFish integration
    mirofish_url: str = "http://localhost:5001"  # URL MiroFish backend

    # Robokassa payment
    robokassa_login: str = ""
    robokassa_password1: str = ""
    robokassa_password2: str = ""
    robokassa_test_mode: bool = False
    site_url: str = "http://localhost:5173"  # Frontend URL for redirects

    # Twilio Verify (SMS auth)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_verify_service_sid: str = ""
    jwt_secret: str = "bizmap-jwt-secret-change-me"

    # Cron jobs
    cron_secret: str = "change-me-in-production"  # Secret token for cron endpoints

    # Gemini API
    gemini_max_retries: int = 3

    # Market Data enrichment
    serpapi_key: str = ""  # SerpAPI key for Google Trends data
    inflation_rate_percent: float = 9.5  # CBR official rate, updated periodically

    # Competitor Lookup
    linkup_api_key: str = ""  # Linkup API key for competitor search

    # Enrichment timeouts
    enrichment_total_timeout: float = 90.0  # Total budget for all enrichment (LLM extraction is slow)
    enrichment_per_source_timeout: float = 30.0  # Per-source timeout (includes Linkup API + LLM call)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
