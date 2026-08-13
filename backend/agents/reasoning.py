# IncidentMind — Similar Incident Reasoning
# Owner: AI / Intelligence layer
#
# Uses the LLM to reason about WHY retrieved historical incidents are (or are not)
# relevant to the current incident, and what their solution outcomes tell us.
#
# This step sits BETWEEN memory retrieval and ranking.
# Its job is to produce human-readable reasoning that explains:
#   - Which retrieved incidents are genuinely similar (not just semantically close)
#   - What key similarities and differences exist
#   - Why a historical solution might or might not apply
#   - What conflicts exist in the historical evidence
#
# Critical rules:
#   - Does NOT invent historical evidence — only reasons about retrieved data.
#   - Preserves all conflicting outcomes (fix A failed, fix C succeeded).
#   - All outcome claims must reference actual retrieved outcomes only.
#   - Passes ALL outcomes (success, failure, partial, rejected, unknown) to ranking.

from __future__ import annotations

import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from backend.agents.bedrock_client import BedrockClient, BedrockParseError, get_bedrock_client
from backend.memory.retrieval import HistoricalIncidentEvidence, MemoryRetrievalResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------

class SolutionAssessment(BaseModel):
    """Assessment of a specific solution in the context of the current incident."""
    solution_text: str
    historical_outcome_summary: str  # E.g. "succeeded 3x, failed 1x"
    applicability: str               # "high" | "medium" | "low" | "unknown"
    applicability_reason: str        # Why this solution may/may not apply
    key_risks: List[str] = Field(default_factory=list)
    outcome_conflicts: List[str] = Field(default_factory=list)  # E.g. "succeeded in prod, failed in staging"


class HistoricalIncidentAssessment(BaseModel):
    """Reasoning about a single retrieved historical incident."""
    incident_id: str
    incident_title: str
    similarity_score: float
    is_genuinely_relevant: bool
    relevance_explanation: str       # Why it is or is not a useful match
    key_similarities: List[str] = Field(default_factory=list)
    key_differences: List[str] = Field(default_factory=list)
    solution_assessments: List[SolutionAssessment] = Field(default_factory=list)


class SimilarIncidentReasoningResult(BaseModel):
    """
    Full reasoning output from the similar incident reasoning engine.

    conflict_detected=True when historical evidence is contradictory.
    no_useful_matches=True when no retrieved incidents provide actionable insight.
    """
    incident_assessments: List[HistoricalIncidentAssessment] = Field(default_factory=list)
    conflict_detected: bool = False
    no_useful_matches: bool = False
    reasoning_summary: str = ""
    cold_start: bool = False


# ---------------------------------------------------------------------------
# System prompt for reasoning
# ---------------------------------------------------------------------------

_REASONING_SYSTEM_PROMPT = """\
You are an expert IT incident analyst for IncidentMind.

You will be given:
1. A description of a CURRENT incident.
2. A list of HISTORICAL incidents retrieved from memory, with their solution attempts and outcomes.

Your task is to reason about which historical incidents are genuinely useful for resolving
the current incident, and what their solution history tells us.

CRITICAL RULES:
1. NEVER invent historical incidents, solutions, or outcomes. Use ONLY the data provided.
2. PRESERVE all conflicting evidence — if Fix A failed and Fix C succeeded for the same type
   of incident, report BOTH facts explicitly. Do not hide failures.
3. outcome=UNKNOWN means there is no evidence either way — do not treat it as success.
4. outcome=REJECTED means the solution was deemed unsuitable or not executed — 
   do not treat it as a successful execution.
5. outcome=FAILURE is valuable negative evidence — always explain what was tried and why
   it did not work.
6. Be explicit about differences between historical and current incidents that may
   reduce the applicability of historical solutions.
7. Return ONLY valid JSON. No markdown, no explanation outside JSON.

JSON schema to return:
{
  "incident_assessments": [
    {
      "incident_id": "string",
      "incident_title": "string",
      "similarity_score": 0.0,
      "is_genuinely_relevant": true,
      "relevance_explanation": "string",
      "key_similarities": ["string"],
      "key_differences": ["string"],
      "solution_assessments": [
        {
          "solution_text": "string",
          "historical_outcome_summary": "string",
          "applicability": "high|medium|low|unknown",
          "applicability_reason": "string",
          "key_risks": ["string"],
          "outcome_conflicts": ["string"]
        }
      ]
    }
  ],
  "conflict_detected": false,
  "no_useful_matches": false,
  "reasoning_summary": "string",
  "cold_start": false
}
"""


def _build_reasoning_prompt(
    current_title: str,
    current_description: str,
    current_category: str,
    current_severity: str,
    current_symptoms: List[str],
    retrieval_result: MemoryRetrievalResult,
) -> str:
    """Build the reasoning prompt from current incident context and retrieved history."""
    lines = [
        "=== CURRENT INCIDENT ===",
        f"Title: {current_title}",
        f"Category: {current_category}",
        f"Severity: {current_severity}",
        f"Description: {current_description[:500]}",
    ]
    if current_symptoms:
        lines.append(f"Symptoms: {', '.join(current_symptoms)}")

    if retrieval_result.cold_start or not retrieval_result.historical_evidence:
        lines.append("\n=== HISTORICAL MEMORY ===")
        lines.append("No historical incidents found. This is a cold start — no prior experience exists.")
    else:
        lines.append(f"\n=== HISTORICAL MEMORY ({retrieval_result.retrieved_count} incidents retrieved) ===")
        for i, ev in enumerate(retrieval_result.historical_evidence, 1):
            lines.append(f"\n--- Historical Incident {i} ---")
            lines.append(f"ID: {ev.incident_id}")
            lines.append(f"Title: {ev.title}")
            lines.append(f"Category: {ev.category} | Severity: {ev.severity}")
            if ev.environment:
                lines.append(f"Environment: {ev.environment}")
            lines.append(f"Description snippet: {ev.description_snippet}")
            lines.append(f"Similarity score: {ev.similarity_score:.3f}")
            lines.append(f"Outcome summary: {ev.success_count} success, {ev.failure_count} failure, "
                         f"{ev.partial_count} partial, {ev.rejected_count} rejected, {ev.unknown_count} unknown")

            if ev.solution_attempts:
                lines.append("Solution attempts:")
                for j, attempt in enumerate(ev.solution_attempts[:10], 1):  # Cap at 10 per incident
                    lines.append(
                        f"  {j}. [{attempt.outcome.upper()}] {attempt.solution_text[:200]}"
                        + (f" | Failure reason: {attempt.failure_reason}" if attempt.failure_reason else "")
                    )
            else:
                lines.append("Solution attempts: None recorded.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Similar Incident Reasoning Engine
# ---------------------------------------------------------------------------

class SimilarIncidentReasoningEngine:
    """
    Applies LLM reasoning to determine which historical incidents and solutions
    are genuinely useful for the current incident.
    """

    def __init__(self, bedrock_client: Optional[BedrockClient] = None) -> None:
        self._client = bedrock_client or get_bedrock_client()

    def reason(
        self,
        current_title: str,
        current_description: str,
        current_category: str,
        current_severity: str,
        current_symptoms: List[str],
        retrieval_result: MemoryRetrievalResult,
    ) -> SimilarIncidentReasoningResult:
        """
        Generate reasoning about historical incidents relevant to the current one.

        Args:
            current_*:        Fields from the current incident understanding.
            retrieval_result: Output from MemoryRetrievalEngine.retrieve().

        Returns:
            SimilarIncidentReasoningResult with structured assessments.
            On cold-start, returns a result indicating no historical experience.
            On LLM parse failure, raises BedrockParseError for the orchestrator to handle.
        """
        # Handle cold-start without LLM call (no data to reason about)
        if retrieval_result.cold_start or retrieval_result.retrieved_count == 0:
            logger.info(
                "SimilarIncidentReasoning: cold start — returning empty reasoning result."
            )
            return SimilarIncidentReasoningResult(
                cold_start=True,
                no_useful_matches=True,
                reasoning_summary=(
                    "No historical incidents found in memory. "
                    "This is the first time a similar incident has been seen. "
                    "Recommendation will be based on AI reasoning only, without historical evidence."
                ),
            )

        prompt = _build_reasoning_prompt(
            current_title=current_title,
            current_description=current_description,
            current_category=current_category,
            current_severity=current_severity,
            current_symptoms=current_symptoms,
            retrieval_result=retrieval_result,
        )

        logger.info(
            "SimilarIncidentReasoning: reasoning over %d historical incidents.",
            retrieval_result.retrieved_count,
        )

        try:
            result = self._client.generate_text(
                prompt=prompt,
                system_prompt=_REASONING_SYSTEM_PROMPT,
                response_model=SimilarIncidentReasoningResult,
            )
            logger.info(
                "SimilarIncidentReasoning: complete — relevant=%d, conflict=%s, no_useful=%s",
                len(result.incident_assessments),
                result.conflict_detected,
                result.no_useful_matches,
            )
            return result
        except BedrockParseError:
            logger.error(
                "SimilarIncidentReasoning: LLM parse failure. Propagating to orchestrator."
            )
            raise
