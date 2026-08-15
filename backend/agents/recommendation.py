# IncidentMind — Recommendation Generation
# Owner: AI / Intelligence layer
#
# Produces the final structured recommendation payload combining:
#   - Top-ranked solution from the ranking step
#   - Evidence-grounded confidence score (NOT pure LLM self-report)
#   - AI reasoning summary (from LLM)
#   - Supporting historical evidence (successes AND failures)
#   - Risks, uncertainties, and whether approval is required
#
# Confidence score rules:
#   - Computed PROGRAMMATICALLY from retrieved evidence (see _compute_confidence)
#   - LLM provides reasoning_summary only — it does NOT report the confidence number
#   - Confidence is explicitly lowered when evidence is sparse, conflicting, or absent
#   - approval_required is forced True when confidence < threshold (see config)
#   - Cold start caps confidence at confidence_cold_start_cap (default 0.2)
#   - Conflicting evidence caps confidence at confidence_conflicting_cap (default 0.45)
#
# Critical rules:
#   - Never claim a solution succeeded unless the stored outcome is SUCCESS
#   - Never fabricate historical incidents or outcomes
#   - Clearly separate "AI recommendation" from "historical evidence"
#   - If evidence is weak or conflicting, communicate that clearly

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.agents.bedrock_client import BedrockClient, BedrockParseError, get_bedrock_client
from backend.agents.ranking import RankingResult, RankedSolution
from backend.agents.reasoning import SimilarIncidentReasoningResult
from backend.agents.safety_guard import check_output_for_leakage
from backend.core.config import RankingConfig, get_ranking_config
from backend.memory.retrieval import HistoricalSolutionEvidence, MemoryRetrievalResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Confidence computation (evidence-grounded)
# ---------------------------------------------------------------------------

def _compute_confidence(
    top_solution: Optional[RankedSolution],
    retrieval_result: MemoryRetrievalResult,
    ranking_result: RankingResult,
    config: RankingConfig,
    is_mock: bool = False,
) -> float:
    """
    Compute confidence score programmatically from retrieved evidence.

    This function must NOT be replaced with an LLM self-reported value.
    The LLM is used only for reasoning_summary (natural language explanation).

    Formula (all components are placeholder defaults — see config.py):
      base = max similarity score of top matching incidents (contributes up to 0.5)
      success_boost = success_ratio * 0.45 * volume_scale (volume_scale = min(successes / 5, 1.0))
      failure_penalty = failure_count * 0.1 (no volume scale, asymmetric safety)
      confidence = clip(base + success_boost - failure_penalty, 0.0, effective_cap)

    Caps applied:
      - Cold start (no memory): capped at confidence_cold_start_cap
      - Conflicting evidence: capped at confidence_conflicting_cap
      - Effective cap: min(confidence_mock_cap, confidence_max_cap) if mock else confidence_max_cap

    Returns:
        float in [0.0, 1.0]
    """
    # Cold start — no evidence
    if retrieval_result.cold_start or ranking_result.no_evidence or top_solution is None:
        logger.debug("Confidence: cold start — capping at %.2f", config.confidence_cold_start_cap)
        return config.confidence_cold_start_cap

    succ = top_solution.success_count
    fail = top_solution.failure_count
    sim = top_solution.avg_similarity

    # Base: semantic similarity of best match
    base = sim * 0.5

    # Success boost with volume scaling
    total_decisive = succ + fail
    if total_decisive > 0:
        success_ratio = succ / total_decisive
        volume_scale = min(succ / 5.0, 1.0)
        success_boost = success_ratio * 0.45 * volume_scale
    else:
        success_boost = 0.0

    # Failure penalty (asymmetric safety, raw count is penalized directly)
    failure_penalty = fail * 0.1

    raw_confidence = base + success_boost - failure_penalty
    raw_confidence = max(0.0, raw_confidence)

    # 1. Apply cold start / conflicting evidence caps first
    if ranking_result.has_conflicting_evidence:
        raw_confidence = min(raw_confidence, config.confidence_conflicting_cap)
        logger.debug(
            "Confidence: conflicting evidence detected — capping at %.2f", config.confidence_conflicting_cap
        )

    # 2. Apply effective cap (mock ceiling vs real ceiling)
    effective_cap = config.confidence_max_cap
    if is_mock:
        effective_cap = min(config.confidence_mock_cap, config.confidence_max_cap)

    raw_confidence = min(raw_confidence, effective_cap)

    logger.debug(
        "Confidence: base=%.3f success_boost=%.3f failure_penalty=%.3f => raw=%.3f final=%.3f",
        base, success_boost, failure_penalty, base + success_boost - failure_penalty, raw_confidence,
    )

    return round(raw_confidence, 4)


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    """A single piece of historical evidence supporting or warning against a solution."""
    outcome: str
    solution_text: str
    incident_id: str
    attempt_count: int = 1
    failure_reason: Optional[str] = None
    failure_reasons: List[str] = Field(default_factory=list)
    note: str  # Human-readable summary of what this evidence means


class Recommendation(BaseModel):
    """
    The final structured recommendation returned by the AI layer.

    This is the payload the Backend will return to the Frontend.
    It must clearly separate:
      - recommended_solution: What to do
      - confidence_score:     How confident the AI is (evidence-grounded)
      - reasoning_summary:    Why (AI reasoning, clearly labelled as AI inference)
      - evidence:             Historical facts (clearly labelled as retrieved memory)
      - risks_and_uncertainties: What could go wrong or is unknown
      - approval_required:    Whether a human must approve before execution
    """
    recommended_solution: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning_summary: str
    evidence: List[EvidenceItem] = Field(default_factory=list)
    risks_and_uncertainties: List[str] = Field(default_factory=list)
    approval_required: bool
    approval_reasons: List[str] = Field(default_factory=list)
    conflict_warning: Optional[str] = None
    cold_start: bool = False
    mode: str = Field(..., description="Execution mode: 'real' or 'mock'")
    all_ranked_solutions: List[Dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# System prompt for reasoning summary
# ---------------------------------------------------------------------------

_RECOMMENDATION_SYSTEM_PROMPT = """\
You are an expert IT incident analyst for IncidentMind.

You will be given:
1. The current incident details.
2. The top-ranked solution selected by the system.
3. Historical evidence about this solution (successes, failures, partial, rejected, unknown).
4. Information about whether there are conflicting outcomes.

Your task is to write a clear, honest reasoning_summary explaining:
- Why this solution was selected.
- What historical evidence supports or warns against it.
- Any alternative solutions that were considered but avoided due to failures (explicitly mention 'avoided recommending [solution] due to N recorded failures in similar incidents' where relevant).
- Any important risks or uncertainties.
- Whether the engineer should treat this with high or low confidence.

CRITICAL RULES:
1. Do NOT invent any historical incidents, solutions, or outcomes.
2. If the solution has previously failed, say so clearly — do not hide failures.
3. outcome=UNKNOWN means no evidence exists — do not call it a success.
4. outcome=REJECTED means it was declined, not that it worked.
5. If evidence is weak or conflicting, say so explicitly.
6. Clearly distinguish what is RETRIEVED FACT (past outcome details), what is AI INFERENCE (similarity judgments, applicability assumptions), and what is UNCERTAIN (missing information, outcome conflicts, or low similarity).
7. Never assert that a solution worked unless there is a recorded SUCCESS outcome in the historical evidence.
8. Return ONLY a valid JSON object with a single field "reasoning_summary" (string).
   No markdown. No explanation outside JSON.
"""


def _build_recommendation_prompt(
    incident_title: str,
    incident_description: str,
    top_solution: RankedSolution,
    retrieval_result: MemoryRetrievalResult,
    has_conflict: bool,
    confidence: float,
) -> str:
    lines = [
        f"INCIDENT: {incident_title}",
        f"DESCRIPTION: {incident_description[:400]}",
        "",
        f"TOP-RANKED SOLUTION: {top_solution.solution_text}",
        f"  Score: {top_solution.score:.3f}",
        f"  Evidence: {top_solution.success_count} success, "
        f"{top_solution.failure_count} failure, {top_solution.partial_count} partial, "
        f"{top_solution.rejected_count} rejected, {top_solution.unknown_count} unknown",
        f"  Avg similarity: {top_solution.avg_similarity:.3f}",
        f"  Confidence (computed from evidence): {confidence:.3f}",
    ]

    if top_solution.failure_reasons:
        lines.append(f"  Known failure reasons: {'; '.join(top_solution.failure_reasons[:3])}")

    if has_conflict:
        lines.append("  WARNING: Conflicting evidence — this solution has both successes and failures.")

    if retrieval_result.cold_start:
        lines.append("\nNote: No historical memory exists. This is a cold start recommendation.")

    return "\n".join(lines)


class _ReasoningOutput(BaseModel):
    reasoning_summary: str


# ---------------------------------------------------------------------------
# Recommendation Engine
# ---------------------------------------------------------------------------

class RecommendationEngine:
    """
    Generates the final structured recommendation for an incident.
    """

    def __init__(
        self,
        bedrock_client: Optional[BedrockClient] = None,
        config: Optional[RankingConfig] = None,
    ) -> None:
        self._client = bedrock_client or get_bedrock_client()
        self._config = config or get_ranking_config()

    def generate(
        self,
        incident_title: str,
        incident_description: str,
        incident_severity: str,
        retrieval_result: MemoryRetrievalResult,
        ranking_result: RankingResult,
        reasoning_result: SimilarIncidentReasoningResult,
    ) -> Recommendation:
        """
        Generate a structured recommendation.

        Args:
            incident_title/description/severity: Current incident fields.
            retrieval_result:  Output from MemoryRetrievalEngine.retrieve().
            ranking_result:    Output from SolutionRankingEngine.rank().
            reasoning_result:  Output from SimilarIncidentReasoningEngine.reason().

        Returns:
            Recommendation (always returned, even in cold-start or low-confidence cases).
        """
        config = self._config
        top_solution = ranking_result.ranked_solutions[0] if ranking_result.ranked_solutions else None

        # Compute evidence-grounded confidence
        confidence = _compute_confidence(top_solution, retrieval_result, ranking_result, config, is_mock=self._client.mock_mode)

        # Cold start — no history at all
        if retrieval_result.cold_start or top_solution is None:
            logger.info(
                "RecommendationEngine: cold start — generating low-confidence recommendation."
            )
            reasoning = (
                "Offline Mock Reasoning (Cold Start): No historical incidents or solutions "
                "were retrieved from memory. A manual investigation is recommended to diagnose the issue."
            ) if self._client.mock_mode else (
                "This is the first time a similar incident has been encountered in memory. "
                "There is no historical evidence to support or contradict any specific fix. "
                "Confidence is low. Human review and approval are required."
            )
            return Recommendation(
                recommended_solution=(
                    "No historical solutions found in memory. "
                    "An engineer should investigate this incident manually. "
                    "Common first steps for similar incident categories may apply — "
                    "consult your runbook or escalate."
                ),
                confidence_score=confidence,
                reasoning_summary=reasoning,
                evidence=[],
                risks_and_uncertainties=[
                    "No historical incidents found in memory (cold start).",
                    "This recommendation is based on AI reasoning only — no empirical evidence.",
                    "Resolution outcome is unknown; carefully monitor system after any action.",
                ],
                approval_required=True,
                approval_reasons=["cold_start"],
                cold_start=True,
                mode="mock" if self._client.mock_mode else "real",
            )

        # Build evidence items from retrieval
        evidence_items: List[EvidenceItem] = []
        retrieved_solution_texts = set()

        for hist_ev in retrieval_result.historical_evidence:
            # Group attempts for this incident to collapse them
            groups = {}
            for attempt in hist_ev.solution_attempts:
                retrieved_solution_texts.add(attempt.solution_text)
                key = (attempt.solution_text, attempt.outcome.value)
                if key not in groups:
                    groups[key] = {
                        "solution_text": attempt.solution_text,
                        "outcome": attempt.outcome.value,
                        "incident_id": hist_ev.incident_id,
                        "attempt_count": 0,
                        "failure_reasons": []
                    }
                groups[key]["attempt_count"] += 1
                if attempt.failure_reason:
                    if attempt.failure_reason not in groups[key]["failure_reasons"]:
                        groups[key]["failure_reasons"].append(attempt.failure_reason)

            for key, val in groups.items():
                reasons = val["failure_reasons"]
                reasons_str = "; ".join(reasons) if reasons else None
                note = self._outcome_note(val["outcome"], reasons_str, val["attempt_count"])
                evidence_items.append(EvidenceItem(
                    outcome=val["outcome"],
                    solution_text=val["solution_text"],
                    incident_id=val["incident_id"],
                    attempt_count=val["attempt_count"],
                    failure_reason=reasons_str,
                    failure_reasons=reasons,
                    note=note,
                ))

        # Compute risks
        risks = self._compute_risks(
            top_solution=top_solution,
            ranking_result=ranking_result,
            confidence=confidence,
            config=config,
            incident_severity=incident_severity,
        )

        # Generate LLM reasoning summary
        reasoning_summary = self._generate_reasoning_summary(
            incident_title=incident_title,
            incident_description=incident_description,
            top_solution=top_solution,
            retrieval_result=retrieval_result,
            ranking_result=ranking_result,
            confidence=confidence,
        )

        # Determine approval requirement & reasons
        approval_reasons: List[str] = []
        if confidence < config.confidence_approval_threshold:
            approval_reasons.append("low_confidence")
        if ranking_result.has_conflicting_evidence:
            approval_reasons.append("conflicting_evidence")
        if incident_severity.lower() == "critical":
            approval_reasons.append("critical_severity")
        if retrieval_result.cold_start:
            approval_reasons.append("cold_start")

        if ranking_result.ranked_solutions:
            if any(s.failure_count > 0 for s in ranking_result.ranked_solutions):
                approval_reasons.append("similar_solution_has_failure_history")
            if any(s.rejected_count > 0 for s in ranking_result.ranked_solutions):
                approval_reasons.append("similar_solution_has_rejection_history")
            if top_solution and top_solution.avg_similarity < 0.6:
                approval_reasons.append("low_similarity")

        approval_required = len(approval_reasons) > 0

        # Post-generation confidence alignment guard (prevent overstatement when confidence is low)
        low_evidence_words = ["guarantee", "certainly", "proven", "reliable", "100%"]
        if confidence < config.confidence_approval_threshold:
            summary_lower = reasoning_summary.lower()
            if any(w in summary_lower for w in low_evidence_words):
                logger.warning(
                    "SAFETY [overstatement-detected]: LLM output overstates confidence for low evidence. "
                    "Falling back to structured explanation."
                )
                reasoning_summary = (
                    f"Based on historical evidence, '{top_solution.solution_text[:80]}' "
                    f"was selected as the top recommendation (score={top_solution.score:.3f}, "
                    f"successes={top_solution.success_count}, "
                    f"failures={top_solution.failure_count}). "
                    f"Confidence is {confidence:.0%}. "
                    "Warning: LLM reasoning summary overstated confidence and was bypassed."
                )

        # Build all_ranked output for transparency
        all_ranked = [
            {
                "rank": s.rank,
                "solution": s.solution_text[:200],
                "score": s.score,
                "successes": s.success_count,
                "failures": s.failure_count,
                "explanation": s.ranking_explanation[:300],
            }
            for s in ranking_result.ranked_solutions[:5]  # Top 5 only
        ]

        # Safety: check output for leakage before returning
        full_output_text = reasoning_summary + " " + (top_solution.solution_text if top_solution else "")
        leakage_warnings = check_output_for_leakage(full_output_text)
        if leakage_warnings:
            risks.extend(leakage_warnings)

        # Safety: check for UUID fabrication
        from backend.agents.safety_guard import validate_no_fabrication
        retrieved_ids = {ev.incident_id for ev in retrieval_result.historical_evidence}
        retrieved_solutions = {item.solution_text for item in evidence_items}
        fabrication_warnings = validate_no_fabrication(
            recommendation_text=reasoning_summary,
            retrieved_incident_ids=retrieved_ids,
            retrieved_solution_texts=retrieved_solutions,
        )
        if fabrication_warnings:
            risks.extend(fabrication_warnings)

        conflict_warning = None
        if ranking_result.has_conflicting_evidence and top_solution:
            conflict_warning = (
                "CONFLICT WARNING: Historical evidence is contradictory. "
                f"The recommended solution has {top_solution.success_count} success(es) "
                f"AND {top_solution.failure_count} failure(s). "
                "Carefully evaluate whether the current context matches the successful cases."
            )

        rec = Recommendation(
            recommended_solution=top_solution.solution_text if top_solution else "Manual triage required",
            confidence_score=confidence,
            reasoning_summary=reasoning_summary,
            evidence=evidence_items,
            risks_and_uncertainties=risks,
            approval_required=approval_required,
            approval_reasons=approval_reasons,
            conflict_warning=conflict_warning,
            cold_start=retrieval_result.cold_start,
            mode="mock" if self._client.mock_mode else "real",
            all_ranked_solutions=all_ranked,
        )

        logger.info(
            "RecommendationEngine: recommendation generated. "
            "confidence=%.3f approval_required=%s conflict=%s reasons=%s mode=%s",
            confidence, approval_required, ranking_result.has_conflicting_evidence, approval_reasons,
            rec.mode,
        )

        return rec

    def _generate_reasoning_summary(
        self,
        incident_title: str,
        incident_description: str,
        top_solution: RankedSolution,
        retrieval_result: MemoryRetrievalResult,
        ranking_result: RankingResult,
        confidence: float,
    ) -> str:
        """Use LLM to generate a reasoning summary. Falls back to structured text on failure."""
        if self._client.mock_mode:
            fact_text = f"Retrieved Fact: This solution has {top_solution.success_count} success(es) and {top_solution.failure_count} failure(s) recorded in similar past incidents."
            inference_text = f"AI Inference: Based on semantic comparison, the current report is similar (similarity score: {top_solution.avg_similarity:.3f}) to these past cases."

            # Uncertainty
            uncertain_text = ""
            if ranking_result.has_conflicting_evidence:
                uncertain_text = " Uncertainty: The solution has both succeeded and failed previously, introducing outcome conflict."
            elif top_solution.unknown_count > 0:
                uncertain_text = f" Uncertainty: There are {top_solution.unknown_count} attempt(s) with unrecorded/unknown outcomes."
            elif top_solution.avg_similarity < 0.6:
                uncertain_text = " Uncertainty: The similarity to historical reports is low, meaning local context may differ."
            else:
                uncertain_text = " Uncertainty: High similarity and consistent outcomes minimize procedural uncertainty."

            # Avoided solutions check (Defect 3)
            avoided_text = ""
            failed_alternatives = [s for s in ranking_result.ranked_solutions[1:] if s.failure_count > 0]
            if failed_alternatives:
                alt = failed_alternatives[0]
                avoided_text = f" Avoided recommending '{alt.solution_text}' due to {alt.failure_count} recorded failures in similar incidents."

            return (
                f"Offline Mock Reasoning: Top-ranked solution '{top_solution.solution_text}' selected (score: {top_solution.score:.3f}). "
                f"{fact_text} {inference_text}{uncertain_text}{avoided_text}"
            )

        prompt = _build_recommendation_prompt(
            incident_title=incident_title,
            incident_description=incident_description,
            top_solution=top_solution,
            retrieval_result=retrieval_result,
            has_conflict=ranking_result.has_conflicting_evidence,
            confidence=confidence,
        )

        try:
            result = self._client.generate_text(
                prompt=prompt,
                system_prompt=_RECOMMENDATION_SYSTEM_PROMPT,
                response_model=_ReasoningOutput,
            )
            return result.reasoning_summary
        except BedrockParseError as exc:
            logger.warning(
                "RecommendationEngine: LLM reasoning summary failed (%s). "
                "Using structured fallback.",
                exc,
            )
            # Avoided alternatives in fallback
            avoided_text = ""
            failed_alternatives = [s for s in ranking_result.ranked_solutions[1:] if s.failure_count > 0]
            if failed_alternatives:
                alt = failed_alternatives[0]
                avoided_text = f" Avoided recommending '{alt.solution_text[:40]}' due to {alt.failure_count} recorded failures in similar incidents."

            # Structured fallback — never fabricates, never crashes
            return (
                f"Based on historical evidence, '{top_solution.solution_text[:80]}' "
                f"was selected as the top recommendation (score={top_solution.score:.3f}, "
                f"successes={top_solution.success_count}, "
                f"failures={top_solution.failure_count}). "
                f"Confidence is {confidence:.0%}. "
                + avoided_text
                + ("Conflicting evidence detected — human review is advised. "
                   if ranking_result.has_conflicting_evidence else "")
                + ("Note: LLM reasoning summary unavailable due to parse error.")
            )

    @staticmethod
    def _outcome_note(outcome: str, failure_reason: Optional[str], attempt_count: int = 1) -> str:
        count_str = f" {attempt_count} times" if attempt_count > 1 else ""
        notes = {
            "success": f"This solution resolved a similar incident{count_str}.",
            "failure": f"This solution FAILED on a similar incident{count_str}."
                       + (f" Reason: {failure_reason}" if failure_reason else ""),
            "partial": f"This solution partially improved a similar incident{count_str} but did not fully resolve it.",
            "rejected": f"This solution was proposed but rejected (not executed) for a similar incident{count_str}.",
            "unknown": f"The outcome for this solution on a similar incident was unknown (no result recorded){count_str}.",
        }
        return notes.get(outcome, f"Outcome: {outcome}{count_str}")

    @staticmethod
    def _compute_risks(
        top_solution: RankedSolution,
        ranking_result: RankingResult,
        confidence: float,
        config: RankingConfig,
        incident_severity: Optional[str] = None,
    ) -> List[str]:
        risks = []
        if top_solution.failure_count > 0:
            risks.append(
                f"This solution has previously FAILED {top_solution.failure_count}x in similar incidents. "
                "Carefully verify that the current context differs from those failed cases."
            )
        if top_solution.rejected_count > 0:
            risks.append(
                f"This solution was rejected {top_solution.rejected_count}x — "
                "an engineer previously deemed it unsuitable."
            )
        if confidence < config.confidence_approval_threshold:
            risks.append(
                f"Low confidence ({confidence:.0%}) — insufficient historical evidence "
                "to make a high-confidence recommendation."
            )
        if ranking_result.has_conflicting_evidence:
            risks.append(
                "Conflicting historical evidence exists — the same solution has both "
                "successes and failures in similar incidents."
            )
        if top_solution.unknown_count > 0:
            risks.append(
                f"{top_solution.unknown_count} outcome(s) for this solution are UNKNOWN "
                "— cannot be treated as evidence of success."
            )
        if top_solution.avg_similarity < 0.6:
            risks.append(
                f"Low similarity ({top_solution.avg_similarity:.2f}) — the historical incident "
                "differs significantly from the current report."
            )
        if incident_severity and incident_severity.lower() == "critical":
            risks.append(
                "Critical incident severity — high impact if recommendation fails."
            )
        return risks
