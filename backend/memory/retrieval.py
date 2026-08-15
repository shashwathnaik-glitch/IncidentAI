# IncidentMind — Persistent Memory Retrieval
# Owner: AI / Intelligence layer
#
# Retrieves relevant historical incident experience from persistent memory.
# This is the primary mechanism by which the AI "remembers" past incidents.
#
# What this module does:
#   1. Accepts a searchable text representation of the current incident.
#   2. Generates (or accepts) a vector embedding via Bedrock.
#   3. Queries the IncidentRepository for the top-K similar historical incidents.
#   4. Fetches all associated SolutionAttempts for each matched incident.
#   5. Returns structured historical evidence preserving ALL outcome types:
#      success, failure, partial, rejected, unknown.
#
# Critical rules:
#   - Never fabricate historical evidence.
#   - Never delete or ignore failed solution attempts.
#   - If retrieval fails, report the failure — do not pretend it succeeded.
#   - Returns an empty evidence list for cold-start (no memory exists yet).

from __future__ import annotations

import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from backend.agents.bedrock_client import BedrockClient, BedrockUnavailableError, get_bedrock_client
from backend.core.config import MEMORY_RETRIEVAL_TOP_K, get_ranking_config, RankingConfig
from backend.db.interfaces import (
    Incident,
    IncidentRepository,
    SimilarIncidentResult,
    SolutionAttempt,
    SolutionAttemptRepository,
    SolutionOutcome,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class HistoricalSolutionEvidence(BaseModel):
    """Evidence about a single solution attempt retrieved from memory."""
    attempt_id: str
    solution_text: str
    outcome: SolutionOutcome
    failure_reason: Optional[str] = None
    performed_by: Optional[str] = None
    execution_duration_ms: Optional[int] = None
    confidence_at_execution: Optional[float] = None
    reward_delta: Optional[int] = None
    created_at_iso: str  # ISO 8601 string for serialisation

    @classmethod
    def from_attempt(cls, attempt: SolutionAttempt) -> "HistoricalSolutionEvidence":
        return cls(
            attempt_id=attempt.id,
            solution_text=attempt.solution_text,
            outcome=attempt.outcome,
            failure_reason=attempt.failure_reason,
            performed_by=attempt.performed_by,
            execution_duration_ms=attempt.execution_duration_ms,
            confidence_at_execution=attempt.confidence_at_execution,
            reward_delta=attempt.reward_delta,
            created_at_iso=attempt.created_at.isoformat(),
        )


class HistoricalIncidentEvidence(BaseModel):
    """
    A historical incident retrieved from memory, with its solution history.
    All outcome types are preserved — success, failure, partial, rejected, unknown.
    """
    incident_id: str
    title: str
    description_snippet: str  # First 300 chars only — avoid PII in large descriptions
    severity: str
    category: str
    environment: Optional[str] = None
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    solution_attempts: List[HistoricalSolutionEvidence] = Field(default_factory=list)

    # Outcome summary counts (computed from solution_attempts)
    success_count: int = 0
    failure_count: int = 0
    partial_count: int = 0
    rejected_count: int = 0
    unknown_count: int = 0
    total_attempts: int = 0

    def compute_outcome_counts(self) -> None:
        """Populate count fields from solution_attempts list."""
        counts = {o: 0 for o in SolutionOutcome}
        for attempt in self.solution_attempts:
            counts[attempt.outcome] = counts.get(attempt.outcome, 0) + 1
        self.success_count = counts[SolutionOutcome.SUCCESS]
        self.failure_count = counts[SolutionOutcome.FAILURE]
        self.partial_count = counts[SolutionOutcome.PARTIAL]
        self.rejected_count = counts[SolutionOutcome.REJECTED]
        self.unknown_count = counts[SolutionOutcome.UNKNOWN]
        self.total_attempts = len(self.solution_attempts)


class MemoryRetrievalResult(BaseModel):
    """
    Full result of a memory retrieval query.

    cold_start=True when no historical incidents exist in memory.
    retrieval_error is set if the database query failed.
    """
    query_text: str
    top_k_requested: int
    retrieved_count: int
    cold_start: bool = False
    retrieval_error: Optional[str] = None
    historical_evidence: List[HistoricalIncidentEvidence] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Memory Retrieval Engine
# ---------------------------------------------------------------------------

class MemoryRetrievalEngine:
    """
    Retrieves similar historical incidents and their solution outcomes from memory.
    """

    def __init__(
        self,
        incident_repo: IncidentRepository,
        attempt_repo: SolutionAttemptRepository,
        bedrock_client: Optional[BedrockClient] = None,
        config: Optional[RankingConfig] = None,
    ) -> None:
        self._incident_repo = incident_repo
        self._attempt_repo = attempt_repo
        self._bedrock = bedrock_client or get_bedrock_client()
        self._config = config or get_ranking_config()

    def retrieve(
        self,
        searchable_text: str,
        top_k: Optional[int] = None,
        precomputed_embedding: Optional[List[float]] = None,
    ) -> MemoryRetrievalResult:
        """
        Retrieve the top-K most similar historical incidents and their solution history.

        Args:
            searchable_text:      Plain-text representation of the current incident.
            top_k:                Override for the default retrieval limit.
            precomputed_embedding: If already computed, skip Bedrock embedding call.

        Returns:
            MemoryRetrievalResult — always returned, even on cold-start or error.
            Never raises; errors are captured in the result object.
        """
        k = top_k or MEMORY_RETRIEVAL_TOP_K
        config = self._config
        min_sim = config.min_similarity_threshold

        # Step 1: Generate embedding
        try:
            embedding = precomputed_embedding or self._bedrock.generate_embedding(searchable_text)
        except BedrockUnavailableError as exc:
            logger.error(
                "MemoryRetrieval: embedding generation failed — cannot search memory. Error: %s",
                exc,
            )
            return MemoryRetrievalResult(
                query_text=searchable_text,
                top_k_requested=k,
                retrieved_count=0,
                retrieval_error=f"Embedding generation failed: {exc}",
            )

        # Step 2: Vector search
        try:
            similar_incidents: List[SimilarIncidentResult] = (
                self._incident_repo.search_similar_incidents(
                    query_embedding=embedding,
                    top_k=k,
                    min_similarity=min_sim,
                )
            )
        except Exception as exc:
            logger.error(
                "MemoryRetrieval: vector search failed — cannot retrieve similar incidents. Error: %s",
                exc,
            )
            return MemoryRetrievalResult(
                query_text=searchable_text,
                top_k_requested=k,
                retrieved_count=0,
                retrieval_error=f"Database vector search failed: {exc}",
            )

        # Cold start — no incidents in memory yet
        if not similar_incidents:
            logger.info(
                "MemoryRetrieval: cold start — no similar incidents found above threshold %.2f",
                min_sim,
            )
            return MemoryRetrievalResult(
                query_text=searchable_text,
                top_k_requested=k,
                retrieved_count=0,
                cold_start=True,
            )

        # Step 3: Batch-fetch solution attempts for all matched incident IDs
        incident_ids = [r.incident.id for r in similar_incidents]
        try:
            attempts_by_incident = self._attempt_repo.get_attempts_for_incidents(incident_ids)
        except Exception as exc:
            logger.error(
                "MemoryRetrieval: failed to fetch solution attempts. Error: %s", exc
            )
            attempts_by_incident = {iid: [] for iid in incident_ids}

        # Step 4: Assemble structured evidence
        evidence: List[HistoricalIncidentEvidence] = []
        for result in similar_incidents:
            incident = result.incident
            attempts = attempts_by_incident.get(incident.id, [])

            hist_attempts = [
                HistoricalSolutionEvidence.from_attempt(a) for a in attempts
            ]

            hist_evidence = HistoricalIncidentEvidence(
                incident_id=incident.id,
                title=incident.title,
                description_snippet=incident.description[:300],
                severity=incident.severity,
                category=incident.category,
                environment=incident.environment,
                similarity_score=result.similarity_score,
                solution_attempts=hist_attempts,
            )
            hist_evidence.compute_outcome_counts()
            evidence.append(hist_evidence)

        logger.info(
            "MemoryRetrieval: retrieved %d historical incidents (top_k=%d, min_sim=%.2f)",
            len(evidence), k, min_sim,
        )

        return MemoryRetrievalResult(
            query_text=searchable_text,
            top_k_requested=k,
            retrieved_count=len(evidence),
            cold_start=False,
            historical_evidence=evidence,
        )
