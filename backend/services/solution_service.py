"""
Service layer for Solution Attempt outcome recording and historical retrieval.

CRITICAL PRODUCT PRINCIPLE:
Solution attempt logs are IMMUTABLE historical records.
Every attempted solution (success, failure, partial, rejected, unknown) creates a NEW attempt record.
Past attempt records are NEVER overwritten or deleted.
"""

from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4
from backend.core.exceptions import NotFoundError
from backend.interfaces.db_interface import IDatabaseRepository
from backend.schemas.solution_attempt import (
    SolutionAttemptCreate,
    SolutionAttemptResponse,
    SolutionOutcomeEnum,
)


class SolutionService:
    def __init__(self, db_repo: IDatabaseRepository):
        self.db_repo = db_repo

    def record_solution_attempt(
        self,
        incident_id: UUID,
        attempt_create: SolutionAttemptCreate,
        performed_by: UUID
    ) -> SolutionAttemptResponse:
        """
        Record a new solution attempt outcome.
        
        CRITICAL RULE:
        Always creates an append-only new record. Never overwrites prior history.
        """
        # Verify incident exists
        incident = self.db_repo.get_incident_by_id(incident_id)
        if not incident:
            raise NotFoundError(f"Incident with ID '{incident_id}' not found")

        attempt_id = uuid4()
        now_iso = datetime.now(timezone.utc).isoformat()

        attempt_data = {
            "id": attempt_id,
            "incident_id": incident_id,
            "solution_text": attempt_create.solution_text,
            "outcome": attempt_create.outcome.value,
            "failure_reason": attempt_create.failure_reason,
            "performed_by": performed_by,
            "execution_duration_ms": attempt_create.execution_duration_ms or 0,
            "confidence_at_execution": attempt_create.confidence_at_execution or 0.0,
            "reward_info": attempt_create.reward_info,
            "created_at": now_iso,
        }

        created_record = self.db_repo.create_solution_attempt(attempt_data)

        return SolutionAttemptResponse(
            id=created_record["id"],
            incident_id=created_record["incident_id"],
            solution_text=created_record["solution_text"],
            outcome=SolutionOutcomeEnum(created_record["outcome"]),
            failure_reason=created_record.get("failure_reason"),
            performed_by=created_record["performed_by"],
            execution_duration_ms=created_record.get("execution_duration_ms", 0),
            confidence_at_execution=created_record.get("confidence_at_execution", 0.0),
            reward_info=created_record.get("reward_info"),
            created_at=datetime.fromisoformat(created_record["created_at"]) if isinstance(created_record["created_at"], str) else created_record["created_at"],
        )

    def get_solution_attempts(self, incident_id: UUID) -> List[SolutionAttemptResponse]:
        """
        Retrieve all historical solution attempts for an incident.
        Preserves complete historical record.
        """
        # Verify incident exists
        incident = self.db_repo.get_incident_by_id(incident_id)
        if not incident:
            raise NotFoundError(f"Incident with ID '{incident_id}' not found")

        records = self.db_repo.get_solution_attempts_by_incident(incident_id)

        return [
            SolutionAttemptResponse(
                id=rec["id"],
                incident_id=rec["incident_id"],
                solution_text=rec["solution_text"],
                outcome=SolutionOutcomeEnum(rec["outcome"]),
                failure_reason=rec.get("failure_reason"),
                performed_by=rec["performed_by"],
                execution_duration_ms=rec.get("execution_duration_ms", 0),
                confidence_at_execution=rec.get("confidence_at_execution", 0.0),
                reward_info=rec.get("reward_info"),
                created_at=datetime.fromisoformat(rec["created_at"]) if isinstance(rec["created_at"], str) else rec["created_at"],
            )
            for rec in records
        ]
