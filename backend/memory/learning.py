# IncidentMind — Experience Recording / Learning Loop
# Owner: AI / Intelligence layer
#
# Records actual solution outcomes so the AI can learn from experience.
#
# The learning loop completes the cycle:
#   Incident -> Recommendation -> Execution -> ACTUAL OUTCOME -> Record -> Memory
#
# Critical rules:
#   - Outcomes come from real execution — NEVER invented or assumed.
#   - NEVER overwrite a previous solution attempt — always INSERT a new record.
#   - ALL outcome types are preserved: success, failure, partial, rejected, unknown.
#   - Failure is valuable negative evidence and must never be deleted.
#   - If the Backend/Database API is unavailable, report the failure clearly.
#   - After recording, the new attempt is immediately available for future retrieval.

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.db.interfaces import (
    SolutionAttempt,
    SolutionAttemptRepository,
    SolutionOutcome,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Input model for recording an outcome
# ---------------------------------------------------------------------------

class OutcomeRecord(BaseModel):
    """
    Input to the learning loop from the execution workflow.

    All fields except incident_id, solution_text, and outcome are optional.
    The AI must NOT invent values for fields that are not provided.
    """
    incident_id: str
    solution_text: str
    outcome: SolutionOutcome
    failure_reason: Optional[str] = None      # Required if outcome=FAILURE
    performed_by: Optional[str] = None        # User ID or "ai_agent"
    execution_duration_ms: Optional[int] = None
    confidence_at_execution: Optional[float] = None  # Confidence score at time of recommendation
    reward_delta: Optional[int] = None        # From reward system if applicable
    mode: Optional[str] = "real"              # Originating recommendation mode ("real" | "mock")
    approval_required: bool = False           # Whether Prompt 6 flagged this as requiring approval
    approval_reference: Optional[str] = None  # Reference code verifying human approval


class RecordingResult(BaseModel):
    """Result of a learning loop record operation."""
    success: bool
    attempt_id: Optional[str] = None
    error: Optional[str] = None
    message: str


# ---------------------------------------------------------------------------
# Learning Loop Engine
# ---------------------------------------------------------------------------

class LearningLoopEngine:
    """
    Records solution outcomes into persistent memory after execution.

    This engine must be called AFTER the actual execution outcome is known.
    It must NOT be called to record a speculated or assumed outcome.
    """

    def __init__(self, attempt_repo: SolutionAttemptRepository) -> None:
        self._attempt_repo = attempt_repo

    def record_outcome(self, record: OutcomeRecord) -> RecordingResult:
        """
        Record the actual outcome of a solution attempt.

        Args:
            record: OutcomeRecord with real execution data.

        Returns:
            RecordingResult indicating success or failure of the recording.
            Never raises — errors are captured in the result.
        """
        # Validate that required references are present and not empty
        if not record.incident_id or not record.incident_id.strip():
            return RecordingResult(
                success=False,
                error="malformed_input",
                message="incident_id cannot be empty."
            )

        if not record.solution_text or not record.solution_text.strip():
            return RecordingResult(
                success=False,
                error="malformed_input",
                message="solution_text cannot be empty."
            )

        # Validate outcome is a valid SolutionOutcome enum value
        if not isinstance(record.outcome, SolutionOutcome):
            return RecordingResult(
                success=False,
                error="malformed_input",
                message="outcome is not a valid SolutionOutcome."
            )

        # AI-Side Approval Gating
        if record.approval_required and not record.approval_reference:
            logger.error(
                "LearningLoop: rejected outcome write for incident=%s solution=%r — "
                "approval is required but approval_reference is missing.",
                record.incident_id, record.solution_text[:50],
            )
            return RecordingResult(
                success=False,
                error="approval_reference_missing",
                message="Cannot record outcome for a solution that requires approval without an approval_reference."
            )

        # Validate outcome semantics
        if record.outcome == SolutionOutcome.FAILURE and not record.failure_reason:
            logger.warning(
                "LearningLoop: recording FAILURE for incident=%s without failure_reason. "
                "Future recommendations will benefit from a documented failure reason.",
                record.incident_id,
            )

        attempt = SolutionAttempt(
            id=str(uuid.uuid4()),
            incident_id=record.incident_id,
            solution_text=record.solution_text,
            outcome=record.outcome,
            failure_reason=record.failure_reason,
            performed_by=record.performed_by,
            execution_duration_ms=record.execution_duration_ms,
            confidence_at_execution=record.confidence_at_execution,
            reward_delta=record.reward_delta,
            mode=record.mode,
            created_at=datetime.utcnow(),
        )

        try:
            saved = self._attempt_repo.save_attempt(attempt)
            logger.info(
                "LearningLoop: recorded attempt id=%s incident=%s outcome=%s",
                saved.id, record.incident_id, record.outcome.value,
            )
            return RecordingResult(
                success=True,
                attempt_id=saved.id,
                message=(
                    f"Outcome '{record.outcome.value}' recorded for incident {record.incident_id}. "
                    f"Attempt ID: {saved.id}. "
                    f"This experience is now available for future memory retrieval."
                ),
            )
        except ValueError as exc:
            # Attempt ID collision — should not happen with UUID4 but handle safely
            logger.error(
                "LearningLoop: attempt ID collision for incident=%s: %s",
                record.incident_id, exc,
            )
            return RecordingResult(
                success=False,
                error=str(exc),
                message="Failed to record outcome due to attempt ID conflict.",
            )
        except Exception as exc:
            logger.error(
                "LearningLoop: failed to persist outcome for incident=%s outcome=%s. Error: %s",
                record.incident_id, record.outcome.value, exc,
            )
            return RecordingResult(
                success=False,
                error=str(exc),
                message=(
                    f"Failed to persist outcome to database for incident {record.incident_id}. "
                    f"Error: {exc}. "
                    "MISSING DEPENDENCY: If this error is from the real DB, the Database/Cloud team "
                    "must implement SolutionAttemptRepository.save_attempt() with a correct INSERT "
                    "into the solution_attempts table (never UPDATE/UPSERT existing records)."
                ),
            )
