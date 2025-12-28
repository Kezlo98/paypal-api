"""Configuration management with Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # PayPal credentials
    paypal_client_id: str = Field(default="test_id", description="PayPal OAuth2 client ID")
    paypal_client_secret: str = Field(default="test_secret", description="PayPal OAuth2 client secret")
    paypal_mode: str = Field("sandbox", description="PayPal environment: sandbox or live")

    # Server config
    port: int = Field(8000, description="Application port")
    rate_limit_per_minute: int = Field(60, description="Rate limit per IP per minute")

    @property
    def paypal_base_url(self) -> str:
        """Get PayPal API base URL based on mode."""
        if self.paypal_mode == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    @field_validator("paypal_mode")
    @classmethod
    def validate_paypal_mode(cls, v: str) -> str:
        """Validate PAYPAL_MODE is either sandbox or live."""
        if v not in ("sandbox", "live"):
            raise ValueError('PAYPAL_MODE must be "sandbox" or "live"')
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance for convenience
settings = get_settings()
