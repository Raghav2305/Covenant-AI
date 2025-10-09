"""
Application configuration using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Contract AI Copilot"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/contract_ai"
    REDIS_URL: str = "redis://localhost:6379"
    
    # AI Services
    OPENAI_API_KEY: str = "sk-test-key"  # Set your actual key in .env
    OPENAI_MODEL: str = "gpt-3.5-turbo"  # Using 3.5 for compatibility
    VECTOR_DB_URL: str = "http://localhost:8080"
    VECTOR_DB_API_KEY: str = ""
    
    # MCP Configuration (Model Context Protocol)
    MCP_SERVER_URL: str = "http://localhost:3001"
    MCP_SERVER_PORT: int = 3001
    MCP_CLIENT_ID: str = "contract_ai_copilot"
    MCP_DATABASE_CONNECTOR_URL: str = "http://localhost:3001"
    MCP_CRM_CONNECTOR_URL: str = "http://localhost:3003"
    MCP_FINANCE_CONNECTOR_URL: str = "http://localhost:3004"
    
    # External System Connections (via MCP)
    TRANSACTION_DB_URL: str = "postgresql://user:pass@transaction-db:5432/transactions"
    CRM_API_URL: str = "https://api.crm-system.com/v1"
    FINANCE_API_URL: str = "https://api.finance-system.com/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_SECRET: str = "your-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    # File Upload
    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: str = "pdf,docx,txt"
    
    # Monitoring & Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    SENTRY_DSN: Optional[str] = None
    
    # Background Tasks
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    MAX_WORKERS: int = 4
    
    # Notification Services
    SLACK_WEBHOOK_URL: Optional[str] = None
    EMAIL_SERVICE_API_KEY: Optional[str] = None
    TEAMS_WEBHOOK_URL: Optional[str] = None

    # Backup & Recovery
    BACKUP_SCHEDULE: Optional[str] = None
    BACKUP_RETENTION_DAYS: Optional[int] = None
    BACKUP_STORAGE_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = 'utf-8'


# Create settings instance
settings = Settings()


# Validate required settings
def validate_settings():
    """Validate critical settings"""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required")
    
    if settings.SECRET_KEY == "your-secret-key-change-in-production":
        if settings.ENVIRONMENT == "production":
            raise ValueError("SECRET_KEY must be changed in production")
    
    return True


# Validate on import
validate_settings()
