"""
Middleware for the DSP Front Door API.
"""

import time
import structlog
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param

from app.config import config


logger = structlog.get_logger(__name__)
security = HTTPBearer(auto_error=False)


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware for request/response logging.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint function
    
    Returns:
        Response object
    """
    start_time = time.time()
    request_id = id(request)
    
    # Log request
    logger.info("Request started",
               request_id=request_id,
               method=request.method,
               url=str(request.url),
               client_ip=request.client.host if request.client else None,
               user_agent=request.headers.get("user-agent"))
    
    try:
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Log response
        logger.info("Request completed",
                   request_id=request_id,
                   status_code=response.status_code,
                   processing_time_ms=round(processing_time_ms, 2))
        
        # Add processing time header
        response.headers["X-Processing-Time-Ms"] = str(round(processing_time_ms, 2))
        
        return response
        
    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.error("Request failed",
                    request_id=request_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    processing_time_ms=round(processing_time_ms, 2))
        
        raise


async def authentication_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware for API key authentication.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint function
    
    Returns:
        Response object
    
    Raises:
        HTTPException: If authentication fails
    """
    # Skip authentication for health endpoint
    if request.url.path == "/health":
        return await call_next(request)
    
    # Skip authentication if no API key is configured
    if not config.front_door.api_key:
        logger.debug("API key authentication disabled")
        return await call_next(request)
    
    # Get API key from headers
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        # Try Authorization header as fallback
        authorization = request.headers.get("Authorization")
        if authorization:
            scheme, credentials = get_authorization_scheme_param(authorization)
            if scheme.lower() == "bearer":
                api_key = credentials
    
    if not api_key:
        logger.warning("Authentication failed: No API key provided",
                      client_ip=request.client.host if request.client else None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide via X-API-Key header or Authorization: Bearer token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if api_key != config.front_door.api_key:
        logger.warning("Authentication failed: Invalid API key",
                      client_ip=request.client.host if request.client else None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    logger.debug("Authentication successful")
    return await call_next(request)


async def cors_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware for CORS handling.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint function
    
    Returns:
        Response object with CORS headers
    """
    # Handle preflight requests
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response
    
    # Process request
    response = await call_next(request)
    
    # Add CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
    
    return response
