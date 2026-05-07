from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from pydantic import field_validator


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "Stock Analyzer API"
    debug: bool = False
    cors_origins: str = "*"
    news_api_key: str = ""
    anthropic_api_key: str = ""
    cache_ttl_seconds: int = 30
    screener_cache_ttl_seconds: int = 300
    screener_include_news: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    signal_notifications_enabled: bool = False
    signal_poll_interval_seconds: int = 300
    signal_cooldown_minutes: int = 30
    signal_dedupe_ttl_hours: int = 720
    signal_min_score: float = 70.0
    signal_min_risk_reward: float = 1.2
    signal_max_entry_distance_pct: float = 2.0
    signal_min_target_room_pct: float = 1.0
    signal_markets: str = "us,th,cn,gold,crypto"
    snack_trade_enabled: bool = True
    snack_trade_min_score: float = 58.0
    snack_trade_min_risk_reward: float = 1.0
    snack_trade_min_volume_ratio: float = 0.5
    snack_trade_max_per_market: int = 1
    snack_trade_max_entry_distance_pct: float = 8.0
    snack_trade_min_target_room_pct: float = 1.0

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("release", "prod", "production", "false", "0", "no", "off"):
                return False
            if normalized in ("debug", "dev", "development", "true", "1", "yes", "on"):
                return True
        return value

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")


settings = Settings()
