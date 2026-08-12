"""Configuration settings for IncidentMind Backend."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "IncidentMind Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Testing Flags
    ENVIRONMENT: str = "development"
    TESTING: bool = False
    LOG_LEVEL: str = "INFO"
    
    # JWT Authentication Security (no usable default in non-testing environments)
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # CockroachDB Database Settings
    DATABASE_URL: str = ""
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 26257
    DATABASE_NAME: str = "incidentmind"
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = ""
    DATABASE_SSLMODE: str = "disable"

    # Email & Slack Notification Settings
    NOTIFICATIONS_ENABLED: bool = True
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "alerts@incidentmind.ai"
    SLACK_WEBHOOK_URL: str = ""
    SLACK_DEFAULT_CHANNEL: str = "#incidents-alerts"

    # Configurable explicit CORS origins list
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_jwt_secret_key(self) -> str:
        """Return active JWT secret key, or test fallback if TESTING is True."""
        if self.JWT_SECRET_KEY:
            return self.JWT_SECRET_KEY
        if self.TESTING:
            return "test_secret_key_for_unit_tests_32_bytes_min"
        return ""

    def get_database_connection_url(self) -> str:
        """Construct database connection string securely."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        password_str = f":{self.DATABASE_PASSWORD}" if self.DATABASE_PASSWORD else ""
        return (
            f"postgresql://{self.DATABASE_USER}{password_str}@"
            f"{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            f"?sslmode={self.DATABASE_SSLMODE}"
        )

    def validate_security(self) -> None:
        """
        Validate security settings.
        In non-testing environments (TESTING=False), JWT_SECRET_KEY must be configured via environment.
        Raises ConfigurationError if missing or insecure.
        """
        if not self.TESTING:
            active_key = self.get_jwt_secret_key()
            if not active_key or len(active_key.strip()) < 32 or "default" in active_key.lower():
                from backend.core.exceptions import ConfigurationError
                raise ConfigurationError(
                    "JWT_SECRET_KEY must be configured with a strong secret (min 32 chars) in non-testing environments."
                )


settings = Settings()
