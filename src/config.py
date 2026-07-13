import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load local environment variables from .env file if present
load_dotenv(dotenv_path=BASE_DIR / ".env")

class AppConfig:
    """Manages application-wide configuration and environment variables."""

    # Slack App Settings
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN", "")
    SLACK_SIGNING_SECRET: str = os.getenv("SLACK_SIGNING_SECRET", "")

    # Gemini settings (for future steps)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Application settings
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> bool:
        """Validates that crucial environment variables are loaded.

        Returns:
            bool: True if validation passes, False otherwise.
        """
        # Note: During initial startup verification, we might not have tokens yet,
        # but we should check if they are present for normal operations.
        missing = []
        if not cls.SLACK_BOT_TOKEN:
            missing.append("SLACK_BOT_TOKEN")
        if not cls.SLACK_APP_TOKEN:
            missing.append("SLACK_APP_TOKEN")

        if missing:
            # We don't raise an exception here so that verification can pass even
            # before the user adds their tokens. We'll log a warning instead.
            return False
        return True
