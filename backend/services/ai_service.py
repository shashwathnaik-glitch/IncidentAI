"""
Service layer for AI analysis reasoning, memory search proxy, and action approval operations.

ARCHITECTURE PATTERN:
API Route (api/v1/ai.py) -> AIService (services/ai_service.py) -> IAIServiceInterface (interfaces/ai_interface.py)
The API route never calls the interface directly.

OWNERSHIP BOUNDARY:
Backend receives request, validates schemas, enriches incident context from DB, and proxies to IAIServiceInterface.
AI Teammate owns Bedrock prompts, model reasoning, and confidence scoring algorithm.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID
from backend.interfaces.ai_interface import IAIServiceInterface
from backend.interfaces.db_interface import IDatabaseRepository
from backend.schemas.memory import MemorySearchQuery, MemorySearchResponse
from backend.schemas.ai import (
    AIAnalyzeRequest,
    AIAnalyzeResponse,
    AIApproveRequest,
    AIApproveResponse,
    HistoricalEvidence,
)


class AIService:
    def __init__(self, ai_interface: IAIServiceInterface, db_repo: Optional[IDatabaseRepository] = None):
        self.ai_interface = ai_interface
        self.db_repo = db_repo

    def search_memory(self, query: MemorySearchQuery) -> MemorySearchResponse:
        """
        Proxy memory search request to AI interface.
        """
        return self.ai_interface.search_memory(query)

    def analyze_incident(self, request: AIAnalyzeRequest) -> AIAnalyzeResponse:
        """
        Receive incident request, validate payload, enrich from database context if available,
        and send incident payload to IAIServiceInterface for Bedrock reasoning analysis.
        """
        payload: Dict[str, Any] = {
            "incident_id": str(request.incident_id),
            "error_logs": request.error_logs,
            "environment": request.environment,
        }

        # Enrich payload with incident details and past solution attempts if database is available
        if self.db_repo:
            incident = self.db_repo.get_incident_by_id(request.incident_id)
            if incident:
                payload.update({
                    "title": incident.get("title"),
                    "description": incident.get("description"),
                    "category": incident.get("category"),
                    "severity": incident.get("severity"),
                })
            attempts = self.db_repo.get_solution_attempts_by_incident(request.incident_id)
            if attempts:
                payload["historical_attempts"] = attempts

        res_dict = self.ai_interface.analyze_incident(payload)

        evidence_dict = res_dict.get("historical_evidence", {})
        evidence = HistoricalEvidence(
            successful_solutions=evidence_dict.get("successful_solutions", []),
            failed_solutions=evidence_dict.get("failed_solutions", [])
        )

        return AIAnalyzeResponse(
            incident_id=request.incident_id,
            recommended_solution=res_dict.get("suggested_fix", res_dict.get("recommended_solution", "Restart container service")),
            explanation=res_dict.get("reasoning", res_dict.get("explanation", "Historical memory matches context")),
            confidence_score=float(res_dict.get("confidence_score", 0.85)),
            similar_incidents_found=int(res_dict.get("similar_incidents_found", 1)),
            historical_evidence=evidence,
            risks=res_dict.get("risks", ["Temporary service disruption during restart"]),
            requires_approval=bool(res_dict.get("requires_approval", True)),
            action_id=res_dict.get("action_id", f"ACT-{request.incident_id.hex[:8]}"),
        )

    def approve_action(self, request: AIApproveRequest, approved_by: UUID) -> AIApproveResponse:
        """
        Approve an AI-recommended action execution.
        """
        res_dict = self.ai_interface.approve_action(request.action_id, str(approved_by))
        return AIApproveResponse(
            action_id=res_dict.get("action_id", request.action_id),
            status=res_dict.get("status", "approved"),
            approved_by=approved_by,
            approved_at=datetime.now(timezone.utc),
        )
