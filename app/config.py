"""
Configuration management for the DSP Front Door system.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ControlTowerConfig(BaseModel):
    """Configuration for DSP AI Control Tower connection."""
    base_url: str = Field(default="http://localhost:5000", description="Control Tower base URL")
    superuser_key: str = Field(..., description="Superuser API key for Control Tower")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")


class OpenAIConfig(BaseModel):
    """Configuration for OpenAI integration."""
    api_key: str = Field(..., description="OpenAI API key")
    base_url: Optional[str] = Field(default=None, description="Custom OpenAI base URL")
    timeout: int = Field(default=60, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")


class FrontDoorConfig(BaseModel):
    """Main configuration for Front Door service."""
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    log_level: str = Field(default="INFO", description="Logging level")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    cache_ttl: int = Field(default=300, description="Manifest cache TTL in seconds")


class AppConfig:
    """Application configuration singleton."""
    
    def __init__(self):
        self.control_tower = ControlTowerConfig(
            base_url=os.getenv("CONTROL_TOWER_BASE_URL", "http://localhost:5000"),
            superuser_key=os.getenv("CONTROL_TOWER_SUPERUSER_KEY", "")
        )
        
        self.openai = OpenAIConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        
        self.front_door = FrontDoorConfig(
            host=os.getenv("FD_HOST", "0.0.0.0"),
            port=int(os.getenv("FD_PORT", "8000")),
            log_level=os.getenv("FD_LOG_LEVEL", "INFO"),
            api_key=os.getenv("FD_API_KEY")
        )
    
    def validate(self) -> bool:
        """Validate configuration."""
        errors = []
        
        if not self.control_tower.superuser_key:
            errors.append("CONTROL_TOWER_SUPERUSER_KEY is required")
        
        if not self.openai.api_key:
            errors.append("OPENAI_API_KEY is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True


# Global configuration instance
config = AppConfig()
