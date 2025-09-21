"""
Utility functions for the DSP Front Door system.
"""

import structlog
import sys
from typing import Dict, Any


def setup_logging(log_level: str = "INFO") -> None:
    """
    Setup structured logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Configure structlog
    structlog.configure(
        processors=[
            # Add log level
            structlog.stdlib.filter_by_level,
            # Add timestamp
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # JSON formatter for production, dev formatter for development
            structlog.dev.ConsoleRenderer() if sys.stdout.isatty() else structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set log level
    import logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO)
    )


def format_error_response(error: Exception, details: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Format error for API response.
    
    Args:
        error: Exception that occurred
        details: Additional error details
    
    Returns:
        Formatted error dictionary
    """
    error_type = type(error).__name__
    error_message = str(error)
    
    response = {
        "error": error_type,
        "message": error_message
    }
    
    if details:
        response["details"] = details
    
    return response


def mask_sensitive_data(data: Dict[str, Any], sensitive_keys: list = None) -> Dict[str, Any]:
    """
    Mask sensitive data in a dictionary for logging.
    
    Args:
        data: Dictionary to mask
        sensitive_keys: List of keys to mask (default: common sensitive keys)
    
    Returns:
        Dictionary with masked sensitive values
    """
    if sensitive_keys is None:
        sensitive_keys = ['api_key', 'secret_key', 'password', 'token', 'auth', 'authorization']
    
    masked_data = data.copy()
    
    def mask_recursive(obj, keys_to_mask):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if any(sensitive_key in key.lower() for sensitive_key in keys_to_mask):
                    obj[key] = "***MASKED***"
                elif isinstance(value, (dict, list)):
                    mask_recursive(value, keys_to_mask)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    mask_recursive(item, keys_to_mask)
    
    mask_recursive(masked_data, sensitive_keys)
    return masked_data
