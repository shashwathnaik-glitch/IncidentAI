"""
Admin REST API Router (/api/v1/admin)
"""

from fastapi import APIRouter
from typing import List, Dict

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

@router.get("/dashboard")
def get_admin_dashboard_metrics():
    """Returns platform metrics, MTTR reduction %, and solution effectiveness breakdown."""
    return {
        "activeIncidents": 3,
        "resolvedIncidents": 142,
        "totalUsers": 48,
        "mttrReductionPercent": 68.4,
        "aiRecommendationAccuracy": 96.4,
        "vectorMemoriesCount": 1284,
        "nodeClusterHealth": "HEALTHY",
        "solutionEffectiveness": {
            "success": 184,
            "failure": 24,
            "partial": 12,
            "rejected": 8,
            "unknown": 4,
            "totalAttempts": 232,
            "successRate": 79.3
        },
        "categoryDistribution": [
            {"category": "Database (CockroachDB)", "count": 54, "percent": 38},
            {"category": "Backend API (FastAPI)", "count": 42, "percent": 30},
            {"category": "AI Service (Bedrock)", "count": 28, "percent": 20},
            {"category": "Infrastructure / Cloud", "count": 18, "percent": 12}
        ],
        "solutionLeaderboard": [
            {"rank": 1, "fixTitle": "Scale CockroachDB max_connections & flush idle cursors", "category": "Database", "successCount": 42, "rewardPoints": 850, "author": "Alex Rivera"},
            {"rank": 2, "fixTitle": "Lower bcrypt work factor to 10 with Redis token caching", "category": "Backend API", "successCount": 38, "rewardPoints": 760, "author": "Jordan Lee"},
            {"rank": 3, "fixTitle": "Wrap boto3 Bedrock call with exponential backoff jitter", "category": "AI Service", "successCount": 29, "rewardPoints": 580, "author": "Sarah Chen"},
            {"rank": 4, "fixTitle": "Flush ingress DNS routing table and restart pod", "category": "Infrastructure", "successCount": 21, "rewardPoints": 420, "author": "Taylor Vance"}
        ],
        "employeeUsage": [
            {"name": "Alex Rivera", "email": "employee@company.com", "title": "L2 Support Engineer", "resolvedCount": 34, "rewardPoints": 850, "lastActive": "5m ago"},
            {"name": "Jordan Lee", "email": "user@company.com", "title": "DevOps Specialist", "resolvedCount": 28, "rewardPoints": 760, "lastActive": "18m ago"},
            {"name": "Sarah Chen", "email": "admin@company.com", "title": "Lead SRE & Admin", "resolvedCount": 45, "rewardPoints": 980, "lastActive": "Now"},
            {"name": "Taylor Vance", "email": "taylor@company.com", "title": "Infrastructure Engineer", "resolvedCount": 19, "rewardPoints": 420, "lastActive": "2h ago"}
        ]
    }

@router.get("/users")
def get_admin_users_list():
    """Returns platform users for RBAC management."""
    return [
        {"id": "usr_adm_001", "name": "Sarah Chen", "email": "admin@company.com", "role": "admin", "title": "Lead SRE & Admin", "status": "Active"},
        {"id": "usr_emp_001", "name": "Alex Rivera", "email": "employee@company.com", "role": "employee", "title": "L2 Support Engineer", "status": "Active"},
        {"id": "usr_emp_002", "name": "Jordan Lee", "email": "user@company.com", "role": "employee", "title": "DevOps Specialist", "status": "Active"}
    ]
