import logging
from slack_bolt import App
from src.session_manager import session_manager, SessionState, get_question_blocks

logger = logging.getLogger(__name__)

def register_events(app: App) -> None:
    """Registers event handlers with the Bolt App instance."""

    @app.event("app_mention")
    def handle_app_mentions(event, say):
        """Stub handler for when the CareBridge bot is mentioned in a channel."""
        user_id = event.get("user")
        channel_id = event.get("channel")
        logger.info("Bot mentioned in channel %s by user: %s", channel_id, user_id)
        say(
            f"Hello <@{user_id}>! I am **CareBridge AI**, your SDoH Screening Navigator. "
            "To begin a screening, run the `/hrs-screen` slash command, or send me a direct message."
        )

    @app.event("assistant_thread_started")
    def handle_assistant_thread_started(event, say, client):
        """Triggered when a user starts a new thread in the Assistant view."""
        assistant_thread = event.get("assistant_thread", {})
        channel_id = assistant_thread.get("channel_id")
        thread_ts = assistant_thread.get("id")
        user_id = event.get("user") or assistant_thread.get("user_id")
        
        logger.info(
            "Assistant thread started. User: %s, Channel: %s, Thread TS: %s",
            user_id, channel_id, thread_ts
        )
        
        # Start a new session for the user
        session = session_manager.start_session(user_id)
        session.thread_ts = thread_ts
        
        # Set thread status to indicate preparing
        try:
            client.assistant_threads_setStatus(
                channel_id=channel_id,
                thread_ts=thread_ts,
                status="preparing screening welcome..."
            )
        except Exception as e:
            logger.error("Failed to set status on assistant thread: %s", e)
            
        # Post the welcome message inside the thread!
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
        
        try:
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text="Welcome to CareBridge AI – HRSN Screening",
                blocks=welcome_blocks
            )
        except Exception as e:
            logger.error("Failed to post welcome message to assistant thread: %s", e, exc_info=True)

    @app.event("assistant_thread_context_changed")
    def handle_assistant_thread_context_changed(event):
        """Logged when the user changes context in the assistant view."""
        logger.info("Assistant thread context changed event received: %s", event)

    @app.event("message")
    def handle_message_events(event, say, client):
        """Processes messages in direct message channels, managing the screening conversation state."""
        channel_type = event.get("channel_type")
        channel_id = event.get("channel", "")
        user_id = event.get("user")
        raw_text = event.get("text", "")
        clean_text = raw_text.strip()
        lower_text = clean_text.lower()
        
        # Avoid processing bot's own posts or other bots
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return

        # We process messages within Direct Messages (im) or if channel starts with D
        is_im = channel_type == "im" or channel_id.startswith("D")
        
        logger.info(
            "Incoming message event. User: %s, Channel: %s, Channel Type: %s, Is IM: %s, Text: '%s'",
            user_id, channel_id, channel_type, is_im, clean_text
        )

        if is_im:
            # Fetch user session
            session = session_manager.get_session(user_id)
            if session:
                logger.info("Found active session for user %s: state=%s, thread_ts=%s", user_id, session.state, getattr(session, "thread_ts", None))
            else:
                logger.info("No active session found for user %s", user_id)

            # Determine target thread_ts for replies
            thread_ts = event.get("thread_ts")
            if not thread_ts and session:
                thread_ts = getattr(session, "thread_ts", None)

            # Helper function to reply within the thread context if present
            def reply(text="", blocks=None, **kwargs):
                if thread_ts:
                    kwargs["thread_ts"] = thread_ts
                return say(text=text, blocks=blocks, **kwargs)

            # Global commands: cancel
            if lower_text in ["cancel", "abort", "exit", "stop"]:
                if session:
                    # Save a cancelled screening record before clearing
                    import datetime
                    from src.dashboard import save_screening, generate_summary_digest
                    cancel_record = {
                        "beneficiary_id": session.beneficiary_id or "Anonymous",
                        "flags": [],
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "screened_by": user_id,
                        "status": "Cancelled"
                    }
                    save_screening(cancel_record)
                    
                    session_manager.clear_session(user_id)
                    reply(
                        "🛑 *Screening Cancelled*: The active screening session has been discarded. "
                        "To start a new screening, type `/hrs-screen` or reply with `start`."
                    )
                    
                    # Post update to leadership dashboard
                    try:
                        digest = generate_summary_digest()
                        client.chat_postMessage(channel="#leadership-dashboard", text=digest)
                    except Exception as e:
                        logger.error("Failed to post cancelled summary update: %s", e)
                else:
                    reply("There is no active screening session to cancel.")
                return

            # Determine start / summary triggers
            is_start_trigger = lower_text in ["start", "begin", "screen", "new"] or \
                               any(keyword in lower_text for keyword in ["start a new", "begin screening", "new screening"])
            is_summary_trigger = "summary" in lower_text or "dashboard" in lower_text

            # Global commands: start / help (if no session active, or if session is in WELCOME state and they trigger start)
            if not session or (session.state == SessionState.WELCOME and is_start_trigger):
                if is_start_trigger:
                    logger.info("Initializing SDoH screening welcome sequence for user %s", user_id)
                    # Start screening welcome sequence
                    session = session_manager.start_session(user_id)
                    # If this message was in a thread, save it to the new session
                    if thread_ts:
                        session.thread_ts = thread_ts
                        
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
                    reply(text="Welcome to CareBridge AI – HRSN Screening", blocks=welcome_blocks)
                elif is_summary_trigger:
                    # Provide dashboard stub response
                    reply(
                        "Welcome to the **CareBridge AI - Operations Dashboard**.\n"
                        "This is a stub response. Dashboard report generation will be added in future steps."
                    )
                else:
                    # Provide helpful instructions
                    reply(
                        f"Hello! I am **CareBridge AI**, your SDoH Screening Navigator.\n"
                        "To start a guided screening, please reply with `start` or run `/hrs-screen`."
                    )
                return

            # Active Session processing
            if session.state == SessionState.WELCOME:
                reply("Please click *Let's Begin* above to start the screening, or type `cancel` to exit.")
            
            elif session.state == SessionState.Q1_BENEFICIARY:
                # Validate the Beneficiary ID input
                if not clean_text or len(clean_text) < 2:
                    reply("⚠️ *Invalid Response*: Please enter a valid Beneficiary ID (at least 2 characters long).")
                    return
                
                # Save the input ID
                session.beneficiary_id = clean_text
                session.record_response("beneficiary_id", clean_text)
                
                # Advance session state
                next_state = session.advance()
                
                # Get next question blocks (Q2: Housing Concern) and send
                q_blocks = get_question_blocks(next_state)
                reply(text="Question 2: Housing Concern", blocks=q_blocks)
                
            else:
                # The user is in a state that requires button clicks (Q2 through Q7)
                reply(
                    "⚠️ *Selection Required*: Please respond to the current question by clicking one of the buttons above, "
                    "or type `cancel` to terminate the session."
                )

    logger.info("Event handlers registered.")
