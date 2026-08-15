"""
Production CockroachDB Repository implementation for IncidentMind Backend.

This repository connects to CockroachDB (PostgreSQL wire protocol port 26257)
and implements IDatabaseRepository data access contracts.
Database credentials and connection strings are read securely from environment settings.
Secrets are never logged or exposed in exception tracebacks.
"""

from datetime import datetime, timezone
import json
from typing import Dict, List, Optional
from uuid import UUID, uuid4
import psycopg2
from psycopg2.extras import RealDictCursor
from backend.core.config import settings
from backend.core.exceptions import ConfigurationError, IncidentAIException
from backend.interfaces.db_interface import IDatabaseRepository, UserRecord


class CockroachDBRepository(IDatabaseRepository):
    """CockroachDB production repository implementation."""

    _SEVERITY_APP_TO_DB = {
        "P1": "critical",
        "P2": "high",
        "P3": "medium",
        "P4": "low",
    }
    _SEVERITY_DB_TO_APP = {
        "critical": "P1",
        "high": "P2",
        "medium": "P3",
        "low": "P4",
    }
    _STATUS_APP_TO_DB = {
        "open": "active",
        "investigating": "investigating",
        "resolved": "resolved",
        "closed": "closed",
    }
    _STATUS_DB_TO_APP = {
        "active": "open",
        "investigating": "investigating",
        "resolved": "resolved",
        "closed": "closed",
    }

    def __init__(self, connection_url: Optional[str] = None):
        self.connection_url = connection_url or settings.get_database_connection_url()

    def _get_connection(self):
        """Establish connection to CockroachDB cluster."""
        try:
            conn = psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor)
            return conn
        except Exception as err:
            # Raise ConfigurationError without leaking connection URL or credentials
            raise ConfigurationError(f"Failed to connect to CockroachDB database instance: {type(err).__name__}")

    def check_connection_health(self) -> bool:
        """Ping database with SELECT 1 to verify active connection health."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    result = cur.fetchone()
                    return result is not None
        except Exception:
            return False

    def get_user_by_email(self, email: str) -> Optional[UserRecord]:
        """Retrieve user record by email address."""
        query = "SELECT id, email, password_hash, name, role, department, created_at FROM users WHERE email = %s;"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (email,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    return UserRecord(
                        user_id=UUID(str(row["id"])),
                        email=row["email"],
                        password_hash=row["password_hash"],
                        name=row["name"],
                        role=row["role"],
                        department=row["department"],
                        created_at=str(row["created_at"])
                    )
        except ConfigurationError:
            raise
        except Exception as err:
            raise IncidentAIException(f"Database query error retrieving user by email: {type(err).__name__}")

    def get_user_by_id(self, user_id: UUID) -> Optional[UserRecord]:
        """Retrieve user record by unique UUID."""
        query = "SELECT id, email, password_hash, name, role, department, created_at FROM users WHERE id = %s;"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (str(user_id),))
                    row = cur.fetchone()
                    if not row:
                        return None
                    return UserRecord(
                        user_id=UUID(str(row["id"])),
                        email=row["email"],
                        password_hash=row["password_hash"],
                        name=row["name"],
                        role=row["role"],
                        department=row["department"],
                        created_at=str(row["created_at"])
                    )
        except ConfigurationError:
            raise
        except Exception as err:
            raise IncidentAIException(f"Database query error retrieving user by ID: {type(err).__name__}")

    def create_incident(self, incident_data: Dict) -> Dict:
        """Create a new incident record in CockroachDB."""
        incident_id = incident_data.get("id", uuid4())
        severity_db = self._SEVERITY_APP_TO_DB.get(incident_data["severity"], incident_data["severity"])
        status_db = self._STATUS_APP_TO_DB.get(incident_data["status"], incident_data["status"])
        query = """
            INSERT INTO incidents (id, title, description, category, severity, status, reported_by, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, title, description, category, severity, status, reported_by, created_at, updated_at;
        """
        params = (
            str(incident_id),
            incident_data["title"],
            incident_data["description"],
            incident_data["category"],
            severity_db,
            status_db,
            str(incident_data["reported_by"]),
            incident_data["created_at"],
            incident_data["updated_at"]
        )
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    row = cur.fetchone()
                    conn.commit()
                    ret = dict(row)
                    ret["severity"] = self._SEVERITY_DB_TO_APP.get(ret["severity"], ret["severity"])
                    ret["status"] = self._STATUS_DB_TO_APP.get(ret["status"], ret["status"])
                    return ret
        except ConfigurationError:
            raise
        except Exception as err:
            raise IncidentAIException(f"Database error creating incident: {type(err).__name__}")

    def get_incident_by_id(self, incident_id: UUID) -> Optional[Dict]:
        """Retrieve incident by ID."""
        query = "SELECT id, title, description, category, severity, status, reported_by, created_at, updated_at FROM incidents WHERE id = %s;"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (str(incident_id),))
                    row = cur.fetchone()
                    if row:
                        ret = dict(row)
                        ret["severity"] = self._SEVERITY_DB_TO_APP.get(ret["severity"], ret["severity"])
                        ret["status"] = self._STATUS_DB_TO_APP.get(ret["status"], ret["status"])
                        return ret
                    return None
        except ConfigurationError:
            raise
        except Exception as err:
            raise IncidentAIException(f"Database error retrieving incident: {type(err).__name__}")

    def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict]:
        """List incidents with optional filtering by status, severity, or category."""
        query = "SELECT id, title, description, category, severity, status, reported_by, created_at, updated_at FROM incidents WHERE 1=1"
        params = []
        if status:
            query += " AND status = %s"
            params.append(self._STATUS_APP_TO_DB.get(status, status))
        if severity:
            query += " AND severity = %s"
            params.append(self._SEVERITY_APP_TO_DB.get(severity, severity))
        if category:
            query += " AND LOWER(category) = LOWER(%s)"
            params.append(category)
        query += " ORDER BY created_at DESC;"

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    rows = cur.fetchall()
                    results = []
                    for r in rows:
                        d = dict(r)
                        d["severity"] = self._SEVERITY_DB_TO_APP.get(d["severity"], d["severity"])
                        d["status"] = self._STATUS_DB_TO_APP.get(d["status"], d["status"])
                        results.append(d)
                    return results
        except ConfigurationError:
            raise
        except Exception as err:
            raise IncidentAIException(f"Database error listing incidents: {type(err).__name__}")

    def update_incident(self, incident_id: UUID, update_data: Dict) -> Optional[Dict]:
        """Update fields of an existing incident record."""
        if not update_data:
            return self.get_incident_by_id(incident_id)

        set_clauses = []
        params = []
        for key, val in update_data.items():
            if key == "severity":
                val = self._SEVERITY_APP_TO_DB.get(val, val)
            elif key == "status":
                val = self._STATUS_APP_TO_DB.get(val, val)
            set_clauses.append(f"{key} = %s")
            params.append(val)
        
        now_iso = datetime.now(timezone.utc).isoformat()
        set_clauses.append("updated_at = %s")
        params.append(now_iso)
        params.append(str(incident_id))

        query = f"UPDATE incidents SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, title, description, category, severity, status, reported_by, created_at, updated_at;"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    row = cur.fetchone()
                    conn.commit()
                    if row:
                        ret = dict(row)
                        ret["severity"] = self._SEVERITY_DB_TO_APP.get(ret["severity"], ret["severity"])
                        ret["status"] = self._STATUS_DB_TO_APP.get(ret["status"], ret["status"])
                        return ret
                    return None
        except ConfigurationError:
            raise
        except Exception as err:
            raise IncidentAIException(f"Database error updating incident: {type(err).__name__}")

    def update_incident_status(self, incident_id: UUID, new_status: str) -> Optional[Dict]:
        """Update incident status in CockroachDB."""
        now_iso = datetime.now(timezone.utc).isoformat()
        status_db = self._STATUS_APP_TO_DB.get(new_status, new_status)
        query = "UPDATE incidents SET status = %s, updated_at = %s WHERE id = %s RETURNING id, title, description, category, severity, status, reported_by, created_at, updated_at;"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (status_db, now_iso, str(incident_id)))
                    row = cur.fetchone()
                    conn.commit()
                    if row:
                        ret = dict(row)
                        ret["severity"] = self._SEVERITY_DB_TO_APP.get(ret["severity"], ret["severity"])
                        ret["status"] = self._STATUS_DB_TO_APP.get(ret["status"], ret["status"])
                        return ret
                    return None
        except ConfigurationError:
            raise
        except Exception as err:
            raise IncidentAIException(f"Database error updating status: {type(err).__name__}")

    def create_solution_attempt(self, attempt_data: Dict) -> Dict:
        """
        Record a new solution attempt.
        CRITICAL RULE: Always append a new attempt record. Never delete or overwrite prior attempt history.
        """
        attempt_id = attempt_data.get("id", uuid4())
        solution_action = attempt_data.get("solution_action") or attempt_data.get("solution_text", "")
        failure_reason = attempt_data.get("notes") or attempt_data.get("failure_reason")
        executed_by = attempt_data.get("executed_by") or attempt_data.get("performed_by")

        query = """
            INSERT INTO solution_attempts (id, incident_id, solution_action, outcome, notes, executed_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, incident_id, solution_action, outcome, notes, executed_by, created_at;
        """
        params = (
            str(attempt_id),
            str(attempt_data["incident_id"]),
            solution_action,
            attempt_data["outcome"],
            failure_reason,
            str(executed_by) if executed_by else None,
            attempt_data["created_at"]
        )
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    row = cur.fetchone()
                    conn.commit()
                    res_dict = dict(row)
                    res_dict["solution_text"] = res_dict.get("solution_action")
                    res_dict["performed_by"] = res_dict.get("executed_by")
                    res_dict["failure_reason"] = res_dict.get("notes")
                    return res_dict
        except ConfigurationError:
            raise
        except Exception as err:
            raise IncidentAIException(f"Database error recording solution attempt: {type(err).__name__}")

    def get_solution_attempts_by_incident(self, incident_id: UUID) -> List[Dict]:
        """Retrieve all solution attempts for an incident ordered by created_at DESC."""
        query = "SELECT id, incident_id, solution_action, outcome, notes, executed_by, created_at FROM solution_attempts WHERE incident_id = %s ORDER BY created_at DESC;"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (str(incident_id),))
                    rows = cur.fetchall()
                    results = []
                    for r in rows:
                        d = dict(r)
                        d["solution_text"] = d.get("solution_action")
                        d["performed_by"] = d.get("executed_by")
                        d["failure_reason"] = d.get("notes")
                        results.append(d)
                    return results
        except ConfigurationError:
            raise
        except Exception as err:
            raise IncidentAIException(f"Database error retrieving solution attempts: {type(err).__name__}")
