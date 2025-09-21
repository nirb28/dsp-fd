"""
Data models for the DSP Front Door system.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ChatMessage(BaseModel):
    """Chat message for inference requests."""
    role: Literal["system", "user", "assistant"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class InferenceRequest(BaseModel):
    """Request model for inference operations."""
    project_id: str = Field(..., description="Project ID from manifest system")
    messages: List[ChatMessage] = Field(..., description="Chat messages for inference")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Optional inference parameters")
    context: Optional[str] = Field(default=None, description="Additional context for the inference")


class InferenceResponse(BaseModel):
    """Response model for inference operations."""
    project_id: str = Field(..., description="Project ID")
    response: str = Field(..., description="Generated response")
    model_used: str = Field(..., description="Model used for inference")
    tokens_used: Optional[int] = Field(default=None, description="Total tokens used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ManifestModule(BaseModel):
    """Represents a module in the project manifest."""
    module_type: str = Field(..., description="Type of the module")
    name: str = Field(..., description="Module name")
    version: str = Field(..., description="Module version")
    status: str = Field(..., description="Module status")
    description: str = Field(..., description="Module description")
    dependencies: List[str] = Field(default_factory=list, description="Module dependencies")
    config: Dict[str, Any] = Field(..., description="Module configuration")


class ProjectManifest(BaseModel):
    """Represents a complete project manifest."""
    project_id: str = Field(..., description="Unique project identifier")
    project_name: str = Field(..., description="Human-readable project name")
    version: str = Field(..., description="Project version")
    description: str = Field(..., description="Project description")
    owner: str = Field(..., description="Project owner")
    team: List[str] = Field(default_factory=list, description="Team members")
    tags: List[str] = Field(default_factory=list, description="Project tags")
    environment: str = Field(..., description="Deployment environment")
    modules: List[ManifestModule] = Field(..., description="Project modules")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    dependencies: Dict[str, str] = Field(..., description="Dependency status")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
