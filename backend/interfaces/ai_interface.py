"""
Abstract AI Agent Interface.

OWNERSHIP BOUNDARY:
Backend / Application Services owns API routes, request validation, Pydantic schemas, and proxying calls.
AI Teammate owns Amazon Bedrock prompts, embeddings generation, vector search logic, recommendation reasoning,
confidence scoring, and model behavior.

AI TEAMMATE REQUIREMENT:
The AI Teammate must implement `IAIServiceInterface` in production by connecting to Amazon Bedrock and
CockroachDB vector storage, providing:
1. `search_memory(query)`: Perform semantic vector search over historical incident embeddings.
2. `analyze_incident(incident_payload)`: Execute LLM reasoning over incident title, description, logs, and
   past solution attempt history. Return a dictionary adhering to:
   - `recommended_solution` (str): Proposed fix recommendation.
   - `explanation` (str): Reasoning behind recommendation.
   - `confidence_score` (float 0.0 - 1.0): Model confidence.
   - `similar_incidents_found` (int): Number of historical vector matches.
   - `historical_evidence` (dict): `{"successful_solutions": [...], "failed_solutions": [...]}`.
   - `risks` (list[str]): Potential risks or side effects.
   - `requires_approval` (bool): Whether human engineer approval is required before execution.
   - `action_id` (str): Unique action identifier if action requires approval.
3. `approve_action(action_id, approved_by)`: Execute approved remediation action and return status.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from backend.schemas.memory import MemorySearchQuery, MemorySearchResponse


class IAIServiceInterface(ABC):
    """
    Interface contract for AI memory search and incident reasoning.

    AI teammate provides the Amazon Bedrock and memory retrieval implementation.
    """

    @abstractmethod
    def search_memory(self, query: MemorySearchQuery) -> MemorySearchResponse:
        """
        Execute semantic search across historical incident memory.
        Delegated to AI agent vector search engine.
        """
        pass

    @abstractmethod
    def analyze_incident(self, incident_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze an incident and return resolution recommendations with confidence scores.

        Input payload dictionary contains:
        - incident_id (str)
        - title (str, optional)
        - description (str, optional)
        - category (str, optional)
        - severity (str, optional)
        - error_logs (str, optional)
        - environment (str, optional)
        - historical_attempts (list[dict], optional)
        """
        pass

    @abstractmethod
    def approve_action(self, action_id: str, approved_by: str) -> Dict[str, Any]:
        """Approve an AI-recommended action for execution."""
        pass
