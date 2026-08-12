"""Unit tests for contract interface conformance, production repository gating, and startup security validation."""

import pytest
from backend.core.config import settings
from backend.core.dependencies import get_db_repository, get_ai_interface
from backend.core.exceptions import ConfigurationError
from backend.interfaces.db_interface import IDatabaseRepository
from backend.interfaces.ai_interface import IAIServiceInterface
from backend.tests.mocks.mock_db_repository import MockDatabaseRepository
from backend.tests.mocks.mock_ai_interface import MockAIInterface


def test_db_repository_interface_conformance():
    """Verify MockDatabaseRepository inherits and implements IDatabaseRepository."""
    mock_db = MockDatabaseRepository()
    assert isinstance(mock_db, IDatabaseRepository)


def test_ai_interface_conformance():
    """Verify MockAIInterface inherits and implements IAIServiceInterface."""
    mock_ai = MockAIInterface()
    assert isinstance(mock_ai, IAIServiceInterface)


def test_mock_gating_when_testing_false():
    """Verify that dependencies.py returns CockroachDBRepository for DB and raises ConfigurationError for unconfigured AI when TESTING is False."""
    settings.TESTING = False
    try:
        db_repo = get_db_repository()
        assert isinstance(db_repo, IDatabaseRepository)

        with pytest.raises(ConfigurationError) as exc_info_ai:
            get_ai_interface()
        assert "Production IAIServiceInterface not configured" in str(exc_info_ai.value)
    finally:
        settings.TESTING = True


def test_jwt_secret_validation_in_non_testing():
    """Verify validate_security raises ConfigurationError when JWT_SECRET_KEY is missing/empty in non-testing mode."""
    original_testing = settings.TESTING
    original_key = settings.JWT_SECRET_KEY
    try:
        settings.TESTING = False
        settings.JWT_SECRET_KEY = ""
        with pytest.raises(ConfigurationError) as exc_info:
            settings.validate_security()
        assert "JWT_SECRET_KEY must be configured" in str(exc_info.value)
    finally:
        settings.TESTING = original_testing
        settings.JWT_SECRET_KEY = original_key
