"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application settings"""
    
    # App settings
    APP_NAME: str = "OSINT Intelligence Platform"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./osint_platform.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS (JSON string in .env, or comma-separated)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3002,http://localhost:5173,http://localhost:5174,http://127.0.0.1:3000,http://127.0.0.1:3002,http://127.0.0.1:5173,http://127.0.0.1:5174"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS into a list"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # OSINT Tools
    SHERLOCK_PATH: str = "sherlock"
    RECONNG_PATH: str = "recon-ng"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # External APIs (optional)
    NEWS_API_KEY: str = ""
    GITHUB_TOKEN: str = ""
    SHODAN_API_KEY: str = ""
    
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
    # Documentation: https://ensembledata.com/apis/docs
    ENSEMBLEDATA_API_KEY: str = ""

    # Maltego Transform Server (optional)
    MALTEGO_API_URL: str = ""
    MALTEGO_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env

settings = Settings()
