"""AI Analysis and Action Approval REST endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, status
from backend.core.dependencies import get_ai_service
from backend.core.security import TokenData, get_current_user_token
from backend.schemas.ai import (
    AIAnalyzeRequest,
    AIAnalyzeResponse,
    AIApproveRequest,
    AIApproveResponse,
)
from backend.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["AI Agent"])


@router.post("/analyze", response_model=AIAnalyzeResponse, status_code=status.HTTP_200_OK)
def analyze_incident(
    request: AIAnalyzeRequest,
    current_token: TokenData = Depends(get_current_user_token),
    ai_service: AIService = Depends(get_ai_service)
) -> AIAnalyzeResponse:
    """
    Submit incident payload for Bedrock reasoning analysis, confidence scoring, and fix recommendation.
    
    AUTHENTICATION: Required (valid Bearer JWT).
    """
    return ai_service.analyze_incident(request)


@router.post("/approve", response_model=AIApproveResponse, status_code=status.HTTP_200_OK)
def approve_action(
    request: AIApproveRequest,
    current_token: TokenData = Depends(get_current_user_token),
    ai_service: AIService = Depends(get_ai_service)
) -> AIApproveResponse:
    """
    Approve an AI-recommended fix action for execution.
    
    AUTHENTICATION: Required (valid Bearer JWT).
    """
    approved_by = UUID(current_token.user_id)
    return ai_service.approve_action(request, approved_by=approved_by)
