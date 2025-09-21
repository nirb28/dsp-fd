"""
Main FastAPI application for the DSP Front Door system.
"""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import config
from app.utils import setup_logging, format_error_response
from app.api.endpoints import router
from app.api.middleware import logging_middleware, authentication_middleware, cors_middleware


# Setup logging
setup_logging(config.front_door.log_level)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting DSP Front Door", 
               host=config.front_door.host,
               port=config.front_door.port,
               log_level=config.front_door.log_level)
    
    try:
        # Validate configuration
        config.validate()
        logger.info("Configuration validation successful")
        
        # Test Control Tower connectivity
        from app.clients.control_tower_client import control_tower_client
        control_tower_healthy = await control_tower_client.health_check()
        
        if control_tower_healthy:
            logger.info("Control Tower connection established", 
                       url=config.control_tower.base_url)
        else:
            logger.warning("Control Tower connection failed", 
                          url=config.control_tower.base_url)
        
        logger.info("DSP Front Door started successfully")
        
    except Exception as e:
        logger.error("Failed to start DSP Front Door", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down DSP Front Door")
    
    # Clear caches
    from app.services.inference_service import inference_service
    inference_service.clear_cache()
    
    from app.clients.control_tower_client import control_tower_client
    control_tower_client.clear_cache()
    
    logger.info("DSP Front Door shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="DSP Front Door",
    description="Enterprise inference system front door that dynamically loads and executes inference modules based on project manifests",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Add middleware in reverse order (last added = first executed)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Trusted host middleware (security)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure as needed for production
)

# Custom middleware
@app.middleware("http")
async def custom_middleware_stack(request: Request, call_next):
    """Combined middleware stack for performance."""
    # Logging middleware
    response = await logging_middleware(request, call_next)
    return response


# Exception handlers

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning("Request validation failed", 
                  url=str(request.url),
                  errors=exc.errors())
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": exc.errors()
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    logger.warning("HTTP exception occurred", 
                  url=str(request.url),
                  status_code=exc.status_code,
                  detail=exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "message": exc.detail or "HTTP error occurred"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error("Unexpected exception occurred", 
                url=str(request.url),
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred"
        }
    )


# Include routers
app.include_router(router, prefix="", tags=["inference"])


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with basic service information."""
    return {
        "service": "DSP Front Door",
        "version": "1.0.0",
        "description": "Enterprise inference system front door",
        "docs_url": "/docs",
        "health_url": "/health",
        "status_url": "/status"
    }
