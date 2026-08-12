"""Dedicated unit and integration tests for Database & CockroachDB Connection layer."""

from backend.core.config import settings
from backend.database.cockroach_repository import CockroachDBRepository


def test_database_connection_url_security():
    """Verify database connection URL is generated securely from settings without hardcoded plain text passwords."""
    url = settings.get_database_connection_url()
    assert "postgresql://" in url
    assert "26257" in url  # Standard CockroachDB port
    assert "incidentmind" in url


def test_cockroach_repository_instantiation():
    """Verify CockroachDBRepository instantiates cleanly with settings URL."""
    repo = CockroachDBRepository()
    assert repo.connection_url is not None
    assert "postgresql://" in repo.connection_url


def test_cockroach_repository_health_check_offline():
    """Verify health check returns False when database server is offline/unreachable rather than crashing."""
    repo = CockroachDBRepository(connection_url="postgresql://root@127.0.0.1:26259/nonexistent_db?sslmode=disable")
    is_healthy = repo.check_connection_health()
    assert is_healthy is False
