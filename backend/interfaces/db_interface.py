"""
Abstract Database Repository Interface.

OWNERSHIP NOTE:
This interface defines the backend contract for database access.
The production CockroachDB repository implementation, connection handling, schema,
and migrations are owned and provided by the Database & Cloud teammate.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from uuid import UUID


class UserRecord(ABC):
    """Data class container for user records returned by repository implementations."""
    def __init__(self, user_id: UUID, email: str, password_hash: str, name: str, role: str, department: str, created_at: str):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.name = name
        self.role = role
        self.department = department
        self.created_at = created_at


class IDatabaseRepository(ABC):
    """
    Interface contract for persistent data access.
    
    Database & Cloud teammate provides the CockroachDB production implementation.
    """
    
    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[UserRecord]:
        """Retrieve user record by email address."""
        pass

    @abstractmethod
    def get_user_by_id(self, user_id: UUID) -> Optional[UserRecord]:
        """Retrieve user record by unique UUID."""
        pass

    @abstractmethod
    def create_incident(self, incident_data: Dict) -> Dict:
        """Create a new incident record."""
        pass

    @abstractmethod
    def get_incident_by_id(self, incident_id: UUID) -> Optional[Dict]:
        """Retrieve incident by ID."""
        pass

    @abstractmethod
    def list_incidents(self, status: Optional[str] = None, severity: Optional[str] = None, category: Optional[str] = None) -> List[Dict]:
        """List incidents with optional filtering by status, severity, or category."""
        pass

    @abstractmethod
    def update_incident(self, incident_id: UUID, update_data: Dict) -> Optional[Dict]:
        """Update fields of an existing incident record."""
        pass

    @abstractmethod
    def update_incident_status(self, incident_id: UUID, new_status: str) -> Optional[Dict]:
        """Update the status of an existing incident."""
        pass

    @abstractmethod
    def create_solution_attempt(self, attempt_data: Dict) -> Dict:
        """
        Record a new solution attempt.
        CRITICAL RULE: Always append a new attempt record. Never delete or overwrite prior attempt history.
        """
        pass

    @abstractmethod
    def get_solution_attempts_by_incident(self, incident_id: UUID) -> List[Dict]:
        """Retrieve all solution attempts for an incident ordered by created_at DESC."""
        pass
