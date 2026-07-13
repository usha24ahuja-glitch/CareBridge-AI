import logging
import re
from typing import Optional
from slack_bolt import App
from src.session_manager import session_manager, SessionState, get_question_blocks, QUESTIONS

logger = logging.getLogger(__name__)

def complete_screening(session, client, user_id: str, channel_id: str, thread_ts: Optional[str]) -> None:
    """Helper to finalize the screening intake process, compile metrics, and route referrals."""
    summary_text = (
        "🏁 *Screening Completed*\n\n"
        f"*Beneficiary ID*: `{session.responses.get('beneficiary_id', 'N/A')}`\n\n"
        "*Responses Recorded*:\n"
        f"• *Housing Concern*: {session.responses.get('housing_concern', 'N/A')}\n"
        f"• *Housing Stability*: {session.responses.get('housing_stability', 'N/A')}\n"
        f"• *Food Security*: {session.responses.get('food_security', 'N/A')}\n"
        f"• *Transportation*: {session.responses.get('transportation', 'N/A')}\n"
        f"• *Utilities*: {session.responses.get('utilities', 'N/A')}\n"
        f"• *Safety*: {session.responses.get('safety', 'N/A')}\n"
    )
    
    if session.followup_responses:
        summary_text += "\n*Follow-up Questions Answered*:\n"
        from src.session_manager import FOLLOW_UP_QUESTIONS
        for domain, answers in session.followup_responses.items():
            summary_text += f"  _*Domain: {domain}*_\n"
            for q_key, ans in answers.items():
                q_text = ""
                for q in FOLLOW_UP_QUESTIONS.get(domain, []):
                    if q["key"] == q_key:
                        q_text = q["text"]
                        break
                summary_text += f"  • {q_text or q_key}: *{ans}*\n"
                
    summary_text += "\nThank you. The screening has been successfully recorded."

    completion_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Screening Completed"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": summary_text
            }
        }
    ]

    post_kwargs = {
        "channel": channel_id,
        "text": "Screening Completed",
        "blocks": completion_blocks
    }
    if thread_ts:
        post_kwargs["thread_ts"] = thread_ts
    client.chat_postMessage(**post_kwargs)

    # Evaluate using deterministic SDoH Rule Engine
    from src.rule_engine import evaluate_screening
    evaluation = evaluate_screening(
        responses=session.responses,
        beneficiary_id=session.beneficiary_id,
        screened_by=user_id
    )
    logger.info("Rule engine evaluation results: %s", evaluation)

    # Save evaluation to completed screenings database
    from src.dashboard import save_screening, generate_summary_digest
    evaluation["status"] = "Completed"
    evaluation["followup_responses"] = session.followup_responses
    save_screening(evaluation)

    # Post immediate update to leadership dashboard
    try:
        digest = generate_summary_digest()
        client.chat_postMessage(channel="#leadership-dashboard", text=digest)
    except Exception as e:
        logger.error("Failed to post completed summary update: %s", e)

    # Format and send internal flag check message to DM channel
    flags = evaluation["flags"]
    if flags:
        flags_str = ", ".join(flags)
        internal_msg = f"Internal flag check: {flags_str} flagged for {session.beneficiary_id}"
    else:
        internal_msg = f"Internal flag check: No domains flagged for {session.beneficiary_id}"

    post_kwargs = {
        "channel": channel_id,
        "text": internal_msg
    }
    if thread_ts:
        post_kwargs["thread_ts"] = thread_ts
    client.chat_postMessage(**post_kwargs)

    # Generate and post simulated Slack AI summary
    from src.slack_ai import generate_slack_ai_summary
    ai_summary = generate_slack_ai_summary(flags)

    post_kwargs = {
        "channel": channel_id,
        "text": ai_summary
    }
    if thread_ts:
        post_kwargs["thread_ts"] = thread_ts
    client.chat_postMessage(**post_kwargs)

    # Format friendly timestamp and route referrals automatically to channels
    import datetime
    try:
        dt = datetime.datetime.fromisoformat(evaluation["timestamp"])
        friendly_ts = dt.strftime("%Y-%m-%d %I:%M %p")
    except Exception:
        friendly_ts = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")

    from src.referral_router import route_referrals
    route_referrals(
        client=client,
        beneficiary_id=session.beneficiary_id,
        flags=flags,
        summary=ai_summary,
        timestamp_str=friendly_ts,
        followup_responses=session.followup_responses
    )

    # Clear the user's session
    session_manager.clear_session(user_id)

def register_actions(app: App) -> None:
    """Registers action handlers for interactive Slack Block Kit events."""

    @app.action("hrs_begin")
    def handle_hrs_begin(ack, body, client, respond):
        """Triggered when the user clicks the 'Let's Begin' button on the welcome card."""
        ack()
        user_id = body.get("user", {}).get("id")
        channel_id = body.get("channel", {}).get("id")
        
        logger.info("User %s clicked 'Let's Begin' in channel %s", user_id, channel_id)

        # Retrieve or start session
        session = session_manager.get_session(user_id)
        if not session:
            session = session_manager.start_session(user_id)
            
        # Verify state is at WELCOME before initiating Q1
        if session.state == SessionState.WELCOME:
            session.advance() # Move to Q1_BENEFICIARY
            
            # Extract thread_ts from container, message, or session
            thread_ts = body.get("container", {}).get("thread_ts") or \
                        body.get("message", {}).get("thread_ts") or \
                        getattr(session, "thread_ts", None)
            
            logger.info("Actions.handle_hrs_begin: Updating welcome message (respond)...")
            try:
                respond(
                    replace_original=True,
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "🏁 *CareBridge AI Screening Started*."
                            }
                        }
                    ]
                )
                logger.info("Actions.handle_hrs_begin: respond() completed successfully.")
            except Exception as e:
                logger.error("Actions.handle_hrs_begin: respond() failed: %s", e, exc_info=True)
            
            logger.info("Actions.handle_hrs_begin: Generating Q1 question blocks...")
            try:
                q_blocks = get_question_blocks(session.state)
                logger.info("Actions.handle_hrs_begin: Q1 blocks generated: %s", q_blocks)
            except Exception as e:
                logger.error("Actions.handle_hrs_begin: get_question_blocks failed: %s", e, exc_info=True)
            
            logger.info("Actions.handle_hrs_begin: Posting Q1 message (chat_postMessage)...")
            try:
                post_kwargs = {
                    "channel": channel_id,
                    "text": "Question 1: Beneficiary Intake",
                    "blocks": q_blocks
                }
                if thread_ts:
                    post_kwargs["thread_ts"] = thread_ts
                response = client.chat_postMessage(**post_kwargs)
                logger.info("Actions.handle_hrs_begin: chat_postMessage completed successfully. Response ts: %s", response.get("ts"))
            except Exception as e:
                logger.error("Actions.handle_hrs_begin: chat_postMessage failed: %s", e, exc_info=True)

    @app.action(re.compile("^hrs_choice_(.+)$"))
    def handle_hrs_choice(ack, body, client, respond):
        """Processes choice selection buttons (Q2 through Q7)."""
        ack()
        
        user_id = body.get("user", {}).get("id")
        channel_id = body.get("channel", {}).get("id")
        action = body.get("actions", [{}])[0]
        action_id = action.get("action_id", "")
        value = action.get("value", "")

        # Extract domain key from action_id (e.g. "hrs_choice_housing_concern_yes" -> "housing_concern")
        domain_key = ""
        for k in ["housing_concern", "housing_stability", "food_security", "transportation", "utilities", "safety"]:
            if action_id.startswith(f"hrs_choice_{k}"):
                domain_key = k
                break

        logger.info(
            "User %s clicked choice button. Action: %s, Domain: %s, Value: %s",
            user_id, action_id, domain_key, value
        )

        session = session_manager.get_session(user_id)
        # Extract thread_ts from container, message, or session
        thread_ts = body.get("container", {}).get("thread_ts") or \
                    body.get("message", {}).get("thread_ts") or \
                    getattr(session, "thread_ts", None)

        if not session:
            respond(
                text="❌ *Session Expired*: No active screening session was found. Type `/hrs-screen` or `start` to begin a new session.",
                response_type="ephemeral"
            )
            return

        # Check if the clicked button matches the current expected question domain
        current_q_config = QUESTIONS.get(session.state, {})
        expected_key = current_q_config.get("key", "")

        if domain_key != expected_key:
            # User clicked an old button from a previous message
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="⚠️ *Out-of-order Selection*: That question has already been answered or is not currently active."
            )
            return

        # 1. Record the response
        session.record_response(domain_key, value)

        # 2. Update clicked message to remove buttons and show selected choice
        respond(
            replace_original=True,
            blocks=[
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"📋 *CareBridge AI Screening* | *{current_q_config.get('title')}*"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{current_q_config.get('text')}*\nSelected: *{value}*"
                    }
                }
            ]
        )

        # 3. Advance state
        # Define mapping of core completion keys to (domain_name, next_core_state)
        COMPLETED_KEYS_MAP = {
            "housing_stability": ("Housing", SessionState.Q4_FOOD_SECURITY),
            "food_security": ("Food", SessionState.Q5_TRANSPORTATION),
            "transportation": ("Transportation", SessionState.Q6_UTILITIES),
            "utilities": ("Utilities", SessionState.Q7_SAFETY),
            "safety": ("Safety", SessionState.COMPLETED)
        }

        # Helper to check if domain is flagged
        def is_domain_flagged(domain: str, val: str) -> bool:
            if domain == "Housing":
                concern = session.responses.get("housing_concern")
                return concern == "Yes" or val in ["No", "Unsure"]
            elif domain == "Food":
                return val in ["Often true", "Sometimes true"]
            elif domain == "Transportation":
                return val == "Yes"
            elif domain == "Utilities":
                return val in ["Yes", "Already shut off"]
            elif domain == "Safety":
                return val == "Yes"
            return False

        # 3. Determine next state / follow-up triggering
        if expected_key in COMPLETED_KEYS_MAP:
            domain, next_core_state = COMPLETED_KEYS_MAP[expected_key]
            if is_domain_flagged(domain, value):
                from src.session_manager import FOLLOW_UP_QUESTIONS
                session.followup_domain = domain
                session.followup_questions = FOLLOW_UP_QUESTIONS[domain]
                session.followup_index = 0
                session.resume_state = next_core_state
                session.state = "followup"
                next_state = "followup"
            else:
                next_state = session.advance()
        else:
            next_state = session.advance()

        # 4. Handle next state: COMPLETED, FOLLOWUP, or next question
        if next_state == "followup":
            # Retrieve the first follow-up question
            from src.session_manager import get_followup_question_blocks
            next_q = session.get_current_followup_question()
            q_blocks = get_followup_question_blocks(next_q)
            post_kwargs = {
                "channel": channel_id,
                "text": f"Follow-up: {next_q['text']}",
                "blocks": q_blocks
            }
            if thread_ts:
                post_kwargs["thread_ts"] = thread_ts
            client.chat_postMessage(**post_kwargs)
        elif next_state == SessionState.COMPLETED:
            complete_screening(session, client, user_id, channel_id, thread_ts)
        else:
            # Post the next question blocks
            next_blocks = get_question_blocks(next_state)
            post_kwargs = {
                "channel": channel_id,
                "text": f"Question: {next_state}",
                "blocks": next_blocks
            }
            if thread_ts:
                post_kwargs["thread_ts"] = thread_ts
            client.chat_postMessage(**post_kwargs)

    @app.action(re.compile("^hrs_followup_choice_(.+)$"))
    def handle_hrs_followup_choice(ack, body, client, respond):
        """Processes choice selection buttons for conditional follow-up questions."""
        ack()
        
        user_id = body.get("user", {}).get("id")
        channel_id = body.get("channel", {}).get("id")
        action = body.get("actions", [{}])[0]
        action_id = action.get("action_id", "")
        value = action.get("value", "")

        session = session_manager.get_session(user_id)
        thread_ts = body.get("container", {}).get("thread_ts") or \
                    body.get("message", {}).get("thread_ts") or \
                    getattr(session, "thread_ts", None)

        if not session:
            respond(
                text="❌ *Session Expired*: No active screening session was found. Type `/hrs-screen` or `start` to begin a new session.",
                response_type="ephemeral"
            )
            return

        q_detail = session.get_current_followup_question()
        if not q_detail:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="⚠️ *Out-of-order Selection*: That follow-up question is not currently active."
            )
            return

        expected_action_prefix = f"hrs_followup_choice_{q_detail['domain'].lower()}_{q_detail['key']}"
        if not action_id.startswith(expected_action_prefix):
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="⚠️ *Out-of-order Selection*: That follow-up question is not currently active."
            )
            return

        # 1. Record the response
        session.record_followup_response(q_detail["domain"], q_detail["key"], value)

        # 2. Update clicked message to remove buttons and show selected choice
        respond(
            replace_original=True,
            blocks=[
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"📋 *CareBridge AI Screening* | *{q_detail['domain']} Follow-up*"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{q_detail['text']}*\nSelected: *{value}*"
                    }
                }
            ]
        )

        # 3. Advance to next follow-up
        session.followup_index += 1
        next_q = session.get_current_followup_question()
        if next_q:
            from src.session_manager import get_followup_question_blocks
            q_blocks = get_followup_question_blocks(next_q)
            post_kwargs = {
                "channel": channel_id,
                "text": f"Follow-up: {next_q['text']}",
                "blocks": q_blocks
            }
            if thread_ts:
                post_kwargs["thread_ts"] = thread_ts
            client.chat_postMessage(**post_kwargs)
        else:
            # We finished this domain's follow-ups. Clear follow-up state.
            session.followup_domain = None
            session.followup_questions = []
            session.followup_index = -1
            
            # Transition back to resume state
            session.state = session.resume_state
            
            if session.state == SessionState.COMPLETED:
                complete_screening(session, client, user_id, channel_id, thread_ts)
            else:
                # Post the next core question block
                next_blocks = get_question_blocks(session.state)
                post_kwargs = {
                    "channel": channel_id,
                    "text": f"Question: {session.state}",
                    "blocks": next_blocks
                }
                if thread_ts:
                    post_kwargs["thread_ts"] = thread_ts
                client.chat_postMessage(**post_kwargs)

    @app.action("hrs_cancel")
    def handle_hrs_cancel(ack, body, client, respond):
        """Triggered when the user clicks 'Cancel' or 'Cancel Screening' on any card."""
        ack()
        user_id = body.get("user", {}).get("id")
        logger.info("User %s clicked Cancel screening button", user_id)

        # Clear the session if active
        session = session_manager.get_session(user_id)
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
            
            # Post immediate update to leadership dashboard
            try:
                digest = generate_summary_digest()
                client.chat_postMessage(channel="#leadership-dashboard", text=digest)
            except Exception as e:
                logger.error("Failed to post cancelled summary update: %s", e)

        # Update message to show it was cancelled
        respond(
            replace_original=True,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🛑 *Screening Cancelled*: The active screening session was aborted by the user."
                    }
                }
            ]
        )

    logger.info("Interactive action handlers registered.")
