import logging
from slack_bolt import App
from src.session_manager import session_manager, SessionState

logger = logging.getLogger(__name__)

def register_commands(app: App) -> None:
    """Registers slash command handlers with Bolt App instance."""

    @app.command("/hrs-screen")
    def handle_hrs_screen(ack, command, client, respond):
        """Initiates the guided HRSN patient screening, enforcing privacy rules."""
        ack()
        
        user_id = command.get("user_id")
        channel_id = command.get("channel_id")
        channel_name = command.get("channel_name")

        logger.info(
            "Command /hrs-screen triggered by user %s in channel %s (%s)",
            user_id, channel_id, channel_name
        )

        # Enforce SDoH privacy constraint: screenings must be conducted in DM
        is_dm = channel_name == "directmessage" or channel_id.startswith("D")

        # Welcome message block structure
        welcome_blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "CareBridge AI – HRSN Screening Navigator"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "I'll guide you through a Health-Related Social Needs screening. "
                        "The screening takes approximately 2 minutes and helps identify "
                        "social needs that may affect health outcomes.\n\n"
                        "Let's begin."
                    )
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Let's Begin"
                        },
                        "style": "primary",
                        "action_id": "hrs_begin"
                    }
                ]
            }
        ]

        # Extract thread_ts from command if present
        thread_ts = command.get("thread_ts")

        if not is_dm:
            try:
                # Open a direct message channel with the user
                dm_channel = client.conversations_open(users=user_id)
                dm_channel_id = dm_channel["channel"]["id"]
                
                # Start in-memory session for the user
                session = session_manager.start_session(user_id)
                if thread_ts:
                    session.thread_ts = thread_ts
                
                # Send the welcome message to the DM channel
                post_kwargs = {
                    "channel": dm_channel_id,
                    "text": "Welcome to CareBridge AI – HRSN Screening",
                    "blocks": welcome_blocks
                }
                if thread_ts:
                    post_kwargs["thread_ts"] = thread_ts
                client.chat_postMessage(**post_kwargs)
                
                # Notify the user ephemerally in the public channel
                respond(
                    text=(
                        "🔒 *Privacy Notice*: SDoH screenings collect sensitive patient data. "
                        "To protect beneficiary privacy, I have moved the screening to our direct message conversation."
                    ),
                    response_type="ephemeral"
                )
            except Exception as e:
                logger.error("Failed to open DM channel or redirect user: %s", e, exc_info=True)
                respond(
                    text="Sorry, I could not open a direct message channel. Please ensure you can receive DMs from apps.",
                    response_type="ephemeral"
                )
        else:
            # Already in DM, start session and post the welcome message directly
            session = session_manager.start_session(user_id)
            if thread_ts:
                session.thread_ts = thread_ts
                
            post_kwargs = {
                "channel": channel_id,
                "text": "Welcome to CareBridge AI – HRSN Screening",
                "blocks": welcome_blocks
            }
            if thread_ts:
                post_kwargs["thread_ts"] = thread_ts
            client.chat_postMessage(**post_kwargs)

    @app.command("/hrs-dashboard")
    def handle_hrs_dashboard(ack, command, client, respond):
        """Displays the leadership aggregate metrics dashboard."""
        ack()
        user_id = command.get("user_id")
        logger.info("Command /hrs-dashboard received from user: %s", user_id)
        
        from src.dashboard import generate_summary_digest
        from slack_sdk.errors import SlackApiError
        
        digest = generate_summary_digest()
        
        try:
            client.chat_postMessage(
                channel="#leadership-dashboard",
                text=digest
            )
            respond(
                text="📊 *Dashboard Posted*: The summary digest has been successfully posted to `#leadership-dashboard`.",
                response_type="ephemeral"
            )
        except SlackApiError as e:
            error_code = e.response.get("error", "")
            if error_code in ["not_in_channel", "channel_not_found"]:
                err_msg = (
                    "⚠️ *Error*: CareBridge AI is not in `#leadership-dashboard` channel. "
                    "Please invite the bot first by typing `/invite @CareBridge AI` in that channel."
                )
                logger.error("Bot not in #leadership-dashboard: %s", e)
            else:
                err_msg = f"⚠️ *Error*: Failed to post dashboard to `#leadership-dashboard`: {error_code}"
                logger.error("Slack API error posting dashboard: %s", e, exc_info=True)
            respond(text=err_msg, response_type="ephemeral")
        except Exception as e:
            logger.error("Unexpected error posting dashboard: %s", e, exc_info=True)
            respond(text="⚠️ *Error*: An unexpected error occurred.", response_type="ephemeral")

    logger.info("Slash command handlers registered.")
