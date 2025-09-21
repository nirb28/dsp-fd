"""
OpenAI inference module for the DSP Front Door system.
"""

import time
import structlog
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from app.config import config

if TYPE_CHECKING:
    from app.models import ChatMessage, InferenceResponse

from app.modules import BaseInferenceModule


logger = structlog.get_logger(__name__)


class OpenAIInferenceModule(BaseInferenceModule):
    """OpenAI inference module for GPT models."""
    
    def __init__(self, config_data: Dict[str, Any]):
        """
        Initialize OpenAI inference module.
        
        Args:
            config_data: Module configuration from manifest
        """
        super().__init__(config_data)
        
        # Extract OpenAI-specific configuration
        self.model_name = config_data.get("model_name", "gpt-3.5-turbo")
        self.endpoint_url = config_data.get("endpoint_url", "https://api.openai.com/v1/chat/completions")
        self.system_prompt = config_data.get("system_prompt", "You are a helpful assistant.")
        self.max_tokens = config_data.get("max_tokens", 500)
        self.temperature = config_data.get("temperature", 0.7)
        self.top_p = config_data.get("top_p", 0.9)
        self.batch_size = config_data.get("batch_size", 1)
        
        # Initialize OpenAI client
        client_config = {
            "api_key": config.openai.api_key,
            "timeout": config.openai.timeout,
            "max_retries": config.openai.max_retries
        }
        
        # Use custom base URL if provided in config
        if config.openai.base_url:
            client_config["base_url"] = config.openai.base_url
        
        self.client = AsyncOpenAI(**client_config)
        
        logger.info("Initialized OpenAI module", 
                   model=self.model_name,
                   max_tokens=self.max_tokens,
                   temperature=self.temperature)
    
    def _prepare_messages(self, messages: List["ChatMessage"], context: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Prepare messages for OpenAI API format.
        
        Args:
            messages: List of ChatMessage objects
            context: Optional additional context
        
        Returns:
            List of message dictionaries for OpenAI API
        """
        openai_messages = []
        
        # Add system prompt first
        system_content = self.system_prompt
        if context:
            system_content += f"\n\nAdditional Context:\n{context}"
        
        openai_messages.append({
            "role": "system",
            "content": system_content
        })
        
        # Convert ChatMessage objects to OpenAI format
        for msg in messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return openai_messages
    
    def _extract_parameters(self, parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract and validate OpenAI parameters.
        
        Args:
            parameters: Optional parameters from request
        
        Returns:
            Dictionary of validated OpenAI parameters
        """
        if not parameters:
            parameters = {}
        
        # Use request parameters if provided, otherwise use config defaults
        openai_params = {
            "model": parameters.get("model", self.model_name),
            "max_tokens": parameters.get("max_tokens", self.max_tokens),
            "temperature": parameters.get("temperature", self.temperature),
            "top_p": parameters.get("top_p", self.top_p)
        }
        
        # Validate temperature
        if not 0.0 <= openai_params["temperature"] <= 2.0:
            openai_params["temperature"] = self.temperature
            logger.warning("Invalid temperature, using default", 
                          temperature=openai_params["temperature"])
        
        # Validate top_p
        if not 0.0 <= openai_params["top_p"] <= 1.0:
            openai_params["top_p"] = self.top_p
            logger.warning("Invalid top_p, using default", top_p=openai_params["top_p"])
        
        return openai_params
    
    async def infer(
        self, 
        messages: List["ChatMessage"], 
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None
    ) -> "InferenceResponse":
        """
        Perform inference using OpenAI API.
        
        Args:
            messages: List of chat messages
            parameters: Optional inference parameters
            context: Optional additional context
        
        Returns:
            InferenceResponse with generated content
        """
        start_time = time.time()
        
        try:
            # Prepare messages and parameters
            openai_messages = self._prepare_messages(messages, context)
            openai_params = self._extract_parameters(parameters)
            
            logger.info("Starting OpenAI inference", 
                       model=openai_params["model"],
                       messages_count=len(openai_messages),
                       max_tokens=openai_params["max_tokens"])
            
            # Make OpenAI API call
            response: ChatCompletion = await self.client.chat.completions.create(
                messages=openai_messages,
                **openai_params
            )
            
            # Extract response content
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Empty response from OpenAI")
            
            generated_content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            logger.info("OpenAI inference completed", 
                       model=openai_params["model"],
                       tokens_used=tokens_used,
                       processing_time_ms=processing_time_ms)
            
            # Create response
            from app.models import InferenceResponse
            return InferenceResponse(
                project_id="",  # Will be set by caller
                response=generated_content,
                model_used=openai_params["model"],
                tokens_used=tokens_used,
                processing_time_ms=processing_time_ms,
                metadata={
                    "provider": "openai",
                    "temperature": openai_params["temperature"],
                    "top_p": openai_params["top_p"],
                    "max_tokens": openai_params["max_tokens"],
                    "finish_reason": response.choices[0].finish_reason if response.choices else None
                }
            )
            
        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            
            logger.error("OpenAI inference failed", 
                        error=str(e),
                        error_type=type(e).__name__,
                        processing_time_ms=processing_time_ms)
            
            raise RuntimeError(f"OpenAI inference failed: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check OpenAI API health by making a simple request.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Make a minimal request to test connectivity
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            
            logger.debug("OpenAI health check passed", model=self.model_name)
            return True
            
        except Exception as e:
            logger.error("OpenAI health check failed", 
                        model=self.model_name,
                        error=str(e))
            return False
