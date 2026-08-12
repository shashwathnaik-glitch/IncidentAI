"""Main API v1 router combining endpoint sub-routers."""

from fastapi import APIRouter
from backend.api.v1.auth import router as auth_router
from backend.api.v1.memory import router as memory_router
from backend.api.v1.incidents import router as incidents_router
from backend.api.v1.solution_attempts import router as solution_attempts_router
from backend.api.v1.ai import router as ai_router
from backend.api.v1.admin import router as admin_router
from backend.api.v1.notifications import router as notifications_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(memory_router)
api_v1_router.include_router(incidents_router)
api_v1_router.include_router(solution_attempts_router)
api_v1_router.include_router(ai_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(notifications_router)
