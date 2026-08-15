# IncidentMind — End-to-End AI Orchestrator
# Owner: AI / Intelligence layer
#
# Connects all AI components into a single coherent pipeline:
#
#   Incident
#     -> Incident Understanding (extract structure)
#     -> Generate Embedding
#     -> Search Persistent Memory
#     -> Find Similar Incidents
#     -> Retrieve Solution Attempts + Outcomes
#     -> Similar Incident Reasoning
#     -> Outcome-Aware Solution Ranking
#     -> Generate Recommendation
#     -> Explain Recommendation
#     -> Determine Confidence/Risk -> Approval flag if needed
#     -> (After execution) Receive Actual Outcome
#     -> Record Outcome -> Update Memory for future incidents
#
# Principles enforced:
#   - Persistent memory is the source of historical experience
#   - Failed solutions remain valuable negative evidence
#   - Cold-start (no memory) is handled explicitly and honestly
#   - Conflicting evidence is exposed, not hidden
#   - Memory retrieval failures are reported, not silently swallowed
#   - All components are injected (testable without AWS credentials)

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from backend.agents.bedrock_client import BedrockClient, BedrockParseError, get_bedrock_client
from backend.agents.ranking import RankingResult, SolutionRankingEngine
from backend.agents.reasoning import SimilarIncidentReasoningEngine, SimilarIncidentReasoningResult
from backend.agents.recommendation import Recommendation, RecommendationEngine
from backend.agents.safety_guard import sanitise_input
from backend.agents.understanding import IncidentUnderstanding, IncidentUnderstandingEngine
from backend.core.config import RankingConfig, get_ranking_config
from backend.db.interfaces import IncidentRepository, SolutionAttemptRepository
from backend.db.mock_db import get_repositories
from backend.memory.learning import LearningLoopEngine, OutcomeRecord, RecordingResult
from backend.memory.retrieval import MemoryRetrievalEngine, MemoryRetrievalResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------

@dataclass
class AnalysisResult:
    """
    Full result of the AI analysis pipeline for an incident.
    All intermediate outputs are preserved for audit and explainability.
    """
    incident_id: str
    understanding: Optional[IncidentUnderstanding]
    retrieval_result: Optional[MemoryRetrievalResult]
    reasoning_result: Optional[SimilarIncidentReasoningResult]
    ranking_result: Optional[RankingResult]
    recommendation: Optional[Recommendation]
    pipeline_error: Optional[str] = None
    success: bool = True


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class AIOrchestrator:
    """
    Coordinates the full AI incident analysis and recommendation pipeline.

    All components are injected so they can be replaced with mocks in tests
    or with production implementations when the DB is ready.
    """

    def __init__(
        self,
        incident_repo: Optional[IncidentRepository] = None,
        attempt_repo: Optional[SolutionAttemptRepository] = None,
        bedrock_client: Optional[BedrockClient] = None,
        config: Optional[RankingConfig] = None,
    ) -> None:
        # Dependency injection — falls back to factory defaults
        _inc_repo, _att_repo = get_repositories()
        self._incident_repo = incident_repo or _inc_repo
        self._attempt_repo = attempt_repo or _att_repo
        self._bedrock = bedrock_client or get_bedrock_client()
        self._config = config or get_ranking_config()

        # AI components
        self._understanding_engine = IncidentUnderstandingEngine(self._bedrock)
        self._retrieval_engine = MemoryRetrievalEngine(
            self._incident_repo, self._attempt_repo, self._bedrock, self._config
        )
        self._reasoning_engine = SimilarIncidentReasoningEngine(self._bedrock)
        self._ranking_engine = SolutionRankingEngine(self._config)
        self._recommendation_engine = RecommendationEngine(self._bedrock, self._config)
        self._learning_engine = LearningLoopEngine(self._attempt_repo)

    # ------------------------------------------------------------------
    # Main analysis pipeline
    # ------------------------------------------------------------------

    def analyse_incident(
        self,
        incident_id: str,
        title: str,
        description: str,
        severity: str = "unknown",
        category: str = "unknown",
        logs: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Run the full AI analysis pipeline for a new incident.

        Args:
            incident_id:  The incident's ID (from Backend/Database after creation).
            title, description, severity, category, logs, environment:
                          Incident fields from the reporter.

        Returns:
            AnalysisResult with all intermediate and final outputs.
            On pipeline error, returns partial result with pipeline_error set.
        """
        logger.info(
            "AIOrchestrator: starting analysis for incident_id=%s title=%r",
            incident_id, title[:80],
        )

        # --- Step 1: Incident Understanding ---
        try:
            understanding = self._understanding_engine.analyse(
                title=title,
                description=description,
                severity=severity,
                category=category,
                logs=logs,
                environment=environment,
            )
        except BedrockParseError as exc:
            logger.error(
                "AIOrchestrator: incident understanding failed for id=%s: %s",
                incident_id, exc,
            )
            return AnalysisResult(
                incident_id=incident_id,
                understanding=None,
                retrieval_result=None,
                reasoning_result=None,
                ranking_result=None,
                recommendation=None,
                pipeline_error=f"Incident understanding failed: {exc}",
                success=False,
            )
        except ValueError as exc:
            return AnalysisResult(
                incident_id=incident_id,
                understanding=None,
                retrieval_result=None,
                reasoning_result=None,
                ranking_result=None,
                recommendation=None,
                pipeline_error=f"Invalid incident input: {exc}",
                success=False,
            )

        # --- Step 2: Memory Retrieval ---
        retrieval_result = self._retrieval_engine.retrieve(
            searchable_text=understanding.searchable_representation,
        )

        if retrieval_result.retrieval_error:
            logger.warning(
                "AIOrchestrator: memory retrieval error for incident_id=%s: %s",
                incident_id, retrieval_result.retrieval_error,
            )
            # Do NOT abort — continue with empty memory (explicitly acknowledged)

        # --- Step 3: Similar Incident Reasoning ---
        try:
            reasoning_result = self._reasoning_engine.reason(
                current_title=title,
                current_description=description,
                current_category=understanding.category,
                current_severity=understanding.severity,
                current_symptoms=understanding.symptoms,
                retrieval_result=retrieval_result,
            )
        except BedrockParseError as exc:
            logger.warning(
                "AIOrchestrator: reasoning engine parse failure for id=%s: %s. "
                "Continuing with reduced reasoning.",
                incident_id, exc,
            )
            # Degraded mode — proceed without LLM reasoning
            from backend.agents.reasoning import SimilarIncidentReasoningResult
            reasoning_result = SimilarIncidentReasoningResult(
                cold_start=retrieval_result.cold_start,
                no_useful_matches=True,
                reasoning_summary="[Reasoning unavailable due to LLM parse error]",
            )

        # --- Step 4: Outcome-Aware Ranking ---
        ranking_result = self._ranking_engine.rank(retrieval_result)

        # --- Step 5: Recommendation Generation ---
        try:
            recommendation = self._recommendation_engine.generate(
                incident_title=title,
                incident_description=description,
                incident_severity=severity,
                retrieval_result=retrieval_result,
                ranking_result=ranking_result,
                reasoning_result=reasoning_result,
            )
        except Exception as exc:
            logger.error(
                "AIOrchestrator: recommendation generation failed for id=%s: %s",
                incident_id, exc,
            )
            # Last-resort safe fallback
            recommendation = Recommendation(
                recommended_solution="Unable to generate recommendation. Manual investigation required.",
                confidence_score=0.0,
                reasoning_summary=f"Recommendation generation failed: {exc}",
                evidence=[],
                risks_and_uncertainties=["System error during recommendation generation."],
                approval_required=True,
                approval_reasons=["system_failure"],
                cold_start=retrieval_result.cold_start if retrieval_result else True,
            )

        logger.info(
            "AIOrchestrator: analysis complete for incident_id=%s. "
            "confidence=%.3f approval_required=%s",
            incident_id,
            recommendation.confidence_score,
            recommendation.approval_required,
        )

        return AnalysisResult(
            incident_id=incident_id,
            understanding=understanding,
            retrieval_result=retrieval_result,
            reasoning_result=reasoning_result,
            ranking_result=ranking_result,
            recommendation=recommendation,
            success=True,
        )

    # ------------------------------------------------------------------
    # Learning loop (called after execution)
    # ------------------------------------------------------------------

    def record_outcome(self, record: OutcomeRecord) -> RecordingResult:
        """
        Record the actual outcome of a solution attempt after execution.

        This must be called with the REAL outcome from the execution workflow.
        Never call this with an assumed or invented outcome.

        Args:
            record: OutcomeRecord with the actual execution result.

        Returns:
            RecordingResult indicating success or failure of the persistence operation.
        """
        logger.info(
            "AIOrchestrator: recording outcome incident_id=%s outcome=%s",
            record.incident_id, record.outcome.value,
        )
        return self._learning_engine.record_outcome(record)


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def create_orchestrator(
    bedrock_mock_mode: Optional[bool] = None,
) -> AIOrchestrator:
    """
    Create an AIOrchestrator with the standard dependency configuration.

    Args:
        bedrock_mock_mode: Override MOCK_BEDROCK setting if provided.

    Returns:
        Configured AIOrchestrator ready for use.
    """
    from backend.agents.bedrock_client import BedrockClient
    from backend.core.config import MOCK_BEDROCK

    mock = bedrock_mock_mode if bedrock_mock_mode is not None else MOCK_BEDROCK

    client = BedrockClient(mock_mode=mock)
    inc_repo, att_repo = get_repositories()
    config = get_ranking_config()

    return AIOrchestrator(
        incident_repo=inc_repo,
        attempt_repo=att_repo,
        bedrock_client=client,
        config=config,
    )
