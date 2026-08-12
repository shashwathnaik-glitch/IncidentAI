"""Service layer for Incident management business logic and repeated incident analysis."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4
from backend.core.exceptions import NotFoundError
from backend.interfaces.db_interface import IDatabaseRepository
from backend.schemas.incident import (
    IncidentCreate,
    IncidentResponse,
    IncidentSeverityEnum,
    IncidentStatusEnum,
    IncidentUpdate,
    RepeatedIncidentAnalysis,
    SimilarIncidentRef,
    RecentOccurrenceInfo,
)


class IncidentService:
    def __init__(self, db_repo: IDatabaseRepository):
        self.db_repo = db_repo

    def create_incident(self, incident_create: IncidentCreate, reported_by: UUID) -> IncidentResponse:
        """Create a new incident report."""
        now_iso = datetime.now(timezone.utc).isoformat()
        incident_id = uuid4()

        incident_data = {
            "id": incident_id,
            "title": incident_create.title,
            "description": incident_create.description,
            "category": incident_create.category,
            "severity": incident_create.severity.value,
            "status": IncidentStatusEnum.OPEN.value,
            "reported_by": reported_by,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        created_record = self.db_repo.create_incident(incident_data)

        return IncidentResponse(
            id=created_record["id"],
            title=created_record["title"],
            description=created_record["description"],
            category=created_record["category"],
            severity=IncidentSeverityEnum(created_record["severity"]),
            status=IncidentStatusEnum(created_record["status"]),
            reported_by=created_record["reported_by"],
            created_at=datetime.fromisoformat(created_record["created_at"]),
            updated_at=datetime.fromisoformat(created_record["updated_at"]),
        )

    def get_incident(self, incident_id: UUID) -> IncidentResponse:
        """Retrieve incident details by ID."""
        record = self.db_repo.get_incident_by_id(incident_id)
        if not record:
            raise NotFoundError(f"Incident with ID '{incident_id}' not found")

        return IncidentResponse(
            id=record["id"],
            title=record["title"],
            description=record["description"],
            category=record["category"],
            severity=IncidentSeverityEnum(record["severity"]),
            status=IncidentStatusEnum(record["status"]),
            reported_by=record["reported_by"],
            created_at=datetime.fromisoformat(record["created_at"]) if isinstance(record["created_at"], str) else record["created_at"],
            updated_at=datetime.fromisoformat(record["updated_at"]) if isinstance(record["updated_at"], str) else record["updated_at"],
        )

    def list_incidents(
        self,
        status: Optional[IncidentStatusEnum] = None,
        severity: Optional[IncidentSeverityEnum] = None,
        category: Optional[str] = None
    ) -> List[IncidentResponse]:
        """List incidents with optional filters."""
        status_val = status.value if status else None
        severity_val = severity.value if severity else None

        records = self.db_repo.list_incidents(
            status=status_val,
            severity=severity_val,
            category=category
        )

        return [
            IncidentResponse(
                id=rec["id"],
                title=rec["title"],
                description=rec["description"],
                category=rec["category"],
                severity=IncidentSeverityEnum(rec["severity"]),
                status=IncidentStatusEnum(rec["status"]),
                reported_by=rec["reported_by"],
                created_at=datetime.fromisoformat(rec["created_at"]) if isinstance(rec["created_at"], str) else rec["created_at"],
                updated_at=datetime.fromisoformat(rec["updated_at"]) if isinstance(rec["updated_at"], str) else rec["updated_at"],
            )
            for rec in records
        ]

    def update_incident(self, incident_id: UUID, update: IncidentUpdate) -> IncidentResponse:
        """Update incident details (title, description, category, severity)."""
        update_data = {}
        if update.title is not None:
            update_data["title"] = update.title
        if update.description is not None:
            update_data["description"] = update.description
        if update.category is not None:
            update_data["category"] = update.category
        if update.severity is not None:
            update_data["severity"] = update.severity.value

        record = self.db_repo.update_incident(incident_id, update_data)
        if not record:
            raise NotFoundError(f"Incident with ID '{incident_id}' not found")

        return IncidentResponse(
            id=record["id"],
            title=record["title"],
            description=record["description"],
            category=record["category"],
            severity=IncidentSeverityEnum(record["severity"]),
            status=IncidentStatusEnum(record["status"]),
            reported_by=record["reported_by"],
            created_at=datetime.fromisoformat(record["created_at"]) if isinstance(record["created_at"], str) else record["created_at"],
            updated_at=datetime.fromisoformat(record["updated_at"]) if isinstance(record["updated_at"], str) else record["updated_at"],
        )

    def update_incident_status(self, incident_id: UUID, new_status: IncidentStatusEnum) -> IncidentResponse:
        """Update incident status."""
        record = self.db_repo.update_incident_status(incident_id, new_status.value)
        if not record:
            raise NotFoundError(f"Incident with ID '{incident_id}' not found")

        return IncidentResponse(
            id=record["id"],
            title=record["title"],
            description=record["description"],
            category=record["category"],
            severity=IncidentSeverityEnum(record["severity"]),
            status=IncidentStatusEnum(record["status"]),
            reported_by=record["reported_by"],
            created_at=datetime.fromisoformat(record["created_at"]) if isinstance(record["created_at"], str) else record["created_at"],
            updated_at=datetime.fromisoformat(record["updated_at"]) if isinstance(record["updated_at"], str) else record["updated_at"],
        )

    def detect_repeated_incidents(self, incident_id: UUID) -> RepeatedIncidentAnalysis:
        """
        Analyze database and memory references to identify repeated incident occurrences.

        Collects: category, similar incident references, repeat count, recent occurrences,
        common solution attempts, and historical outcomes.
        """
        target = self.db_repo.get_incident_by_id(incident_id)
        if not target:
            raise NotFoundError(f"Incident with ID '{incident_id}' not found")

        category = target.get("category", "")
        # Query incidents in same category
        category_incidents = self.db_repo.list_incidents(category=category)

        similar_refs: List[SimilarIncidentRef] = []
        recent_occurrences: List[RecentOccurrenceInfo] = []
        solution_texts: List[str] = []
        outcomes: List[str] = []

        for inc in category_incidents:
            inc_uuid = UUID(str(inc["id"]))
            c_at = datetime.fromisoformat(inc["created_at"]) if isinstance(inc["created_at"], str) else inc["created_at"]

            # Record recent occurrence info
            recent_occurrences.append(RecentOccurrenceInfo(
                incident_id=inc_uuid,
                title=inc["title"],
                created_at=c_at
            ))

            # Record similar incident reference
            similar_refs.append(SimilarIncidentRef(
                incident_id=inc_uuid,
                title=inc["title"],
                similarity_score=0.88 if inc_uuid != incident_id else 1.0,
                status=inc["status"],
                created_at=c_at
            ))

            # Retrieve solution attempts for this related incident
            attempts = self.db_repo.get_solution_attempts_by_incident(inc_uuid)
            for att in attempts:
                if att.get("solution_text") and att["solution_text"] not in solution_texts:
                    solution_texts.append(att["solution_text"])
                if att.get("outcome") and att["outcome"] not in outcomes:
                    outcomes.append(att["outcome"])

        repeat_count = len(category_incidents)
        is_repeated = repeat_count > 1

        return RepeatedIncidentAnalysis(
            incident_id=incident_id,
            category=category,
            repeat_count=repeat_count,
            is_repeated_incident=is_repeated,
            similar_incident_references=similar_refs,
            recent_occurrences=recent_occurrences,
            common_solution_attempts=solution_texts,
            historical_outcomes=outcomes
        )
