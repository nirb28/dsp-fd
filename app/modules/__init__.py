"""
Inference modules for the DSP Front Door system.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import ChatMessage, InferenceResponse


class BaseInferenceModule(ABC):
    """Base class for all inference modules."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the inference module with configuration.
        
        Args:
            config: Module configuration from manifest
        """
        self.config = config
        self.model_name = config.get("model_name", "unknown")
    
    @abstractmethod
    async def infer(
        self, 
        messages: List["ChatMessage"], 
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None
    ) -> "InferenceResponse":
        """
        Perform inference with the given messages.
        
        Args:
            messages: List of chat messages
            parameters: Optional inference parameters
            context: Optional additional context
        
        Returns:
            InferenceResponse with the generated response
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the inference module is healthy and ready.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model_name
