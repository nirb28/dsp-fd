"""
Client for interacting with the DSP AI Control Tower to fetch project manifests.
"""

import httpx
import structlog
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import config
from app.models import ProjectManifest


logger = structlog.get_logger(__name__)


class ManifestCache:
    """Simple in-memory cache for project manifests."""
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
    
    def get(self, project_id: str) -> Optional[ProjectManifest]:
        """Get cached manifest if still valid."""
        if project_id not in self.cache:
            return None
        
        entry = self.cache[project_id]
        if datetime.utcnow() > entry["expires_at"]:
            del self.cache[project_id]
            return None
        
        logger.debug("Retrieved manifest from cache", project_id=project_id)
        return entry["manifest"]
    
    def set(self, project_id: str, manifest: ProjectManifest) -> None:
        """Cache manifest with expiration."""
        expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
        self.cache[project_id] = {
            "manifest": manifest,
            "expires_at": expires_at
        }
        logger.debug("Cached manifest", project_id=project_id, expires_at=expires_at)
    
    def clear(self) -> None:
        """Clear all cached manifests."""
        self.cache.clear()
        logger.info("Manifest cache cleared")


class ControlTowerClient:
    """Client for DSP AI Control Tower API."""
    
    def __init__(self):
        self.base_url = config.control_tower.base_url.rstrip("/")
        self.headers = {
            "X-Superuser-Key": config.control_tower.superuser_key,
            "Content-Type": "application/json"
        }
        self.timeout = config.control_tower.timeout
        self.cache = ManifestCache(ttl_seconds=config.front_door.cache_ttl)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Control Tower with retry logic."""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
    
    async def get_manifest(self, project_id: str, use_cache: bool = True) -> ProjectManifest:
        """
        Get project manifest by ID.
        
        Args:
            project_id: Project identifier
            use_cache: Whether to use cached version if available
        
        Returns:
            ProjectManifest object
        
        Raises:
            httpx.HTTPStatusError: If manifest not found or other HTTP error
            ValueError: If manifest data is invalid
        """
        # Check cache first
        if use_cache:
            cached_manifest = self.cache.get(project_id)
            if cached_manifest:
                return cached_manifest
        
        try:
            logger.info("Fetching manifest from Control Tower", project_id=project_id)
            
            # Fetch from Control Tower
            response_data = await self._make_request("GET", f"/manifests/{project_id}")
            
            # Parse and validate manifest
            manifest = ProjectManifest(**response_data)
            
            # Cache the result
            self.cache.set(project_id, manifest)
            
            logger.info("Successfully fetched manifest", 
                       project_id=project_id, 
                       version=manifest.version,
                       modules_count=len(manifest.modules))
            
            return manifest
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error("Manifest not found", project_id=project_id)
                raise ValueError(f"Project '{project_id}' not found")
            else:
                logger.error("HTTP error fetching manifest", 
                           project_id=project_id, 
                           status_code=e.response.status_code,
                           error=str(e))
                raise
        except Exception as e:
            logger.error("Unexpected error fetching manifest", 
                        project_id=project_id, 
                        error=str(e))
            raise
    
    async def list_manifests(self) -> Dict[str, Any]:
        """List all available manifests."""
        try:
            logger.info("Fetching manifest list from Control Tower")
            response_data = await self._make_request("GET", "/manifests")
            
            logger.info("Successfully fetched manifest list", 
                       count=len(response_data.get("manifests", [])))
            
            return response_data
            
        except Exception as e:
            logger.error("Error fetching manifest list", error=str(e))
            raise
    
    async def validate_manifest(self, manifest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate manifest data against Control Tower."""
        try:
            logger.info("Validating manifest with Control Tower")
            response_data = await self._make_request("POST", "/manifests/validate", json=manifest_data)
            
            logger.info("Manifest validation completed", 
                       valid=response_data.get("valid", False))
            
            return response_data
            
        except Exception as e:
            logger.error("Error validating manifest", error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """Check if Control Tower is healthy."""
        try:
            # Simple GET request to test connectivity
            await self._make_request("GET", "/manifests", params={"limit": 1})
            logger.debug("Control Tower health check passed")
            return True
            
        except Exception as e:
            logger.error("Control Tower health check failed", error=str(e))
            return False
    
    def clear_cache(self) -> None:
        """Clear the manifest cache."""
        self.cache.clear()


# Global client instance
control_tower_client = ControlTowerClient()
