"""FastAPI dependency injection providers for services and repository interfaces."""

from typing import Optional
from fastapi import Depends
from backend.core.config import settings
from backend.core.exceptions import ConfigurationError
from backend.interfaces.db_interface import IDatabaseRepository
from backend.interfaces.ai_interface import IAIServiceInterface
from backend.interfaces.notification_interface import INotificationInterface

_mock_db_instance: Optional[IDatabaseRepository] = None
_mock_ai_instance: Optional[IAIServiceInterface] = None
_mock_notif_instance: Optional[INotificationInterface] = None


def reset_mock_repositories():
    """Reset mock repository singletons between test runs."""
    global _mock_db_instance, _mock_ai_instance, _mock_notif_instance
    _mock_db_instance = None
    _mock_ai_instance = None
    _mock_notif_instance = None


def get_db_repository() -> IDatabaseRepository:
    """
    Dependency provider for IDatabaseRepository.

    Production implementation connects to CockroachDB via CockroachDBRepository.
    In testing environment (settings.TESTING is True), mock implementation from tests/mocks/ is injected as a singleton.
    In production runtime (settings.TESTING is False), CockroachDBRepository is instantiated.
    """
    global _mock_db_instance
    from backend.core.config import USE_REAL_DB

    if settings.TESTING or not USE_REAL_DB:
        if _mock_db_instance is None:
            try:
                from backend.tests.mocks.mock_db_repository import MockDatabaseRepository
                _mock_db_instance = MockDatabaseRepository()
            except ImportError as err:
                raise ConfigurationError(f"Testing environment active but mock DB import failed: {err}")
        return _mock_db_instance

    try:
        from backend.database.cockroach_repository import CockroachDBRepository
        return CockroachDBRepository()
    except Exception as err:
        raise ConfigurationError(f"CockroachDB repository initialization failed: {err}")


def get_ai_interface() -> IAIServiceInterface:
    """
    Dependency provider for IAIServiceInterface.

    Production implementation is owned by AI teammate.
    In testing environment (settings.TESTING is True), mock implementation from tests/mocks/ is injected as a singleton.
    In non-testing runtime, attempting to call mock without production AI implementation raises ConfigurationError.
    """
    global _mock_ai_instance
    if settings.TESTING:
        if _mock_ai_instance is None:
            try:
                from backend.tests.mocks.mock_ai_interface import MockAIInterface
                _mock_ai_instance = MockAIInterface()
            except ImportError as err:
                raise ConfigurationError(f"Testing environment active but mock AI import failed: {err}")
        return _mock_ai_instance

    # In production, AI teammate connects their Amazon Bedrock / memory retrieval implementation here.
    raise ConfigurationError(
        "Production IAIServiceInterface not configured. "
        "AI Reasoning implementation must be registered by AI teammate."
    )


def get_notification_interface() -> INotificationInterface:
    """
    Dependency provider for INotificationInterface.

    In testing environment or when credentials are missing, returns ConsoleNotificationInterface.
    In production, returns SMTPAndSlackNotificationInterface.
    """
    global _mock_notif_instance
    if settings.TESTING:
        if _mock_notif_instance is None:
            from backend.notifications.transport import ConsoleNotificationInterface
            _mock_notif_instance = ConsoleNotificationInterface()
        return _mock_notif_instance

    from backend.notifications.transport import SMTPAndSlackNotificationInterface
    return SMTPAndSlackNotificationInterface()


def get_auth_service(db_repo: IDatabaseRepository = Depends(get_db_repository)):
    """Dependency provider for AuthService."""
    from backend.services.auth_service import AuthService
    return AuthService(db_repo=db_repo)


def get_ai_service(
    ai_interface: IAIServiceInterface = Depends(get_ai_interface),
    db_repo: IDatabaseRepository = Depends(get_db_repository)
):
    """Dependency provider for AIService."""
    from backend.services.ai_service import AIService
    return AIService(ai_interface=ai_interface, db_repo=db_repo)


def get_memory_service(ai_interface: IAIServiceInterface = Depends(get_ai_interface)):
    """Dependency provider for MemoryService."""
    from backend.services.memory_service import MemoryService
    return MemoryService(ai_interface=ai_interface)


def get_incident_service(db_repo: IDatabaseRepository = Depends(get_db_repository)):
    """Dependency provider for IncidentService."""
    from backend.services.incident_service import IncidentService
    return IncidentService(db_repo=db_repo)


def get_solution_service(db_repo: IDatabaseRepository = Depends(get_db_repository)):
    """Dependency provider for SolutionService."""
    from backend.services.solution_service import SolutionService
    return SolutionService(db_repo=db_repo)


def get_admin_service(db_repo: IDatabaseRepository = Depends(get_db_repository)):
    """Dependency provider for AdminService."""
    from backend.services.admin_service import AdminService
    return AdminService(db_repo=db_repo)


def get_notification_service(notification_interface: INotificationInterface = Depends(get_notification_interface)):
    """Dependency provider for NotificationService."""
    from backend.services.notification_service import NotificationService
    return NotificationService(notification_interface=notification_interface)
