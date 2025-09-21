"""
Entry point for the DSP Front Door system.
"""

import uvicorn
import structlog
from app.config import config
from app.utils import setup_logging


def main():
    """Main entry point for the DSP Front Door system."""
    try:
        # Setup logging
        setup_logging(config.front_door.log_level)
        logger = structlog.get_logger(__name__)
        
        logger.info("Starting DSP Front Door server",
                   host=config.front_door.host,
                   port=config.front_door.port,
                   log_level=config.front_door.log_level)
        
        # Run the server
        uvicorn.run(
            "app.main:app",
            host=config.front_door.host,
            port=config.front_door.port,
            log_level=config.front_door.log_level.lower(),
            reload=False,  # Set to True for development
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Failed to start server", error=str(e))
        raise


if __name__ == "__main__":
    main()
