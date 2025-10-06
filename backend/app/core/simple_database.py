"""
Simple Database configuration using SQLite for testing
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import structlog
from app.core.config import settings

logger = structlog.get_logger()

# Use SQLite for testing
SQLITE_URL = "sqlite:///./contract_ai.db"

# Create database engine
engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


def init_db():
    """Initialize database tables"""
    try:
        # Import all models to ensure they are registered
        from app.models import contract, obligation, alert  # noqa
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("SQLite database tables created successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
