"""Pytest fixtures for IncidentMind Stage 1 & 2 testing."""

import pytest
from fastapi.testclient import TestClient
from backend.core.config import settings
from backend.core.dependencies import reset_mock_repositories
from backend.main import app


@pytest.fixture(autouse=True)
def enable_testing_mode():
    """Ensure settings.TESTING is True and reset mock repositories before each test."""
    original_testing = settings.TESTING
    settings.TESTING = True
    reset_mock_repositories()
    yield
    settings.TESTING = original_testing
    reset_mock_repositories()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client
