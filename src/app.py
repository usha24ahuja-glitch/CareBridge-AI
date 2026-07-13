import sys
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from src.config import AppConfig
from src.utils import setup_logging
from src.handlers import register_commands, register_events, register_actions

# Initialize application-wide logging
logger = setup_logging()

# Instantiate the Bolt App.
# We fall back to dummy strings to prevent instantiation crashes during dry-run verification
# if environment variables are not yet defined in the environment.
app = App(
    token=AppConfig.SLACK_BOT_TOKEN or "xoxb-dummy-token-verification",
    signing_secret=AppConfig.SLACK_SIGNING_SECRET or "dummy-signing-secret",
    token_verification_enabled=False
)

# Register command, event, and interactive action routers
register_commands(app)
register_events(app)
register_actions(app)

def main(dry_run: bool = False) -> None:
    """Bootstraps and starts the CareBridge AI Slack Bolt application.

    Args:
        dry_run (bool): If True, validates initialization and exits without
                        starting the Socket Mode handler.
    """
    logger.info("Initializing CareBridge AI - HRSN Screening Navigator...")
    
    # Check environmental variables
    has_tokens = AppConfig.validate()
    
    if dry_run:
        logger.info("Initialization check complete. Environment tokens loaded: %s", has_tokens)
        logger.info("Dry-run verification passed successfully!")
        return

    if not has_tokens:
        logger.error(
            "CRITICAL CONFIGURATION ERROR: Crucial environment variables are missing.\n"
            "Please copy '.env.example' to '.env' and fill in your Slack credentials.\n"
            "Required keys: SLACK_BOT_TOKEN, SLACK_APP_TOKEN\n"
            "Shutting down."
        )
        sys.exit(1)

    try:
        logger.info("Starting Slack Socket Mode Handler...")
        handler = SocketModeHandler(app, AppConfig.SLACK_APP_TOKEN)
        
        # Start background dashboard scheduler
        from src.dashboard import run_scheduler
        run_scheduler(app.client)
        
        handler.start()
    except Exception as e:
        logger.error("Failed to start Socket Mode Handler: %s", e, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Check if validation arguments are passed (used for automated verification tests)
    is_dry_run = "--verify" in sys.argv or "verify" in sys.argv
    main(dry_run=is_dry_run)
