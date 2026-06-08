from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://snip:snip_dev@localhost:5432/snip"
    db_pool_size: int = 10
    db_max_overflow: int = 5

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str  # HMAC signing key for session cookies
    hmac_key: str    # HMAC-SHA256 key for email_search_hash

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # KMS
    kms_key_arn: str = ""

    # SES
    ses_from_email: str = "noreply@snip.io"

    # Google Safe Browsing
    google_safe_browsing_api_key: str = ""
    google_safe_browsing_timeout: float = 0.8

    # Mixpanel
    mixpanel_token: str = ""
    mixpanel_timeout: float = 2.0

    # Cloudflare
    cloudflare_zone_id: str = ""
    cloudflare_api_token: str = ""
    snip_base_url: str = "https://snip.io"
    cloudflare_purge_timeout: float = 2.0

    # SQS
    sqs_clicks_url: str = ""
    sqs_mixpanel_url: str = ""
    sqs_mail_events_url: str = ""

    # App frontend base URL (used in transactional emails)
    app_base_url: str = "https://app.snip.io"

    # Sentry
    sentry_dsn: str = ""

    # Pwned Passwords
    pwned_passwords_timeout: float = 0.5

    # Rate limits
    link_create_rate_limit: int = 60       # per minute per user
    signup_rate_limit_ip: int = 5          # per hour per IP
    signup_rate_limit_domain: int = 3      # per hour per email domain
    login_max_attempts: int = 5            # per 15-minute window per email
    login_lockout_minutes: int = 15
    password_reset_rate_limit_email: int = 3   # per hour per email
    password_reset_rate_limit_ip: int = 10     # per hour per IP

    # Session
    session_absolute_days: int = 30
    session_idle_days: int = 7

    # Tokens
    invite_expiry_days: int = 7
    email_verification_expiry_hours: int = 24
    password_reset_expiry_minutes: int = 60

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()  # type: ignore[call-arg]
