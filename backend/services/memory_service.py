"""
Service layer for AI memory search operations.

ARCHITECTURE PATTERN:
API Route (api/v1/memory.py) -> MemoryService (services/memory_service.py) -> IAIServiceInterface (interfaces/ai_interface.py)
The API route never calls the interface directly.

OWNERSHIP RECORD:
AI Agent layer owns semantic memory retrieval, vector ranking, and similarity evaluation.
Database layer owns underlying CockroachDB vector storage infrastructure.
Backend acts strictly as a secure request/response proxy.
"""

from backend.interfaces.ai_interface import IAIServiceInterface
from backend.schemas.memory import MemorySearchQuery, MemorySearchResponse


class MemoryService:
    def __init__(self, ai_interface: IAIServiceInterface):
        self.ai_interface = ai_interface

    def search_memory(self, query: MemorySearchQuery) -> MemorySearchResponse:
        """
        Proxy authenticated memory search request to AI interface.
        
        Backend role: Validate request/response schemas and proxy call.
        AI role: Perform semantic vector search across CockroachDB incident memory.
        """
        return self.ai_interface.search_memory(query)
