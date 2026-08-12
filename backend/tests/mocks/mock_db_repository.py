"""
Test-only Mock Database Repository.

LOCATION RULE:
This file lives exclusively under tests/mocks/ and is isolated for unit testing.
It is never imported in production startup.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from backend.core.security import get_password_hash
from backend.interfaces.db_interface import IDatabaseRepository, UserRecord


class MockDatabaseRepository(IDatabaseRepository):
    """In-memory database repository for testing."""

    def __init__(self):
        emp_id = UUID("11111111-1111-1111-1111-111111111111")
        admin_id = UUID("22222222-2222-2222-2222-222222222222")

        self.users: Dict[str, UserRecord] = {
            "employee@company.com": UserRecord(
                user_id=emp_id,
                email="employee@company.com",
                password_hash=get_password_hash("Password123!"),
                name="Jane Doe",
                role="employee",
                department="IT Support",
                created_at="2026-01-01T00:00:00Z"
            ),
            "admin@company.com": UserRecord(
                user_id=admin_id,
                email="admin@company.com",
                password_hash=get_password_hash("AdminPassword123!"),
                name="System Admin",
                role="admin",
                department="DevOps",
                created_at="2026-01-01T00:00:00Z"
            )
        }
        self.incidents: Dict[UUID, Dict] = {}
        self.solution_attempts: List[Dict] = []

    def get_user_by_email(self, email: str) -> Optional[UserRecord]:
        return self.users.get(email)

    def get_user_by_id(self, user_id: UUID) -> Optional[UserRecord]:
        for user in self.users.values():
            if user.id == user_id:
                return user
        return None

    def create_incident(self, incident_data: Dict) -> Dict:
        incident_id = incident_data.get("id", uuid4())
        incident_data["id"] = incident_id
        self.incidents[incident_id] = incident_data
        return incident_data

    def get_incident_by_id(self, incident_id: UUID) -> Optional[Dict]:
        return self.incidents.get(incident_id)

    def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict]:
        results = list(self.incidents.values())
        if status:
            results = [inc for inc in results if inc.get("status") == status]
        if severity:
            results = [inc for inc in results if inc.get("severity") == severity]
        if category:
            results = [inc for inc in results if inc.get("category", "").lower() == category.lower()]
        return results

    def update_incident(self, incident_id: UUID, update_data: Dict) -> Optional[Dict]:
        incident = self.incidents.get(incident_id)
        if not incident:
            return None
        for key, value in update_data.items():
            if value is not None:
                incident[key] = value
        incident["updated_at"] = datetime.now(timezone.utc).isoformat()
        return incident

    def update_incident_status(self, incident_id: UUID, new_status: str) -> Optional[Dict]:
        incident = self.incidents.get(incident_id)
        if not incident:
            return None
        incident["status"] = new_status
        incident["updated_at"] = datetime.now(timezone.utc).isoformat()
        return incident

    def create_solution_attempt(self, attempt_data: Dict) -> Dict:
        attempt_id = attempt_data.get("id", uuid4())
        attempt_data["id"] = attempt_id
        self.solution_attempts.append(attempt_data)
        return attempt_data

    def get_solution_attempts_by_incident(self, incident_id: UUID) -> List[Dict]:
        return [att for att in self.solution_attempts if att.get("incident_id") == incident_id]
