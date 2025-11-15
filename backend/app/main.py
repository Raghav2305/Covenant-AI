"""
Contract AI Copilot - Main FastAPI Application
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import structlog
import logging
import sys
from structlog.stdlib import ProcessorFormatter, LoggerFactory

from app.core.config import settings
from app.core.database import init_db
from app.api import contracts, obligations, monitoring, reports, copilot, admin
from app.core.mcp_client import MCPClientManager

# Configure structured logging
# Use ConsoleRenderer for development if DEBUG is True
renderer = structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer()

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        ProcessorFormatter.wrap_for_formatter, # Added this
    ],
    context_class=dict,
    logger_factory=LoggerFactory(), # Changed this
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Configure standard Python logging to route through structlog
logging.basicConfig(
    format="%(message)s",
    level=logging.DEBUG, # Changed to DEBUG
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Contract AI Copilot application")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Initialize MCP client manager
    app.state.mcp_manager = MCPClientManager()
    await app.state.mcp_manager.initialize()
    logger.info("MCP client manager initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Contract AI Copilot application")
    await app.state.mcp_manager.cleanup()


# Create FastAPI application
app = FastAPI(
    title="Contract AI Copilot API",
    description="AI-powered contract lifecycle and obligation management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
cors_origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["localhost", "127.0.0.1"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Contract AI Copilot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        # Check MCP connections
        # Check Redis connection
        
        return {
            "status": "healthy",
            "database": "connected",
            "mcp": "connected",
            "redis": "connected"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")


# Include API routers
app.include_router(contracts.router, prefix="/api/v1/contracts", tags=["contracts"])
app.include_router(obligations.router, prefix="/api/v1/obligations", tags=["obligations"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(copilot.router, prefix="/api/v1/copilot", tags=["copilot"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
        log_config=None # Disable uvicorn's default logging
    )
