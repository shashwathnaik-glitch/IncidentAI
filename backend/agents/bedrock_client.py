# IncidentMind — Amazon Bedrock Client
# Owner: AI / Intelligence layer
#
# Provides all AI model interactions:
#   - generate_text:      invoke LLM for reasoning / structured JSON output
#   - generate_embedding: invoke embedding model to produce a vector
#
# Safety rules:
#   - Never log raw prompt content at INFO or above (may contain incident data)
#   - Never log API keys or AWS credentials
#   - Supports MOCK_BEDROCK=true for offline development and CI
#   - Structured output path validates via Pydantic; retries once on parse failure
#   - Falls back to a clean error (never fabricates a response)

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Type, TypeVar

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from pydantic import BaseModel, ValidationError

from backend.core.config import (
    BEDROCK_EMBEDDING_MODEL,
    BEDROCK_MAX_TOKENS,
    BEDROCK_REGION,
    BEDROCK_TEXT_MODEL,
    MOCK_BEDROCK,
    MOCK_EMBEDDINGS,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class BedrockError(Exception):
    """Base exception for Bedrock client errors."""


class BedrockParseError(BedrockError):
    """Raised when the LLM response cannot be parsed into the expected schema."""


class BedrockCredentialError(BedrockError):
    """Raised when AWS credentials are missing or invalid."""


class BedrockUnavailableError(BedrockError):
    """Raised when Bedrock service is unavailable or times out."""


# ---------------------------------------------------------------------------
# Mock responses (offline mode)
# ---------------------------------------------------------------------------

_MOCK_EMBEDDING_DIM = 1024  # Match titan-embed-text-v2 dimensions

def _mock_embedding(text: str) -> List[float]:
    """
    Deterministic mock embedding based on text hash and semantic categories.
    Different texts will produce meaningfully different vectors, but semantically
    similar texts sharing keyword categories will return realistic relative
    cosine similarity scores (e.g. 0.4 to 0.85).
    """
    import hashlib
    import math

    # 1. Generate the unique vector for this exact text
    seed_unique = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)
    rng_unique = __import__("random").Random(seed_unique)
    unique_vec = [rng_unique.gauss(0, 1) for _ in range(_MOCK_EMBEDDING_DIM)]
    mag_unique = math.sqrt(sum(x * x for x in unique_vec))
    unique_vec = [x / mag_unique for x in unique_vec]

    # 2. Check for keyword categories
    categories = {
        "postgres_db": [
            "postgres", "postgresql", "5432", "database refusing", "connection pool",
            "econnrefused", "active clients", "too many connections", "max_connections",
            "database session", "establish postgresql sessions"
        ],
        "auth_service": [
            "auth", "authentication", "login", "credentials", "jwt", "token", "unauthorized"
        ],
        "memory_oom": [
            "oom", "out of memory", "memory leak", "heap", "garbage collection", "ram"
        ]
    }

    matched_categories = []
    text_lower = text.lower()
    for cat_name, keywords in categories.items():
        if any(kw in text_lower for kw in keywords):
            matched_categories.append(cat_name)

    if not matched_categories:
        # Fallback case: return the unique normalized random vector for this text.
        return unique_vec

    # 3. Blending with matched category vectors
    blend_vec = [0.0] * _MOCK_EMBEDDING_DIM
    for cat_name in matched_categories:
        seed_cat = int(hashlib.sha256(cat_name.encode()).hexdigest(), 16) % (2**32)
        rng_cat = __import__("random").Random(seed_cat)
        cat_vec = [rng_cat.gauss(0, 1) for _ in range(_MOCK_EMBEDDING_DIM)]
        mag_cat = math.sqrt(sum(x * x for x in cat_vec))
        for i in range(_MOCK_EMBEDDING_DIM):
            blend_vec[i] += cat_vec[i] / mag_cat

    # Normalise blend_vec
    mag_blend = math.sqrt(sum(x * x for x in blend_vec))
    blend_vec = [x / mag_blend for x in blend_vec]

    # 4. Blend unique_vec and blend_vec
    # alpha = sqrt(0.7) ≈ 0.8366 ensures that two different texts in the same category
    # will have a cosine similarity of around 0.70.
    alpha = 0.8366
    beta = math.sqrt(1.0 - alpha * alpha)

    final_vec = [alpha * blend_vec[i] + beta * unique_vec[i] for i in range(_MOCK_EMBEDDING_DIM)]

    # Normalise final vector to unit sphere
    mag_final = math.sqrt(sum(x * x for x in final_vec))
    return [x / mag_final for x in final_vec]


def _mock_generate_text(prompt: str, system_prompt: Optional[str]) -> str:
    """
    Returns a minimal valid JSON structure for offline testing.
    The shape mirrors what each component expects so that downstream
    Pydantic validation passes in mock mode.
    """
    # Return a generic structured placeholder; test code should override
    # this with specific mock fixtures when precise output is needed.
    return json.dumps({
        # Fields for IncidentUnderstanding
        "summary": "[MOCK] Incident summary not available (offline mode)",
        "category": "unknown",
        "severity": "unknown",
        "symptoms": [],
        "error_messages": [],
        "technical_entities": [],
        "context": {},
        "searchable_representation": prompt[:200],
        "possible_root_causes": [],
        "information_classification": {
            "facts": [],
            "inferences": [],
            "unknown": ["All fields — operating in offline MOCK_BEDROCK mode"]
        },
        # Fields for SimilarIncidentReasoningResult and _ReasoningOutput
        "incident_assessments": [],
        "conflict_detected": False,
        "no_useful_matches": False,
        "reasoning_summary": "[MOCK] No LLM reasoning available (offline mode)",
        "cold_start": True,
        # Fields for recommendation logic fallback checks
        "similar_incidents": [],
        "ranked_solutions": [],
        "recommended_solution": "[MOCK] No recommendation available (offline mode)",
        "confidence_factors": {},
        "risks": [],
        "approval_required": True,
    })


# ---------------------------------------------------------------------------
# Bedrock Client
# ---------------------------------------------------------------------------

class BedrockClient:
    """
    Thin, reusable wrapper around Amazon Bedrock Runtime.

    Usage:
        client = BedrockClient()
        embedding = client.generate_embedding("database connection failure")
        result = client.generate_text("Analyse this incident...", response_model=IncidentUnderstanding)
    """

    def __init__(
        self,
        region: str = BEDROCK_REGION,
        text_model: str = BEDROCK_TEXT_MODEL,
        embedding_model: str = BEDROCK_EMBEDDING_MODEL,
        max_tokens: int = BEDROCK_MAX_TOKENS,
        mock_mode: Optional[bool] = None,
        mock_text_mode: Optional[bool] = None,
        mock_embedding_mode: Optional[bool] = None,
    ) -> None:
        self.region = region
        self.text_model = text_model
        self.embedding_model = embedding_model
        self.max_tokens = max_tokens

        # Backwards compatibility and split modes logic
        if mock_mode is not None:
            self.mock_text_mode = mock_mode
            self.mock_embedding_mode = mock_mode
        else:
            self.mock_text_mode = mock_text_mode if mock_text_mode is not None else MOCK_BEDROCK
            self.mock_embedding_mode = mock_embedding_mode if mock_embedding_mode is not None else MOCK_EMBEDDINGS

        # Deprecated single mock_mode attribute for other clients who access self.mock_mode
        self.mock_mode = self.mock_text_mode and self.mock_embedding_mode

        self._client = None

        if not self.mock_text_mode or not self.mock_embedding_mode:
            self._client = self._create_boto_client()

    def _create_boto_client(self) -> Any:
        """
        Create a boto3 Bedrock Runtime client.
        Uses the standard AWS credential chain:
          1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
          2. ~/.aws/credentials profile
          3. IAM instance role
        Raises BedrockCredentialError if no credentials are found.
        """
        try:
            config = Config(
                region_name=self.region,
                retries={"max_attempts": 3, "mode": "adaptive"},
                connect_timeout=10,
                read_timeout=120,
            )
            client = boto3.client("bedrock-runtime", config=config)
            logger.info("Bedrock client initialised (region=%s, model=%s)", self.region, self.text_model)
            return client
        except NoCredentialsError as exc:
            raise BedrockCredentialError(
                "AWS credentials not found. Set AWS_ACCESS_KEY_ID and "
                "AWS_SECRET_ACCESS_KEY environment variables, configure "
                "~/.aws/credentials, or attach an IAM role. "
                "Set MOCK_BEDROCK=true to run in offline mode."
            ) from exc
        except Exception as exc:
            raise BedrockUnavailableError(
                f"Failed to create Bedrock client: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a vector embedding for the given text.

        Args:
            text: Input text (incident description, solution text, etc.)

        Returns:
            List of floats representing the embedding vector.

        Raises:
            BedrockUnavailableError: If the embedding call fails.
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text.")

        if self.mock_embedding_mode:
            logger.debug("BedrockClient [MOCK]: generating embedding for text length=%d", len(text))
            return _mock_embedding(text)

        try:
            body = json.dumps({"inputText": text})
            response = self._client.invoke_model(
                modelId=self.embedding_model,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            result = json.loads(response["body"].read())
            embedding = result.get("embedding", [])
            if not embedding:
                raise BedrockUnavailableError("Embedding model returned empty vector.")
            logger.debug("Bedrock: generated embedding dim=%d", len(embedding))
            return embedding
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            raise BedrockUnavailableError(
                f"Bedrock embedding call failed (error_code={error_code})"
            ) from exc
        except Exception as exc:
            raise BedrockUnavailableError(
                f"Unexpected error during embedding generation: {type(exc).__name__}"
            ) from exc

    # ------------------------------------------------------------------
    # Text / reasoning generation
    # ------------------------------------------------------------------

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[T]] = None,
    ) -> Any:
        """
        Generate a text response from the LLM.

        If response_model is provided (a Pydantic BaseModel subclass):
          - The response is expected to be valid JSON.
          - It is validated against response_model.
          - On parse/validation failure, the call is retried ONCE.
          - If it fails again, BedrockParseError is raised (never fabricates).
          - Caller must handle BedrockParseError safely.

        If response_model is None:
          - Raw string response is returned.

        Args:
            prompt:         The user/instruction prompt.
            system_prompt:  Optional system-level instruction (Claude-specific).
            response_model: Optional Pydantic model class to validate response.

        Returns:
            Pydantic model instance (if response_model given) or raw str.

        Raises:
            BedrockParseError:       LLM returned unparseable JSON after retry.
            BedrockUnavailableError: Network/service error.
            BedrockCredentialError:  Authentication failure.
        """
        if self.mock_text_mode:
            raw = _mock_generate_text(prompt, system_prompt)
            if response_model is not None:
                return self._parse_with_retry(raw, response_model, prompt, system_prompt, attempt=2)
            return raw

        raw_response = self._invoke_llm(prompt, system_prompt)

        if response_model is not None:
            return self._parse_with_retry(raw_response, response_model, prompt, system_prompt, attempt=1)

        return raw_response

    def _invoke_llm(self, prompt: str, system_prompt: Optional[str]) -> str:
        """Invoke the Bedrock LLM and return the raw text response."""
        messages = [{"role": "user", "content": prompt}]

        body: Dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "messages": messages,
        }
        if system_prompt:
            body["system"] = system_prompt

        try:
            response = self._client.invoke_model(
                modelId=self.text_model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            result = json.loads(response["body"].read())
            content = result.get("content", [])
            if not content:
                raise BedrockUnavailableError("LLM returned empty content.")
            text = content[0].get("text", "")
            if not text:
                raise BedrockUnavailableError("LLM returned empty text block.")
            return text
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            raise BedrockUnavailableError(
                f"Bedrock LLM call failed (error_code={error_code})"
            ) from exc
        except BedrockUnavailableError:
            raise
        except Exception as exc:
            raise BedrockUnavailableError(
                f"Unexpected error during LLM generation: {type(exc).__name__}"
            ) from exc

    def _parse_with_retry(
        self,
        raw: str,
        response_model: Type[T],
        prompt: str,
        system_prompt: Optional[str],
        attempt: int,
    ) -> T:
        """
        Attempt to parse raw LLM output into response_model.

        Strategy:
          - Attempt 1: parse directly.
          - If parse fails and we have a live client, retry the LLM call once.
          - If parse fails again (attempt 2): raise BedrockParseError cleanly.
          - NEVER return a fabricated fallback response.
        """
        try:
            return self._extract_and_validate(raw, response_model)
        except (BedrockParseError, ValidationError, json.JSONDecodeError) as exc:
            if attempt >= 2 or self.mock_mode:
                # Second failure or mock mode — fail cleanly, do not fabricate
                raise BedrockParseError(
                    f"LLM response could not be parsed into {response_model.__name__} "
                    f"after {'mock attempt' if self.mock_mode else '2 attempts'}. "
                    f"Error: {exc}"
                ) from exc

            logger.warning(
                "BedrockClient: parse failure on attempt %d for model %s. "
                "Retrying once. (parse error: %s)",
                attempt, response_model.__name__, type(exc).__name__,
            )
            time.sleep(1)  # Brief back-off before retry
            raw = self._invoke_llm(prompt, system_prompt)
            return self._parse_with_retry(raw, response_model, prompt, system_prompt, attempt=2)

    @staticmethod
    def _extract_and_validate(raw: str, response_model: Type[T]) -> T:
        """
        Extract JSON from the raw LLM text and validate against response_model.

        Handles LLM output that may wrap JSON in markdown code fences.
        """
        text = raw.strip()

        # Strip markdown code fences if present (```json ... ```)
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last fence lines
            inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            text = "\n".join(inner).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise BedrockParseError(
                f"JSON decode failed: {exc}. Raw text starts with: {raw[:200]!r}"
            ) from exc

        try:
            return response_model.model_validate(data)
        except ValidationError as exc:
            raise BedrockParseError(
                f"Schema validation failed for {response_model.__name__}: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_client_instance: Optional[BedrockClient] = None


def get_bedrock_client() -> BedrockClient:
    """
    Return the shared BedrockClient singleton.
    Creates it on first call.  Safe to call multiple times.
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = BedrockClient()
    return _client_instance


def reset_bedrock_client() -> None:
    """Reset the singleton (for testing)."""
    global _client_instance
    _client_instance = None
