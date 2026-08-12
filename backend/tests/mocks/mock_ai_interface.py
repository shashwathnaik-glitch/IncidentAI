"""
Test-only Mock AI Interface.

LOCATION RULE:
This file lives exclusively under tests/mocks/ and is isolated for unit testing.
"""

from typing import Any, Dict
from uuid import UUID
from backend.interfaces.ai_interface import IAIServiceInterface
from backend.schemas.memory import MemoryItemResponse, MemorySearchQuery, MemorySearchResponse


class MockAIInterface(IAIServiceInterface):
    """In-memory mock AI interface for testing memory search proxying."""

    def search_memory(self, query: MemorySearchQuery) -> MemorySearchResponse:
        matches = [
            MemoryItemResponse(
                incident_id=UUID("33333333-3333-3333-3333-333333333333"),
                title=f"Mock Incident related to: {query.query}",
                similarity_score=0.92,
                historical_outcomes=["success", "failure"],
                summary=f"Resolved previous incident matching {query.query} by restarting service."
            )
        ]
        return MemorySearchResponse(
            query=query.query,
            total_results=len(matches),
            matches=matches
        )

    def analyze_incident(self, incident_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "confidence_score": 0.88,
            "suggested_fix": "Restart service container",
            "reasoning": "Previous success evidence matches 85% context."
        }

    def approve_action(self, action_id: str, approved_by: str) -> Dict[str, Any]:
        return {
            "action_id": action_id,
            "status": "approved",
            "approved_by": approved_by
        }
