# IncidentMind — Incident Understanding
# Owner: AI / Intelligence layer
#
# Transforms a raw incident report into a structured, searchable representation
# that can be embedded and used for memory retrieval.
#
# Critical rules:
#   - Strictly separates FACTS (extracted from input) from INFERENCES (AI-derived)
#     and UNKNOWN (information not available in input).
#   - Never invents error messages, system names, or context that isn't present.
#   - Structured output is validated via Pydantic; retries once on parse failure.
#   - Input is sanitised against prompt injection before being sent to Bedrock.

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.agents.bedrock_client import BedrockClient, BedrockParseError, get_bedrock_client
from backend.agents.safety_guard import sanitise_input

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output schema (validated by Pydantic)
# ---------------------------------------------------------------------------

class InformationClassification(BaseModel):
    """
    Separates what is known from what is inferred or unknown.
    This distinction must always be preserved in the recommendation output.
    """
    facts: List[str] = Field(
        default_factory=list,
        description="Directly stated in the incident report (title, description, logs).",
    )
    inferences: List[str] = Field(
        default_factory=list,
        description="AI-derived conclusions — NOT confirmed by the incident data.",
    )
    unknown: List[str] = Field(
        default_factory=list,
        description="Information that would help but is absent from the report.",
    )


class IncidentUnderstanding(BaseModel):
    """
    Structured representation of an incident, produced by the LLM.

    'searchable_representation' is the concatenated plain-text string
    used to generate the vector embedding for memory retrieval.
    """
    summary: str = Field(..., description="One-sentence summary of the incident.")
    category: str = Field(..., description="Incident category (e.g. database, network, auth).")
    severity: str = Field(..., description="Severity level extracted from input or inferred.")
    symptoms: List[str] = Field(default_factory=list, description="Observable symptoms.")
    error_messages: List[str] = Field(
        default_factory=list,
        description="Literal error strings extracted from description or logs.",
    )
    technical_entities: List[str] = Field(
        default_factory=list,
        description="Named systems, services, databases, libraries affected.",
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Environment / context metadata (env, region, version, etc.).",
    )
    possible_root_causes: List[str] = Field(
        default_factory=list,
        description="Possible root cause hypotheses — labelled as INFERENCE.",
    )
    searchable_representation: str = Field(
        ...,
        description="Concatenated text optimised for embedding generation.",
    )
    mode: str = Field(default="real", description="Execution mode: 'real' or 'mock'")
    information_classification: InformationClassification = Field(
        default_factory=InformationClassification,
        description="Separates facts, inferences, and unknowns.",
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_UNDERSTANDING_SYSTEM_PROMPT = """\
You are an expert IT incident analyst for IncidentMind.

Your task is to analyse a raw incident report and produce a structured JSON object.

CRITICAL RULES:
1. Never invent information that is not present in the incident report.
2. Clearly separate FACTS (directly in the report) from INFERENCES (your analysis) 
   from UNKNOWN (missing information).
3. Extract error messages VERBATIM from the logs — do not paraphrase them.
4. The 'searchable_representation' field must be a concise, dense plain-text string 
   combining category, symptoms, error messages, and affected systems — optimised for 
   semantic vector search.
5. Return ONLY a valid JSON object. No markdown, no explanation outside JSON.

JSON schema to return:
{
  "summary": "string",
  "category": "string",
  "severity": "string",
  "symptoms": ["string"],
  "error_messages": ["string"],
  "technical_entities": ["string"],
  "context": {},
  "possible_root_causes": ["string (INFERENCE)"],
  "searchable_representation": "string",
  "information_classification": {
    "facts": ["string"],
    "inferences": ["string"],
    "unknown": ["string"]
  }
}
"""


# ---------------------------------------------------------------------------
# Incident understanding engine
# ---------------------------------------------------------------------------

class IncidentUnderstandingEngine:
    """
    Analyses a raw incident report and returns a structured IncidentUnderstanding.
    """

    def __init__(self, bedrock_client: Optional[BedrockClient] = None) -> None:
        self._client = bedrock_client or get_bedrock_client()

    def analyse(
        self,
        title: str,
        description: str,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        logs: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> IncidentUnderstanding:
        """
        Analyse a raw incident and return a structured IncidentUnderstanding.

        Args:
            title:       Short incident title.
            description: Human-written description of the incident.
            severity:    Optional severity label provided by the reporter.
            category:    Optional category label provided by the reporter.
            logs:        Optional raw log snippet attached to the incident.
            environment: Optional environment string (e.g. 'production').

        Returns:
            IncidentUnderstanding validated Pydantic model.

        Raises:
            ValueError:         If title and description are both empty.
            BedrockParseError:  If the LLM fails to return valid structured output
                                after retry. Caller must handle this and fail safely.
        """
        if not title and not description:
            raise ValueError(
                "Incident must have at least a title or a description."
            )

        # --- Input validation ---
        if title is not None and not isinstance(title, str):
            raise ValueError("Incident title must be a string value.")
        if description is not None and not isinstance(description, str):
            raise ValueError("Incident description must be a string value.")

        if title and len(title) > 500:
            raise ValueError("Incident title exceeds maximum allowed length of 500 characters.")
        if description and len(description) > 10000:
            raise ValueError("Incident description exceeds maximum allowed length of 10000 characters.")

        # --- Input sanitisation (prompt injection guard) ---
        safe_title = sanitise_input(title or "")
        safe_description = sanitise_input(description or "")
        safe_logs = sanitise_input(logs or "") if logs else None

        # Truncate logs to prevent excessive token usage
        if safe_logs and len(safe_logs) > 3000:
            safe_logs = safe_logs[:3000] + "\n[LOGS TRUNCATED — original too long]"
            logger.debug("Incident logs truncated to 3000 chars to fit context window.")

        # --- Build prompt ---
        prompt_parts = [
            f"INCIDENT TITLE: {safe_title}",
            f"INCIDENT DESCRIPTION: {safe_description}",
        ]
        if severity:
            prompt_parts.append(f"REPORTER-PROVIDED SEVERITY: {severity}")
        if category:
            prompt_parts.append(f"REPORTER-PROVIDED CATEGORY: {category}")
        if environment:
            prompt_parts.append(f"ENVIRONMENT: {environment}")
        if safe_logs:
            prompt_parts.append(f"ATTACHED LOGS:\n{safe_logs}")

        prompt = "\n\n".join(prompt_parts)

        logger.info(
            "IncidentUnderstandingEngine: analysing incident title=%r severity=%s category=%s",
            safe_title[:80], severity, category,
        )

        try:
            understanding = self._client.generate_text(
                prompt=prompt,
                system_prompt=_UNDERSTANDING_SYSTEM_PROMPT,
                response_model=IncidentUnderstanding,
            )
            understanding.mode = "mock" if self._client.mock_mode else "real"
            logger.info(
                "IncidentUnderstandingEngine: success — category=%s severity=%s "
                "symptoms=%d error_messages=%d mode=%s",
                understanding.category,
                understanding.severity,
                len(understanding.symptoms),
                len(understanding.error_messages),
                understanding.mode,
            )
            return understanding
        except BedrockParseError:
            # Re-raise — caller (orchestrator) decides how to handle.
            logger.error(
                "IncidentUnderstandingEngine: LLM parse failure for incident title=%r. "
                "Propagating error to orchestrator.",
                safe_title[:80],
            )
            raise
