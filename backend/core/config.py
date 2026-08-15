"""Central configuration for IncidentMind backend.

Combines application/infrastructure settings with AI/Bedrock/ranking settings.
"""

import os
from dataclasses import dataclass, field
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "IncidentMind Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment & Testing
    ENVIRONMENT: str = "development"
    TESTING: bool = False
    LOG_LEVEL: str = "INFO"

    # JWT Authentication
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # CockroachDB
    DATABASE_URL: str = ""
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 26257
    DATABASE_NAME: str = "incidentmind"
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = ""
    DATABASE_SSLMODE: str = "disable"

    # Notifications
    NOTIFICATIONS_ENABLED: bool = True
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "alerts@incidentmind.ai"
    SLACK_WEBHOOK_URL: str = ""
    SLACK_DEFAULT_CHANNEL: str = "#incidents-alerts"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_jwt_secret_key(self) -> str:
        if self.JWT_SECRET_KEY:
            return self.JWT_SECRET_KEY
        if self.TESTING:
            return "test_secret_key_for_unit_tests_32_bytes_min"
        return ""

    def get_database_connection_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL

        password_str = (
            f":{self.DATABASE_PASSWORD}" if self.DATABASE_PASSWORD else ""
        )

        return (
            f"postgresql://{self.DATABASE_USER}{password_str}@"
            f"{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            f"?sslmode={self.DATABASE_SSLMODE}"
        )

    def validate_security(self) -> None:
        if not self.TESTING:
            active_key = self.get_jwt_secret_key()

            if (
                not active_key
                or len(active_key.strip()) < 32
                or "default" in active_key.lower()
            ):
                from backend.core.exceptions import ConfigurationError

                raise ConfigurationError(
                    "JWT_SECRET_KEY must be configured with a strong secret "
                    "(min 32 chars) in non-testing environments."
                )


# ---------------------------------------------------------------------------
# Amazon Bedrock / AI configuration
# ---------------------------------------------------------------------------

BEDROCK_REGION: str = os.getenv("AWS_REGION", "us-east-1")

BEDROCK_TEXT_MODEL: str = os.getenv(
    "BEDROCK_TEXT_MODEL",
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
)

BEDROCK_EMBEDDING_MODEL: str = os.getenv(
    "BEDROCK_EMBEDDING_MODEL",
    "amazon.titan-embed-text-v2:0",
)

BEDROCK_MAX_TOKENS: int = int(
    os.getenv("BEDROCK_MAX_TOKENS", "4096")
)

MOCK_BEDROCK: bool = (
    os.getenv("MOCK_BEDROCK", "false").lower() == "true"
)

# ---------------------------------------------------------------------------
# Database / memory configuration
# ---------------------------------------------------------------------------

USE_REAL_DB: bool = (
    os.getenv("USE_REAL_DB", "false").lower() == "true"
)

MEMORY_RETRIEVAL_TOP_K: int = int(
    os.getenv("MEMORY_RETRIEVAL_TOP_K", "10")
)


# ---------------------------------------------------------------------------
# Outcome-aware ranking configuration
# ---------------------------------------------------------------------------

@dataclass
class RankingConfig:
    """Configurable weights for outcome-aware solution ranking."""

    weight_similarity: float = field(
        default_factory=lambda: float(
            os.getenv("WEIGHT_SIMILARITY", "0.4")
        )
    )

    weight_success: float = field(
        default_factory=lambda: float(
            os.getenv("WEIGHT_SUCCESS", "1.0")
        )
    )

    weight_failure: float = field(
        default_factory=lambda: float(
            os.getenv("WEIGHT_FAILURE", "-1.5")
        )
    )

    weight_partial: float = field(
        default_factory=lambda: float(
            os.getenv("WEIGHT_PARTIAL", "0.3")
        )
    )

    weight_rejected: float = field(
        default_factory=lambda: float(
            os.getenv("WEIGHT_REJECTED", "-0.2")
        )
    )

    weight_unknown: float = 0.0

    weight_context_match: float = field(
        default_factory=lambda: float(
            os.getenv("WEIGHT_CONTEXT_MATCH", "0.5")
        )
    )

    min_similarity_threshold: float = field(
        default_factory=lambda: float(
            os.getenv("MIN_SIMILARITY_THRESHOLD", "0.6")
        )
    )

    confidence_approval_threshold: float = field(
        default_factory=lambda: float(
            os.getenv("CONFIDENCE_APPROVAL_THRESHOLD", "0.55")
        )
    )

    confidence_cold_start_cap: float = field(
        default_factory=lambda: float(
            os.getenv("CONFIDENCE_COLD_START_CAP", "0.2")
        )
    )

    confidence_conflicting_cap: float = field(
        default_factory=lambda: float(
            os.getenv("CONFIDENCE_CONFLICTING_CAP", "0.45")
        )
    )

    confidence_max_cap: float = field(
        default_factory=lambda: float(
            os.getenv("CONFIDENCE_MAX_CAP", "0.95")
        )
    )

    confidence_mock_cap: float = field(
        default_factory=lambda: float(
            os.getenv("CONFIDENCE_MOCK_CAP", "0.6")
        )
    )


def get_ranking_config() -> RankingConfig:
    """Return a RankingConfig populated from environment variables."""
    return RankingConfig()

settings = Settings()
