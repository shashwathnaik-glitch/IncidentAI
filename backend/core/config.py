# IncidentMind — Core Configuration
# Owner: AI / Intelligence layer
#
# Centralises all AI-layer settings so that weights, model IDs, and thresholds
# are never hard-coded inside business logic.  Every value marked
# "(placeholder default)" is an initial starting point and should be tuned
# once real production data is available.

from __future__ import annotations

import os
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Amazon Bedrock model identifiers
# ---------------------------------------------------------------------------
BEDROCK_REGION: str = os.getenv("AWS_REGION", "us-east-1")

# Text / reasoning model used for incident understanding, reasoning, and
# recommendation generation.
BEDROCK_TEXT_MODEL: str = os.getenv(
    "BEDROCK_TEXT_MODEL",
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
)

# Embedding model used to generate vector representations of incidents.
# NOTE: titan-embed-text-v2 produces 1024-dim vectors.  If you switch models
# after vectors are already stored you must re-embed all stored incidents.
BEDROCK_EMBEDDING_MODEL: str = os.getenv(
    "BEDROCK_EMBEDDING_MODEL",
    "amazon.titan-embed-text-v2:0",
)

# Maximum tokens the LLM may return for a single response.
BEDROCK_MAX_TOKENS: int = int(os.getenv("BEDROCK_MAX_TOKENS", "4096"))

# Set to "true" to run entirely offline with mock LLM responses.
# Required when AWS credentials are not available (e.g. local CI runs).
MOCK_BEDROCK: bool = os.getenv("MOCK_BEDROCK", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Database / repository settings
# ---------------------------------------------------------------------------
# When USE_REAL_DB=true the orchestrator factory will import and inject the
# real CockroachDB repository instead of the in-memory mock.
# This is the single switch-point for the Backend/Database team to activate
# the production persistence layer.
USE_REAL_DB: bool = os.getenv("USE_REAL_DB", "false").lower() == "true"

DATABASE_URL: str = os.getenv("DATABASE_URL", "")  # CockroachDB connection string

# Number of similar incidents to retrieve from memory.
MEMORY_RETRIEVAL_TOP_K: int = int(os.getenv("MEMORY_RETRIEVAL_TOP_K", "10"))

# ---------------------------------------------------------------------------
# RankingConfig — outcome-aware solution ranking weights
# ---------------------------------------------------------------------------
# ALL magnitudes below are PLACEHOLDER DEFAULTS.
# They define direction (successes help, failures hurt) but the exact numbers
# must be calibrated once real incident data is available.
# Do NOT inline these in ranking logic — always pass a RankingConfig instance.
# ---------------------------------------------------------------------------

@dataclass
class RankingConfig:
    """
    Configurable weights for the outcome-aware solution ranking algorithm.

    Defaults are placeholder values.  Override via environment variables or
    by constructing a custom instance and passing it to the ranker.

    Direction rules (must never change):
      - weight_similarity   > 0  (semantic closeness is positive signal)
      - weight_success      > 0  (historical successes raise priority)
      - weight_failure      < 0  (historical failures lower priority)
      - weight_rejected     < 0  (rejected != successful; mild negative signal)
      - weight_unknown      = 0  (no evidence -> neutral, no adjustment)
      - weight_context_match > 0 (context overlap raises priority)

    'rejected' is treated as a mild negative rather than neutral (unknown)
    because a rejection indicates the solution was actively deemed unsuitable
    or declined.  'unknown' means the outcome was simply never recorded.
    """

    # Semantic similarity contribution (placeholder default: 0.4)
    weight_similarity: float = field(
        default_factory=lambda: float(os.getenv("WEIGHT_SIMILARITY", "0.4"))
    )

    # Per successful historical attempt (placeholder default: +1.0)
    weight_success: float = field(
        default_factory=lambda: float(os.getenv("WEIGHT_SUCCESS", "1.0"))
    )

    # Per failed historical attempt (placeholder default: -1.5)
    weight_failure: float = field(
        default_factory=lambda: float(os.getenv("WEIGHT_FAILURE", "-1.5"))
    )

    # Per partial historical attempt (placeholder default: +0.3)
    weight_partial: float = field(
        default_factory=lambda: float(os.getenv("WEIGHT_PARTIAL", "0.3"))
    )

    # Per rejected attempt — mild negative because rejection signals unsuitability
    # (placeholder default: -0.2)
    weight_rejected: float = field(
        default_factory=lambda: float(os.getenv("WEIGHT_REJECTED", "-0.2"))
    )

    # Unknown outcome — truly neutral, no evidence either way (always 0.0)
    weight_unknown: float = 0.0

    # Context match bonus when the current incident context closely matches
    # the historical incident context (placeholder default: +0.5)
    weight_context_match: float = field(
        default_factory=lambda: float(os.getenv("WEIGHT_CONTEXT_MATCH", "0.5"))
    )

    # Minimum cosine similarity score to consider an incident as a useful match
    # (placeholder default: 0.6)
    min_similarity_threshold: float = field(
        default_factory=lambda: float(os.getenv("MIN_SIMILARITY_THRESHOLD", "0.6"))
    )

    # Confidence thresholds
    # Below this value, approval_required is forced True
    confidence_approval_threshold: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_APPROVAL_THRESHOLD", "0.55"))
    )

    # Maximum confidence when evidence is absent (cold start)
    confidence_cold_start_cap: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_COLD_START_CAP", "0.2"))
    )

    # Maximum confidence when only conflicting evidence exists
    confidence_conflicting_cap: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_CONFLICTING_CAP", "0.45"))
    )

    # Maximum confidence ceiling regardless of evidence volume (placeholder default: 0.95)
    confidence_max_cap: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_MAX_CAP", "0.95"))
    )

    # Maximum confidence ceiling when running in mock mode (placeholder default: 0.6)
    confidence_mock_cap: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_MOCK_CAP", "0.6"))
    )


def get_ranking_config() -> RankingConfig:
    """Return a RankingConfig instance populated from environment variables."""
    return RankingConfig()
