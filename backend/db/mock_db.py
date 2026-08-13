# IncidentMind — In-Memory Mock Database
# Owner: AI / Intelligence layer (temporary; replace with CockroachDB when ready)
#
# PURPOSE:
#   Provides a fully functional in-memory implementation of IncidentRepository
#   and SolutionAttemptRepository so the AI layer can be developed and tested
#   without requiring the real CockroachDB instance.
#
# EXIT PLAN (switching to production DB):
#   1. Database/Cloud team implements CockroachDBIncidentRepository and
#      CockroachDBSolutionAttemptRepository in backend/db/cockroachdb.py.
#   2. Set USE_REAL_DB=true in environment variables.
#   3. get_repositories() factory (below) will automatically inject the real
#      implementations -- no other code changes required.
#   4. Run re-embedding job to regenerate embeddings with production model.
#
# WARNING: This mock is NOT thread-safe and NOT persistent across restarts.
#          It is for local development and testing ONLY.

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from backend.db.interfaces import (
    Incident,
    IncidentRepository,
    SimilarIncidentResult,
    SolutionAttempt,
    SolutionAttemptRepository,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Vector similarity helper
# ---------------------------------------------------------------------------

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    Returns 0.0 if either vector has zero magnitude to avoid division by zero.
    """
    vec_a = np.array(a, dtype=np.float64)
    vec_b = np.array(b, dtype=np.float64)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    val = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
    return min(max(val, -1.0), 1.0)


# ---------------------------------------------------------------------------
# Mock Incident Repository
# ---------------------------------------------------------------------------

class MockIncidentRepository(IncidentRepository):
    """
    In-memory incident store.
    Thread-safety: NOT guaranteed — single-threaded test use only.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Incident] = {}

    def save_incident(self, incident: Incident) -> Incident:
        logger.debug("MockDB: saving incident id=%s", incident.id)
        self._store[incident.id] = incident
        return incident

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        return self._store.get(incident_id)

    def search_similar_incidents(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        min_similarity: float = 0.0,
    ) -> List[SimilarIncidentResult]:
        """
        Brute-force cosine similarity over all stored incidents that have embeddings.
        Returns up to top_k results with similarity >= min_similarity,
        ordered by similarity descending.
        """
        results: List[SimilarIncidentResult] = []

        for incident in self._store.values():
            if incident.embedding is None:
                continue
            sim = _cosine_similarity(query_embedding, incident.embedding)
            if sim >= min_similarity:
                results.append(
                    SimilarIncidentResult(
                        incident=incident,
                        similarity_score=sim,
                        solution_attempts=[],  # Populated by retrieval layer
                    )
                )

        results.sort(key=lambda r: r.similarity_score, reverse=True)
        return results[:top_k]

    def list_incidents(self, limit: int = 50, offset: int = 0) -> List[Incident]:
        all_incidents = sorted(
            self._store.values(), key=lambda i: i.created_at, reverse=True
        )
        return all_incidents[offset : offset + limit]

    def count(self) -> int:
        return len(self._store)


# ---------------------------------------------------------------------------
# Mock Solution Attempt Repository
# ---------------------------------------------------------------------------

class MockSolutionAttemptRepository(SolutionAttemptRepository):
    """
    In-memory solution attempt store.

    ENFORCES the immutability rule: save_attempt always appends; never replaces.
    """

    def __init__(self) -> None:
        # incident_id -> list of attempts (appended, never overwritten)
        self._store: Dict[str, List[SolutionAttempt]] = defaultdict(list)
        # attempt_id -> attempt (for quick lookup)
        self._by_id: Dict[str, SolutionAttempt] = {}

    def save_attempt(self, attempt: SolutionAttempt) -> SolutionAttempt:
        """
        INSERT a new attempt.  NEVER overwrites existing records.
        If an attempt with the same ID already exists, raises ValueError.
        """
        if attempt.id in self._by_id:
            raise ValueError(
                f"Attempt id={attempt.id} already exists. "
                "Memory rule: never overwrite a solution attempt. "
                "Create a new attempt record instead."
            )
        logger.debug(
            "MockDB: saving attempt id=%s incident=%s outcome=%s",
            attempt.id, attempt.incident_id, attempt.outcome,
        )
        self._store[attempt.incident_id].append(attempt)
        self._by_id[attempt.id] = attempt
        return attempt

    def get_attempts_for_incident(self, incident_id: str) -> List[SolutionAttempt]:
        attempts = self._store.get(incident_id, [])
        # Return newest first
        return sorted(attempts, key=lambda a: a.created_at, reverse=True)

    def get_attempts_for_incidents(
        self, incident_ids: List[str]
    ) -> dict:
        return {
            inc_id: self.get_attempts_for_incident(inc_id)
            for inc_id in incident_ids
        }

    def count(self) -> int:
        return sum(len(v) for v in self._store.values())


# ---------------------------------------------------------------------------
# Singleton instances (for use in tests and local runs)
# ---------------------------------------------------------------------------

_incident_repo: Optional[MockIncidentRepository] = None
_attempt_repo: Optional[MockSolutionAttemptRepository] = None


def _get_mock_incident_repository() -> MockIncidentRepository:
    global _incident_repo
    if _incident_repo is None:
        _incident_repo = MockIncidentRepository()
    return _incident_repo


def _get_mock_attempt_repository() -> MockSolutionAttemptRepository:
    global _attempt_repo
    if _attempt_repo is None:
        _attempt_repo = MockSolutionAttemptRepository()
    return _attempt_repo


def reset_mock_repositories() -> None:
    """
    Reset both in-memory stores.
    Call this in test setUp/tearDown to ensure test isolation.
    """
    global _incident_repo, _attempt_repo
    _incident_repo = None
    _attempt_repo = None


# ---------------------------------------------------------------------------
# Repository factory (dependency injection entry point)
# ---------------------------------------------------------------------------

def get_repositories() -> tuple[IncidentRepository, SolutionAttemptRepository]:
    """
    Factory that returns the correct repository implementation based on config.

    USE_REAL_DB=false (default): returns in-memory mock (development/testing)
    USE_REAL_DB=true:            imports and returns CockroachDB implementation

    This is the ONLY place that needs to change when the real DB is ready.
    The orchestrator and all AI components call get_repositories() and never
    instantiate a concrete repository directly.
    """
    import os

    use_real = os.getenv("USE_REAL_DB", "false").lower() == "true"

    if use_real:
        # Database/Cloud team: implement this module and class.
        # MISSING DEPENDENCY — report to Database/Cloud team:
        #   Required: backend/db/cockroachdb.py
        #   Must export: CockroachDBIncidentRepository, CockroachDBSolutionAttemptRepository
        #   Connection string read from: DATABASE_URL env variable
        try:
            from backend.db.cockroachdb import (  # type: ignore
                CockroachDBIncidentRepository,
                CockroachDBSolutionAttemptRepository,
            )

            db_url = os.getenv("DATABASE_URL", "")
            if not db_url:
                raise EnvironmentError(
                    "USE_REAL_DB=true but DATABASE_URL is not set. "
                    "Falling back to mock database."
                )
            return CockroachDBIncidentRepository(db_url), CockroachDBSolutionAttemptRepository(db_url)
        except (ImportError, EnvironmentError) as exc:
            logger.warning(
                "Real DB requested but unavailable (%s). "
                "Falling back to in-memory mock. "
                "This is NOT suitable for production.",
                exc,
            )

    return _get_mock_incident_repository(), _get_mock_attempt_repository()
