from typing import Any, Dict, Optional
from uuid import UUID
from backend.interfaces.ai_interface import IAIServiceInterface
from backend.interfaces.db_interface import IDatabaseRepository
from backend.schemas.memory import MemoryItemResponse, MemorySearchQuery, MemorySearchResponse


class MockAIInterface(IAIServiceInterface):
    """In-memory mock AI interface for testing memory search proxying."""

    def __init__(self, db_repo: Optional[IDatabaseRepository] = None):
        self.db_repo = db_repo

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
        category = incident_payload.get("category", "")
        current_id = incident_payload.get("incident_id")
        
        similar_incidents_found = 0
        successful_solutions = []
        failed_solutions = []
        reasoning = "Previous success evidence matches 85% context."
        suggested_fix = "Restart service container"
        
        if self.db_repo and category:
            try:
                # Query incidents in the same category
                incidents = self.db_repo.list_incidents(category=category)
                for inc in incidents:
                    if str(inc["id"]) != str(current_id):
                        similar_incidents_found += 1
                        # Get attempts for this similar incident
                        attempts = self.db_repo.get_solution_attempts_by_incident(inc["id"])
                        for att in attempts:
                            sol_text = att.get("solution_text") or att.get("solution_action", "")
                            if att.get("outcome") == "success":
                                successful_solutions.append(sol_text)
                            else:
                                failed_solutions.append(sol_text)
                
                if similar_incidents_found > 0:
                    reasoning = f"Found {similar_incidents_found} similar historical incident(s) in category '{category}'."
                    if successful_solutions:
                        suggested_fix = successful_solutions[0]
            except Exception:
                pass

        return {
            "confidence_score": 0.88,
            "suggested_fix": suggested_fix,
            "reasoning": reasoning,
            "similar_incidents_found": similar_incidents_found,
            "historical_evidence": {
                "successful_solutions": successful_solutions,
                "failed_solutions": failed_solutions
            }
        }

    def approve_action(self, action_id: str, approved_by: str) -> Dict[str, Any]:
        return {
            "action_id": action_id,
            "status": "approved",
            "approved_by": approved_by
        }

