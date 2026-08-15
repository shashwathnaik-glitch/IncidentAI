# IncidentMind — Outcome-Aware Solution Ranking
# Owner: AI / Intelligence layer
#
# Ranks candidate solutions using historical outcome evidence.
# ALL weights are read from RankingConfig — never hard-coded here.
#
# Core principle (must never change):
#   A solution that has failed repeatedly must NOT be blindly recommended again
#   when stronger successful evidence exists for an alternative.
#
# Outcome treatment:
#   SUCCESS  -> positive evidence (weight_success per instance)
#   FAILURE  -> negative evidence (weight_failure per instance, always negative)
#   PARTIAL  -> weak positive evidence (weight_partial)
#   REJECTED -> mild negative signal (weight_rejected < 0)
#              Rationale: rejection signals the solution was deemed unsuitable
#              or declined by an engineer. This is distinct from UNKNOWN.
#   UNKNOWN  -> neutral (weight_unknown = 0.0, no adjustment)
#              Rationale: no evidence either way — cannot infer success or failure.
#
# See backend/core/config.py for all default weights and their rationale.

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.core.config import RankingConfig, get_ranking_config
from backend.db.interfaces import SolutionOutcome
from backend.memory.retrieval import (
    HistoricalIncidentEvidence,
    HistoricalSolutionEvidence,
    MemoryRetrievalResult,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Candidate solution (aggregated across historical incidents)
# ---------------------------------------------------------------------------

@dataclass
class SolutionCandidate:
    """
    A candidate solution aggregated from all historical evidence.
    One candidate may appear in multiple historical incidents.
    """
    solution_text: str

    # Evidence from all historical incidents
    success_count: int = 0
    failure_count: int = 0
    partial_count: int = 0
    rejected_count: int = 0
    unknown_count: int = 0
    total_attempts: int = 0

    # Weighted similarity: average similarity of incidents where this solution appeared
    avg_similarity: float = 0.0

    # Context match score (0.0–1.0, computed separately)
    context_match_score: float = 0.0

    # Final computed score
    score: float = 0.0

    # Breakdown for explainability
    score_breakdown: Dict[str, float] = field(default_factory=dict)

    # Source incident IDs (for hallucination audit)
    source_incident_ids: List[str] = field(default_factory=list)

    # Failure reasons collected
    failure_reasons: List[str] = field(default_factory=list)


@dataclass
class RankedSolution:
    """A ranked solution with full explainability output."""
    rank: int
    solution_text: str
    score: float
    success_count: int
    failure_count: int
    partial_count: int
    rejected_count: int
    unknown_count: int
    total_attempts: int
    avg_similarity: float
    score_breakdown: Dict[str, float]
    failure_reasons: List[str]
    ranking_explanation: str
    source_incident_ids: List[str]


@dataclass
class RankingResult:
    """Full output of the ranking step."""
    ranked_solutions: List[RankedSolution]
    config_used: Dict[str, float]   # Snapshot of weights used (for audit)
    has_conflicting_evidence: bool  # True if any solution has both successes and failures
    no_evidence: bool               # True when memory was empty (cold start)
    ranking_notes: str              # Human-readable summary of the ranking


# ---------------------------------------------------------------------------
# Canonical solution key (for grouping across incidents)
# ---------------------------------------------------------------------------

def _canonical_key(solution_text: str) -> str:
    """
    Normalise a solution text into a grouping key.
    Two solutions that are semantically identical but differ in whitespace/case
    will be grouped together.
    """
    return " ".join(solution_text.lower().strip().split())


# ---------------------------------------------------------------------------
# Ranking engine
# ---------------------------------------------------------------------------

class SolutionRankingEngine:
    """
    Ranks candidate solutions using historical outcome evidence and configurable weights.

    Usage:
        engine = SolutionRankingEngine()
        result = engine.rank(retrieval_result)
    """

    def __init__(self, config: Optional[RankingConfig] = None) -> None:
        self._config = config or get_ranking_config()

    def rank(self, retrieval_result: MemoryRetrievalResult) -> RankingResult:
        """
        Rank all candidate solutions based on retrieved historical evidence.

        Args:
            retrieval_result: Output from MemoryRetrievalEngine.retrieve().

        Returns:
            RankingResult with ranked_solutions ordered highest score first.
        """
        config = self._config
        config_snapshot = {
            "weight_similarity": config.weight_similarity,
            "weight_success": config.weight_success,
            "weight_failure": config.weight_failure,
            "weight_partial": config.weight_partial,
            "weight_rejected": config.weight_rejected,
            "weight_unknown": config.weight_unknown,
            "weight_context_match": config.weight_context_match,
        }

        # Cold start — no historical evidence
        if retrieval_result.cold_start or not retrieval_result.historical_evidence:
            logger.info("SolutionRanking: cold start — no evidence to rank.")
            return RankingResult(
                ranked_solutions=[],
                config_used=config_snapshot,
                has_conflicting_evidence=False,
                no_evidence=True,
                ranking_notes=(
                    "No historical evidence available. "
                    "Cold start: recommendation will be generated from AI reasoning alone."
                ),
            )

        # Step 1: Aggregate solutions across all historical incidents
        candidates: Dict[str, SolutionCandidate] = {}
        similarity_accumulator: Dict[str, List[float]] = defaultdict(list)

        weighted_successes: Dict[str, float] = defaultdict(float)
        weighted_failures: Dict[str, float] = defaultdict(float)
        weighted_partials: Dict[str, float] = defaultdict(float)
        weighted_rejections: Dict[str, float] = defaultdict(float)
        weighted_unknowns: Dict[str, float] = defaultdict(float)

        for hist_evidence in retrieval_result.historical_evidence:
            sim = hist_evidence.similarity_score

            for attempt in hist_evidence.solution_attempts:
                key = _canonical_key(attempt.solution_text)

                if key not in candidates:
                    candidates[key] = SolutionCandidate(solution_text=attempt.solution_text)

                cand = candidates[key]
                cand.total_attempts += 1

                if attempt.outcome == SolutionOutcome.SUCCESS:
                    cand.success_count += 1
                    weighted_successes[key] += sim
                elif attempt.outcome == SolutionOutcome.FAILURE:
                    cand.failure_count += 1
                    weighted_failures[key] += sim
                    if attempt.failure_reason:
                        cand.failure_reasons.append(attempt.failure_reason)
                elif attempt.outcome == SolutionOutcome.PARTIAL:
                    cand.partial_count += 1
                    weighted_partials[key] += sim
                elif attempt.outcome == SolutionOutcome.REJECTED:
                    cand.rejected_count += 1
                    weighted_rejections[key] += sim
                elif attempt.outcome == SolutionOutcome.UNKNOWN:
                    cand.unknown_count += 1
                    weighted_unknowns[key] += sim

                if hist_evidence.incident_id not in cand.source_incident_ids:
                    cand.source_incident_ids.append(hist_evidence.incident_id)

                similarity_accumulator[key].append(sim)

        # Step 2: Compute average similarity per candidate
        for key, sims in similarity_accumulator.items():
            candidates[key].avg_similarity = sum(sims) / len(sims)

        # Step 3: Score each candidate using configurable weights and normalized counts
        import math

        for key, cand in candidates.items():
            n_success = math.sqrt(weighted_successes[key])
            n_failure = math.sqrt(weighted_failures[key])
            n_partial = math.sqrt(weighted_partials[key])
            n_rejected = math.sqrt(weighted_rejections[key])
            n_unknown = math.sqrt(weighted_unknowns[key])

            sim_contrib = cand.avg_similarity * config.weight_similarity
            succ_contrib = n_success * config.weight_success
            fail_contrib = n_failure * config.weight_failure
            part_contrib = n_partial * config.weight_partial
            rej_contrib = n_rejected * config.weight_rejected
            unk_contrib = n_unknown * config.weight_unknown
            ctx_contrib = cand.context_match_score * config.weight_context_match

            cand.score = (
                sim_contrib + succ_contrib + fail_contrib +
                part_contrib + rej_contrib + unk_contrib + ctx_contrib
            )
            cand.score_breakdown = {
                "similarity": round(sim_contrib, 4),
                "success": round(succ_contrib, 4),
                "failure": round(fail_contrib, 4),
                "partial": round(part_contrib, 4),
                "rejected": round(rej_contrib, 4),
                "unknown": round(unk_contrib, 4),
                "context_match": round(ctx_contrib, 4),
                "total": round(cand.score, 4),
            }

        # Step 4: Sort by score descending, breaking ties deterministically by solution text (alphabetical ascending)
        sorted_candidates = sorted(candidates.values(), key=lambda c: c.solution_text)
        sorted_candidates = sorted(sorted_candidates, key=lambda c: c.score, reverse=True)

        # Step 5: Detect conflicting evidence
        has_conflict = any(
            c.success_count > 0 and c.failure_count > 0
            for c in sorted_candidates
        )

        # Step 6: Build RankedSolution output with explainability
        ranked: List[RankedSolution] = []
        for rank_idx, cand in enumerate(sorted_candidates, 1):
            explanation = self._build_explanation(rank_idx, cand, config)
            ranked.append(RankedSolution(
                rank=rank_idx,
                solution_text=cand.solution_text,
                score=round(cand.score, 4),
                success_count=cand.success_count,
                failure_count=cand.failure_count,
                partial_count=cand.partial_count,
                rejected_count=cand.rejected_count,
                unknown_count=cand.unknown_count,
                total_attempts=cand.total_attempts,
                avg_similarity=round(cand.avg_similarity, 4),
                score_breakdown=cand.score_breakdown,
                failure_reasons=cand.failure_reasons,
                ranking_explanation=explanation,
                source_incident_ids=cand.source_incident_ids,
            ))

        logger.info(
            "SolutionRanking: ranked %d candidates. Top: %r (score=%.3f). Conflict: %s",
            len(ranked),
            ranked[0].solution_text[:80] if ranked else "",
            ranked[0].score if ranked else 0.0,
            has_conflict,
        )

        notes = self._build_ranking_notes(ranked, has_conflict)

        return RankingResult(
            ranked_solutions=ranked,
            config_used=config_snapshot,
            has_conflicting_evidence=has_conflict,
            no_evidence=False,
            ranking_notes=notes,
        )

    @staticmethod
    def _build_explanation(rank: int, cand: SolutionCandidate, config: RankingConfig) -> str:
        """Build a human-readable ranking explanation for a candidate."""
        parts = [f"Rank #{rank}: '{cand.solution_text[:100]}'"]
        parts.append(
            f"Score {cand.score:.3f} (similarity={cand.avg_similarity:.3f}, "
            f"successes={cand.success_count}, failures={cand.failure_count}, "
            f"partial={cand.partial_count}, rejected={cand.rejected_count}, "
            f"unknown={cand.unknown_count})"
        )
        succ_val = cand.score_breakdown.get("success", 0.0)
        fail_val = cand.score_breakdown.get("failure", 0.0)
        if cand.success_count > 0:
            parts.append(
                f"Positive evidence: succeeded {cand.success_count}x in similar incidents "
                f"({succ_val:+.2f} score contribution)."
            )
        if cand.failure_count > 0:
            parts.append(
                f"Negative evidence: FAILED {cand.failure_count}x in similar incidents "
                f"({fail_val:.2f} score penalty)."
            )
            if cand.failure_reasons:
                parts.append(f"Known failure reasons: {'; '.join(cand.failure_reasons[:3])}.")
        if cand.partial_count > 0:
            parts.append(
                f"Partial evidence: partially resolved {cand.partial_count}x "
                f"(limited positive signal)."
            )
        if cand.rejected_count > 0:
            parts.append(
                f"Rejected {cand.rejected_count}x (mild negative signal — "
                f"rejection means the solution was deemed unsuitable or not executed, "
                f"not the same as unknown)."
            )
        if cand.unknown_count > 0:
            parts.append(
                f"Unknown outcome {cand.unknown_count}x (neutral — "
                f"no evidence either way, not treated as success)."
            )
        if cand.success_count > 0 and cand.failure_count > 0:
            parts.append(
                "WARNING: Conflicting evidence — this solution has both successes and failures. "
                "Context match is critical before recommending."
            )
        return " | ".join(parts)

    @staticmethod
    def _build_ranking_notes(ranked: List[RankedSolution], has_conflict: bool) -> str:
        if not ranked:
            return "No candidates to rank."
        notes = [f"Ranked {len(ranked)} solution candidate(s)."]
        top = ranked[0]
        notes.append(
            f"Top-ranked: '{top.solution_text[:80]}' (score={top.score:.3f}, "
            f"successes={top.success_count}, failures={top.failure_count})."
        )
        if has_conflict:
            notes.append(
                "Conflicting evidence detected: at least one solution has both "
                "success and failure records. Recommendation includes a warning."
            )
        if len(ranked) > 1:
            bottom = ranked[-1]
            notes.append(
                f"Lowest-ranked: '{bottom.solution_text[:80]}' "
                f"(score={bottom.score:.3f})."
            )
        return " ".join(notes)
