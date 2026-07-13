import logging
import sys
from src.config import AppConfig

def setup_logging() -> logging.Logger:
    """Configures the logging format and level for the application.

    Returns:
        logging.Logger: The configured root logger.
    """
    log_level_str = AppConfig.LOG_LEVEL.upper()
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    level = log_levels.get(log_level_str, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger("CareBridge")
    logger.info("Logging configured at level: %s", log_level_str)
    return logger
