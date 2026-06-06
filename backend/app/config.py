"""
Application configuration
"""
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # App settings
    APP_NAME: str = "OSINT Intelligence Platform"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALERT_MONITOR_INTERVAL_HOURS: int = 6
    INQUIRY_SCHEDULER_INTERVAL_HOURS: int = 6
    INQUIRY_SCHEDULER_ENABLED: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./osint_platform.db"
    USE_ALEMBIC: bool = False

    @property
    def database_url_sync(self) -> str:
        """URL síncrona per Alembic (sqlite/postgresql sense driver async)."""
        url = self.DATABASE_URL
        if url.startswith("sqlite+aiosqlite"):
            return url.replace("sqlite+aiosqlite", "sqlite", 1)
        if url.startswith("postgresql+asyncpg"):
            return url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
        return url

    # Security
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS (JSON string in .env, or comma-separated)
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://localhost:3002,http://localhost:5173,"
        "http://localhost:5174,http://127.0.0.1:3000,http://127.0.0.1:3002,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174,"
        "http://192.168.100.13:3000"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS into a list"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS

    # LLM provider for extraction + prospective scenarios
    # auto = first available key (anthropic → openai → gemini)
    LLM_PROVIDER: str = "auto"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EXTRACT_MODEL: str = "gpt-4o-mini"
    OPENAI_SCENARIO_MODEL: str = "gpt-4o"

    # Anthropic Claude
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_EXTRACT_MODEL: str = "claude-haiku-4-5-20251001"
    ANTHROPIC_SCENARIO_MODEL: str = "claude-sonnet-4-20250514"

    # Google Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_EXTRACT_MODEL: str = "gemini-2.0-flash"
    GEMINI_SCENARIO_MODEL: str = "gemini-2.0-flash"

    # OSINT Tools
    SHERLOCK_PATH: str = "sherlock"
    THEHARVESTER_PATH: str = "theHarvester"
    RECONNG_PATH: str = "recon-ng"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # External APIs (optional)
    NEWS_API_KEY: str = ""
    GITHUB_TOKEN: str = ""
    SHODAN_API_KEY: str = ""

    # Tavily — cerca web en temps real (https://tavily.com)
    TAVILY_API_KEY: str = ""
    TAVILY_MAP_EXTRACT_MAX_URLS: int = 8
    TAVILY_SEARCH_EXTRACT_MAX_URLS: int = 5
    TAVILY_PREFERRED_CRAWL_LIMIT: int = 25
    TAVILY_RESEARCH_MAX_WAIT_SECONDS: int = 300
    TAVILY_AUTO_EXTRACT_EVENTS: bool = True

    # Extraction — minimum case-topic relevance (0..1) to process an OSINT article
    CASE_ARTICLE_RELEVANCE_MIN_SCORE: float = 0.28
    CASE_STATEMENT_RELEVANCE_MIN_SCORE: float = 0.22

    # Apify (Nikkei Asia scraper fallback)
    APIFY_API_TOKEN: str = ""
    APIFY_NIKKEI_ACTOR: str = "xtracto/nikkei-scraper"

    # Nikkei Asia: own (free HTTP/RSS) | apify | auto (own first, Apify if body short)
    NIKKEI_PROVIDER: str = "auto"
    NIKKEI_RATE_LIMIT_SEC: float = 2.0

    # Bloomberg (RSS via feeds.bloomberg.com; HTML often 403)
    BLOOMBERG_RATE_LIMIT_SEC: float = 2.5

    # Generic article fetcher (enrichment pipeline)
    ARTICLE_FETCHER_RATE_LIMIT_SEC: float = 1.5
    ARTICLE_FETCHER_TIMEOUT_SEC: float = 25.0
    OSINT_POST_ENRICH_MAX_ITEMS: int = 5

    # Domains boosted for enrichment / extraction priority
    GEOPOLITICS_PREFERRED_DOMAINS: str = (
        "foreignaffairs.com,reuters.com,csis.org,iiss.org,chathamhouse.org,"
        "ecfr.eu,brookings.edu,rand.org,crisisgroup.org,nikkei.com,"
        "asia.nikkei.com,bloomberg.com,japantimes.co.jp,ft.com,economist.com"
    )

    # Financial APIs (optional - for investment recommendations)
    ALPHAVANTAGE_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""
    FINANCIAL_MODELING_PREP_API_KEY: str = ""

    # Geopolitical APIs (optional - premium/trial required)
    PERMUTABLE_API_KEY: str = ""

    # Currency Exchange APIs (optional)
    EXCHANGERATE_API_KEY: str = ""
    FIXER_API_KEY: str = ""

    # Cryptocurrency APIs (optional)
    COINGECKO_API_KEY: str = ""

    # IP Geolocation APIs (optional)
    IPSTACK_API_KEY: str = ""

    # EnsembleData API (Social Media Scraping - optional)
    ENSEMBLEDATA_API_KEY: str = ""

    # Maltego Transform Server (optional)
    MALTEGO_API_URL: str = ""
    MALTEGO_API_KEY: str = ""


def _validate_settings(s: Settings) -> None:
    """Fail fast if critical settings are missing."""
    if not s.SECRET_KEY:
        print("ERROR: SECRET_KEY no configurada. Afegeix SECRET_KEY=<clau_aleatoria> al .env")
        print('Genera una clau amb: python -c "import secrets; print(secrets.token_hex(32))"')
        sys.exit(1)


settings = Settings()
_validate_settings(settings)
