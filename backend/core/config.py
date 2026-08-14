"""
Core Configuration Settings for IncidentMind Backend API
"""

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "IncidentMind Backend API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Secret Key for JWT Signature
    SECRET_KEY: str = os.getenv("JWT_SECRET", "incidentmind_super_secret_jwt_key_2026_hackathon")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours

    # CockroachDB Connection String
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://root@localhost:26257/defaultdb?sslmode=disable")

    # AWS Amazon Bedrock Settings
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    EMBEDDING_MODEL_ID: str = os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v1")
    LLM_MODEL_ID: str = os.getenv("LLM_MODEL_ID", "anthropic.claude-v2")

    class Config:
        case_sensitive = True

settings = Settings()
