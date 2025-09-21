"""
Inference service that dynamically loads and manages inference modules.
"""

import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.models import ProjectManifest, InferenceRequest, InferenceResponse, ManifestModule
from app.clients.control_tower_client import control_tower_client
from app.modules import BaseInferenceModule
from app.modules.openai_module import OpenAIInferenceModule


logger = structlog.get_logger(__name__)


class ModuleRegistry:
    """Registry for inference module types."""
    
    _modules = {
        "openai": OpenAIInferenceModule,
        "gpt": OpenAIInferenceModule,  # Alias for OpenAI
    }
    
    @classmethod
    def register(cls, name: str, module_class: type):
        """Register a new inference module type."""
        cls._modules[name] = module_class
    
    @classmethod
    def get(cls, name: str) -> Optional[type]:
        """Get inference module class by name."""
        return cls._modules.get(name.lower())
    
    @classmethod
    def list_available(cls) -> List[str]:
        """List all available module types."""
        return list(cls._modules.keys())


class InferenceService:
    """Service for managing inference operations with dynamic module loading."""
    
    def __init__(self):
        self.loaded_modules: Dict[str, BaseInferenceModule] = {}
        self.module_cache_ttl = 300  # 5 minutes
        self.last_health_check: Dict[str, datetime] = {}
    
    def _detect_provider_from_config(self, config: Dict[str, Any]) -> str:
        """
        Detect inference provider from module configuration.
        
        Args:
            config: Module configuration
        
        Returns:
            Provider name (e.g., 'openai', 'anthropic')
        """
        # Check endpoint URL for provider hints
        endpoint_url = config.get("endpoint_url", "").lower()
        if "openai" in endpoint_url or "api.openai.com" in endpoint_url:
            return "openai"
        
        # Check model name for provider hints
        model_name = config.get("model_name", "").lower()
        if model_name.startswith(("gpt-", "text-", "davinci", "curie", "babbage", "ada")):
            return "openai"
        
        # Default fallback
        logger.warning("Could not detect provider, defaulting to OpenAI", config=config)
        return "openai"
    
    def _get_inference_module(self, manifest: ProjectManifest) -> ManifestModule:
        """
        Find inference endpoint module in the manifest.
        
        Args:
            manifest: Project manifest
        
        Returns:
            ManifestModule for inference endpoint
        
        Raises:
            ValueError: If no inference module found or module is disabled
        """
        inference_modules = [
            module for module in manifest.modules 
            if module.module_type == "inference_endpoint"
        ]
        
        if not inference_modules:
            raise ValueError(f"No inference_endpoint module found in manifest for project '{manifest.project_id}'")
        
        if len(inference_modules) > 1:
            logger.warning("Multiple inference modules found, using first one", 
                          project_id=manifest.project_id,
                          count=len(inference_modules))
        
        inference_module = inference_modules[0]
        
        if inference_module.status.lower() != "enabled":
            raise ValueError(f"Inference module '{inference_module.name}' is not enabled (status: {inference_module.status})")
        
        return inference_module
    
    async def _load_module(self, project_id: str, module_config: ManifestModule) -> BaseInferenceModule:
        """
        Load inference module for the given configuration.
        
        Args:
            project_id: Project identifier
            module_config: Module configuration from manifest
        
        Returns:
            Loaded inference module instance
        
        Raises:
            ValueError: If module type is not supported
            RuntimeError: If module loading fails
        """
        try:
            # Detect provider from config
            provider = self._detect_provider_from_config(module_config.config)
            
            # Get module class from registry
            module_class = ModuleRegistry.get(provider)
            if not module_class:
                available = ModuleRegistry.list_available()
                raise ValueError(f"Unsupported inference provider '{provider}'. Available: {available}")
            
            logger.info("Loading inference module", 
                       project_id=project_id,
                       provider=provider,
                       module_name=module_config.name,
                       module_class=module_class.__name__)
            
            # Create module instance
            module = module_class(module_config.config)
            
            # Perform health check
            is_healthy = await module.health_check()
            if not is_healthy:
                raise RuntimeError(f"Module health check failed for provider '{provider}'")
            
            logger.info("Successfully loaded inference module", 
                       project_id=project_id,
                       provider=provider,
                       model=module.get_model_name())
            
            return module
            
        except Exception as e:
            logger.error("Failed to load inference module", 
                        project_id=project_id,
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    async def get_or_load_module(self, project_id: str) -> BaseInferenceModule:
        """
        Get cached inference module or load it from manifest.
        
        Args:
            project_id: Project identifier
        
        Returns:
            Inference module instance
        
        Raises:
            ValueError: If project not found or configuration invalid
            RuntimeError: If module loading fails
        """
        # Check if module is already loaded
        if project_id in self.loaded_modules:
            logger.debug("Using cached inference module", project_id=project_id)
            return self.loaded_modules[project_id]
        
        try:
            # Fetch manifest from Control Tower
            manifest = await control_tower_client.get_manifest(project_id)
            
            # Find inference module in manifest
            inference_module_config = self._get_inference_module(manifest)
            
            # Load the module
            module = await self._load_module(project_id, inference_module_config)
            
            # Cache the loaded module
            self.loaded_modules[project_id] = module
            
            return module
            
        except Exception as e:
            logger.error("Failed to get or load module", 
                        project_id=project_id,
                        error=str(e))
            raise
    
    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        """
        Perform inference for the given request.
        
        Args:
            request: InferenceRequest with project_id and messages
        
        Returns:
            InferenceResponse with generated content
        
        Raises:
            ValueError: If project not found or configuration invalid
            RuntimeError: If inference fails
        """
        try:
            logger.info("Starting inference", 
                       project_id=request.project_id,
                       messages_count=len(request.messages))
            
            # Get or load inference module
            module = await self.get_or_load_module(request.project_id)
            
            # Perform inference
            response = await module.infer(
                messages=request.messages,
                parameters=request.parameters,
                context=request.context
            )
            
            # Set project_id in response
            response.project_id = request.project_id
            
            logger.info("Inference completed successfully", 
                       project_id=request.project_id,
                       model=response.model_used,
                       processing_time_ms=response.processing_time_ms)
            
            return response
            
        except Exception as e:
            logger.error("Inference failed", 
                        project_id=request.project_id,
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    async def health_check(self, project_id: str) -> bool:
        """
        Check health of inference module for a project.
        
        Args:
            project_id: Project identifier
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            module = await self.get_or_load_module(project_id)
            is_healthy = await module.health_check()
            
            self.last_health_check[project_id] = datetime.utcnow()
            
            logger.debug("Module health check completed", 
                        project_id=project_id,
                        healthy=is_healthy)
            
            return is_healthy
            
        except Exception as e:
            logger.error("Module health check failed", 
                        project_id=project_id,
                        error=str(e))
            return False
    
    def clear_cache(self, project_id: Optional[str] = None) -> None:
        """
        Clear cached modules.
        
        Args:
            project_id: Specific project to clear, or None to clear all
        """
        if project_id:
            if project_id in self.loaded_modules:
                del self.loaded_modules[project_id]
                logger.info("Cleared module cache for project", project_id=project_id)
        else:
            self.loaded_modules.clear()
            self.last_health_check.clear()
            logger.info("Cleared all module cache")
    
    def get_loaded_projects(self) -> List[str]:
        """Get list of projects with loaded modules."""
        return list(self.loaded_modules.keys())


# Global inference service instance
inference_service = InferenceService()
