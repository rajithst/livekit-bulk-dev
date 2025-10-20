"""
FastAPI backend application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .core.config import settings
from .core.logging import setup_logging
from .api.v1.router import api_router
from .middleware.auth import AuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.error_handler import error_handler_middleware


# Setup logging
setup_logging(settings.log_level)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Voice Assistant Backend API",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)
app.middleware("http")(error_handler_middleware)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    # Initialize database connection pool
    from .db.session import init_db
    await init_db()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    from .db.session import close_db
    await close_db()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Voice Assistant API",
        "docs": "/api/docs" if settings.debug else None
    }
