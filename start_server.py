"""
Development server startup script for DSP Front Door.
"""

import os
import sys
import argparse
import uvicorn
import structlog
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import config
from app.utils import setup_logging


def setup_development_environment():
    """Setup development environment variables if not set."""
    env_defaults = {
        "CONTROL_TOWER_BASE_URL": "http://localhost:5000",
        "CONTROL_TOWER_SUPERUSER_KEY": "dev-superuser-key",
        "OPENAI_API_KEY": "your-openai-api-key-here",
        "FD_HOST": "0.0.0.0",
        "FD_PORT": "8000",
        "FD_LOG_LEVEL": "INFO",
        "FD_API_KEY": ""  # No auth in dev mode
    }
    
    for key, default_value in env_defaults.items():
        if not os.getenv(key):
            os.environ[key] = default_value
            print(f"Set {key}={default_value}")


def check_dependencies():
    """Check if required services are available."""
    import httpx
    import asyncio
    
    async def check_control_tower():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{config.control_tower.base_url}/manifests", 
                                           headers={"X-Superuser-Key": config.control_tower.superuser_key})
                return response.status_code == 200
        except:
            return False
    
    # Check Control Tower
    control_tower_ok = asyncio.run(check_control_tower())
    
    if not control_tower_ok:
        print(f"⚠️  WARNING: Control Tower not available at {config.control_tower.base_url}")
        print("   Make sure DSP AI Control Tower is running")
        print("   The Front Door will start but inference requests may fail")
    else:
        print(f"✅ Control Tower available at {config.control_tower.base_url}")
    
    # Check OpenAI API key
    if not config.openai.api_key or config.openai.api_key == "your-openai-api-key-here":
        print("⚠️  WARNING: OpenAI API key not configured")
        print("   Set OPENAI_API_KEY environment variable")
        print("   Inference requests will fail without a valid API key")
    else:
        print("✅ OpenAI API key configured")


def main():
    """Main startup function."""
    parser = argparse.ArgumentParser(description="DSP Front Door Development Server")
    parser.add_argument("--host", default=None, help="Host to bind to (overrides config)")
    parser.add_argument("--port", type=int, default=None, help="Port to bind to (overrides config)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default=None, choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Log level (overrides config)")
    parser.add_argument("--dev", action="store_true", help="Development mode with default env vars")
    
    args = parser.parse_args()
    
    # Setup development environment if requested
    if args.dev:
        setup_development_environment()
    
    # Load configuration and use config values, with command line args as overrides
    from app.config import config
    
    # Priority: Command line args (if explicitly set) > Config values > Defaults
    actual_host = args.host if args.host is not None else config.front_door.host
    actual_port = args.port if args.port is not None else config.front_door.port  
    actual_log_level = args.log_level if args.log_level is not None else config.front_door.log_level
    
    # Setup logging
    setup_logging(actual_log_level)
    logger = structlog.get_logger(__name__)
    
    logger.info("Starting DSP Front Door Development Server")
    
    # Log configuration source for transparency
    if args.port is not None:
        logger.info("Using port from command line", port=actual_port, source="command_line")
    else:
        logger.info("Using port from configuration", port=actual_port, source="config_file")
    
    # Check dependencies
    check_dependencies()
    
    # Validate configuration
    try:
        config.validate()
        logger.info("Configuration validation passed")
    except ValueError as e:
        logger.error("Configuration validation failed", error=str(e))
        if not args.dev:
            sys.exit(1)
        logger.warning("Continuing in development mode despite configuration errors")
    
    # Start server
    logger.info("Starting server",
               host=actual_host,
               port=actual_port,
               reload=args.reload,
               log_level=actual_log_level)
    
    try:
        uvicorn.run(
            "app.main:app",
            host=actual_host,
            port=actual_port,
            log_level=actual_log_level.lower(),
            reload=args.reload,
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server startup failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
