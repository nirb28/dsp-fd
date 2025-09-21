"""
API endpoints for the DSP Front Door system.
"""

import structlog
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models import (
    InferenceRequest, 
    InferenceResponse, 
    HealthResponse, 
    ErrorResponse,
    ProjectManifest
)
from app.services.inference_service import inference_service
from app.clients.control_tower_client import control_tower_client
from app.config import config
from app.utils import format_error_response


logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.post(
    "/inference",
    response_model=InferenceResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Execute Inference",
    description="Execute inference for a project using dynamically loaded modules based on manifest configuration"
)
async def execute_inference(request: InferenceRequest) -> InferenceResponse:
    """
    Execute inference for a project.
    
    This endpoint:
    1. Fetches the project manifest from the Control Tower
    2. Dynamically loads the appropriate inference module
    3. Executes inference with the provided messages
    4. Returns the generated response
    
    Args:
        request: InferenceRequest with project_id, messages, and optional parameters
    
    Returns:
        InferenceResponse with generated content and metadata
    
    Raises:
        HTTPException: Various HTTP errors based on the failure type
    """
    try:
        logger.info("Inference request received", 
                   project_id=request.project_id,
                   messages_count=len(request.messages))
        
        # Validate request
        if not request.project_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_id cannot be empty"
            )
        
        if not request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="messages cannot be empty"
            )
        
        # Execute inference
        response = await inference_service.infer(request)
        
        logger.info("Inference completed successfully", 
                   project_id=request.project_id,
                   model=response.model_used,
                   processing_time_ms=response.processing_time_ms)
        
        return response
        
    except ValueError as e:
        logger.error("Validation error during inference", 
                    project_id=request.project_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FileNotFoundError:
        logger.error("Project not found", project_id=request.project_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{request.project_id}' not found"
        )
    except RuntimeError as e:
        logger.error("Runtime error during inference", 
                    project_id=request.project_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failed: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected error during inference", 
                    project_id=request.project_id,
                    error=str(e),
                    error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )


@router.get(
    "/projects/{project_id}/manifest",
    response_model=ProjectManifest,
    responses={
        404: {"model": ErrorResponse, "description": "Project Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Get Project Manifest",
    description="Retrieve the manifest configuration for a specific project"
)
async def get_project_manifest(project_id: str) -> ProjectManifest:
    """
    Get project manifest by ID.
    
    Args:
        project_id: Project identifier
    
    Returns:
        ProjectManifest with complete configuration
    
    Raises:
        HTTPException: If project not found or other errors
    """
    try:
        logger.info("Manifest request received", project_id=project_id)
        
        if not project_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_id cannot be empty"
            )
        
        manifest = await control_tower_client.get_manifest(project_id)
        
        logger.info("Manifest retrieved successfully", 
                   project_id=project_id,
                   version=manifest.version)
        
        return manifest
        
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error("Error retrieving manifest", 
                    project_id=project_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project manifest"
        )


@router.get(
    "/projects",
    response_model=Dict[str, Any],
    summary="List Projects",
    description="List all available projects from the Control Tower"
)
async def list_projects() -> Dict[str, Any]:
    """
    List all available projects.
    
    Returns:
        Dictionary with project list and metadata
    """
    try:
        logger.info("Project list request received")
        
        manifests_data = await control_tower_client.list_manifests()
        
        logger.info("Project list retrieved successfully", 
                   count=len(manifests_data.get("manifests", [])))
        
        return manifests_data
        
    except Exception as e:
        logger.error("Error listing projects", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project list"
        )


@router.post(
    "/projects/{project_id}/health",
    response_model=Dict[str, Any],
    summary="Check Project Health",
    description="Check the health of a specific project's inference module"
)
async def check_project_health(project_id: str) -> Dict[str, Any]:
    """
    Check health of a project's inference module.
    
    Args:
        project_id: Project identifier
    
    Returns:
        Health status information
    """
    try:
        logger.info("Health check request received", project_id=project_id)
        
        if not project_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_id cannot be empty"
            )
        
        is_healthy = await inference_service.health_check(project_id)
        
        logger.info("Health check completed", 
                   project_id=project_id,
                   healthy=is_healthy)
        
        return {
            "project_id": project_id,
            "healthy": is_healthy,
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": "2025-09-20T11:13:11-04:00"
        }
        
    except Exception as e:
        logger.error("Error during health check", 
                    project_id=project_id,
                    error=str(e))
        return {
            "project_id": project_id,
            "healthy": False,
            "status": "error",
            "error": str(e),
            "timestamp": "2025-09-20T11:13:11-04:00"
        }


@router.delete(
    "/cache",
    response_model=Dict[str, str],
    summary="Clear Cache",
    description="Clear cached modules and manifests"
)
async def clear_cache(project_id: str = None) -> Dict[str, str]:
    """
    Clear cached data.
    
    Args:
        project_id: Optional specific project to clear, or None for all
    
    Returns:
        Confirmation message
    """
    try:
        logger.info("Cache clear request received", project_id=project_id)
        
        # Clear inference service cache
        inference_service.clear_cache(project_id)
        
        # Clear manifest cache if clearing all
        if not project_id:
            control_tower_client.clear_cache()
        
        message = f"Cache cleared for project '{project_id}'" if project_id else "All caches cleared"
        logger.info("Cache cleared successfully", project_id=project_id)
        
        return {"message": message}
        
    except Exception as e:
        logger.error("Error clearing cache", 
                    project_id=project_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="Get System Status",
    description="Get detailed system status including loaded modules and dependencies"
)
async def get_system_status() -> Dict[str, Any]:
    """
    Get detailed system status.
    
    Returns:
        System status information
    """
    try:
        logger.info("System status request received")
        
        # Check Control Tower connectivity
        control_tower_healthy = await control_tower_client.health_check()
        
        # Get loaded projects
        loaded_projects = inference_service.get_loaded_projects()
        
        status_data = {
            "status": "healthy" if control_tower_healthy else "degraded",
            "timestamp": "2025-09-20T11:13:11-04:00",
            "version": "1.0.0",
            "dependencies": {
                "control_tower": "healthy" if control_tower_healthy else "unhealthy",
                "inference_service": "healthy"
            },
            "loaded_projects": loaded_projects,
            "loaded_projects_count": len(loaded_projects),
            "configuration": {
                "control_tower_url": config.control_tower.base_url,
                "cache_ttl": config.front_door.cache_ttl,
                "authentication_enabled": bool(config.front_door.api_key)
            }
        }
        
        logger.info("System status retrieved successfully", 
                   control_tower_healthy=control_tower_healthy,
                   loaded_projects_count=len(loaded_projects))
        
        return status_data
        
    except Exception as e:
        logger.error("Error retrieving system status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system status"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Basic health check endpoint"
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.
    
    Returns:
        HealthResponse with service status
    """
    try:
        # Check Control Tower connectivity
        control_tower_healthy = await control_tower_client.health_check()
        
        status_value = "healthy" if control_tower_healthy else "degraded"
        
        return HealthResponse(
            status=status_value,
            version="1.0.0",
            dependencies={
                "control_tower": "healthy" if control_tower_healthy else "unhealthy"
            }
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            dependencies={
                "control_tower": "error"
            }
        )
