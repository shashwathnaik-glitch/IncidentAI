# IncidentMind — AI Safety Guard
# Owner: AI / Intelligence layer
#
# Provides input sanitisation and output validation functions used across the
# AI pipeline to mitigate:
#   - Prompt injection via incident descriptions/logs
#   - PII / credentials leakage into prompts or logs
#   - Hallucination (fabricated historical evidence)
#   - Outcome misclassification (rejected/unknown falsely treated as success)
#
# All functions here are called BEFORE content is sent to Bedrock.
# This module is also used in the safety audit test suite (Step 10/11).

from __future__ import annotations

import logging
import re
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt injection patterns
# ---------------------------------------------------------------------------
# These are common patterns used in prompt injection attacks embedded inside
# user-supplied text (incident titles, descriptions, logs).
# The list is not exhaustive — defence-in-depth is provided by structured
# prompting (always wrapping user content in clearly delimited fields).

_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+(previous|all|the\s+above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(previous|all|the\s+above)\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all|previous)\s+", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"act\s+as\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"</?\s*prompt\s*/?>", re.IGNORECASE),
    re.compile(r"mark\s+this\s+(as\s+)?(resolved|success|fixed)", re.IGNORECASE),
    re.compile(r"bypass\s+(approval|review|check)", re.IGNORECASE),
    re.compile(r"override\s+(approval|safety|confidence)", re.IGNORECASE),
    re.compile(r"set\s+confidence\s*(to|=)\s*[0-9]", re.IGNORECASE),
    re.compile(r"approval_required\s*[=:]\s*false", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# PII / credential patterns  (for log-masking — not sent to Bedrock)
# ---------------------------------------------------------------------------

_SENSITIVE_PATTERNS: List[tuple[str, re.Pattern]] = [
    ("AWS_KEY",      re.compile(r"(?i)(AKIA|ASIA)[A-Z0-9]{16}")),
    ("SECRET_KEY",   re.compile(r"(?i)(aws_secret_access_key|secret[_\s]key)\s*[=:]\s*\S+")),
    ("PASSWORD",     re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*\S+")),
    ("API_KEY",      re.compile(r"(?i)(api[_\-]?key|apikey|access[_\-]?token)\s*[=:]\s*\S+")),
    ("JWT",          re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")),
    ("DB_CONN",      re.compile(r"(?i)(postgres|mysql|cockroach|mongodb|redis)://[^\s]+")),
    ("PRIVATE_KEY",  re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----")),
]


class InjectionDetected(Exception):
    """Raised when prompt injection is detected in user-supplied input."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sanitise_input(text: str, raise_on_injection: bool = False) -> str:
    """
    Sanitise user-supplied input before embedding it in an LLM prompt.

    Steps:
      1. Strip leading/trailing whitespace.
      2. Detect prompt injection patterns.
         - If detected: redact the offending portion and log a WARNING.
         - If raise_on_injection=True: raise InjectionDetected instead.
      3. Mask sensitive credential-like patterns.

    The returned string is safe to embed in a structured prompt field.
    Original content is NOT returned without sanitisation.

    Args:
        text:               Input text (incident title, description, logs).
        raise_on_injection: If True, raises InjectionDetected rather than
                            silently redacting. Use True in strict contexts.

    Returns:
        Sanitised string.
    """
    if not text:
        return text

    result = text.strip()

    # Step 1: Detect and handle injection patterns
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(result)
        if match:
            msg = (
                f"Potential prompt injection detected in input. "
                f"Pattern matched: {pattern.pattern!r} at position {match.start()}."
            )
            logger.warning("SECURITY [prompt-injection]: %s", msg)

            if raise_on_injection:
                raise InjectionDetected(msg)

            # Redact the matched portion
            result = pattern.sub("[REDACTED-INJECTION-ATTEMPT]", result)

    # Step 2: Mask sensitive patterns
    for label, pattern in _SENSITIVE_PATTERNS:
        if pattern.search(result):
            logger.warning(
                "SECURITY [sensitive-data]: potential %s pattern detected in input — masking.",
                label,
            )
            result = pattern.sub(f"[MASKED-{label}]", result)

    return result


def check_output_for_leakage(text: str) -> List[str]:
    """
    Scan AI-generated output for accidental sensitive data leakage.

    Returns a list of warning strings (empty if clean).
    Call before returning AI output to the Backend/Frontend.
    """
    warnings: List[str] = []
    for label, pattern in _SENSITIVE_PATTERNS:
        if pattern.search(text):
            warnings.append(
                f"AI output contains potential {label} pattern — review before exposing to client."
            )
            logger.warning(
                "SECURITY [output-leakage]: %s pattern found in AI output.", label
            )
    return warnings


def validate_no_fabrication(
    recommendation_text: str,
    retrieved_incident_ids: Set[str],
    retrieved_solution_texts: Set[str],
) -> List[str]:
    """
    Basic hallucination guard: check that the recommendation does not reference
    incident IDs or solution texts that were not retrieved from memory.

    This is a structural check, not a semantic one.  It catches cases where
    the LLM inserts its own invented incident IDs or solution steps verbatim.

    Returns a list of issue strings (empty if clean).
    """
    issues: List[str] = []

    # Check for UUID-like strings in the recommendation that don't match retrieved IDs
    uuid_pattern = re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    )
    found_uuids = set(uuid_pattern.findall(recommendation_text))
    invented_ids = found_uuids - retrieved_incident_ids
    if invented_ids:
        issues.append(
            f"AI output references incident IDs not found in memory retrieval: {invented_ids}"
        )
        logger.error(
            "HALLUCINATION GUARD: AI output contains %d unrecognised incident ID(s): %s",
            len(invented_ids), invented_ids,
        )

    return issues


def assert_outcome_not_misclassified(outcome_label: str, description: str) -> None:
    """
    Assert that outcome labels in the recommendation text are not misclassified.
    Specifically:
      - 'unknown' must not be described as 'success' or 'verified'.
      - 'rejected' must not be described as 'executed successfully'.

    Logs a CRITICAL warning if a misclassification is detected.
    Does not raise — the calling audit layer decides severity.

    Returns a list of misclassification warnings.
    """
    issues: List[str] = []

    outcome_lower = outcome_label.lower()
    desc_lower = description.lower()

    if outcome_lower == "unknown":
        misclass_patterns = ["success", "verified", "resolved", "worked", "fixed"]
        for word in misclass_patterns:
            if word in desc_lower:
                issues.append(
                    f"Outcome misclassification: outcome=UNKNOWN but description "
                    f"contains '{word}' — unknown must never be treated as success."
                )
                logger.critical(
                    "SAFETY [outcome-misclassification]: UNKNOWN outcome described as '%s'", word
                )

    elif outcome_lower == "rejected":
        misclass_patterns = ["executed successfully", "fixed", "resolved successfully", "worked"]
        for phrase in misclass_patterns:
            if phrase in desc_lower:
                issues.append(
                    f"Outcome misclassification: outcome=REJECTED but description "
                    f"contains '{phrase}' — rejected is not a successful execution."
                )
                logger.critical(
                    "SAFETY [outcome-misclassification]: REJECTED outcome described as '%s'", phrase
                )

    return issues
