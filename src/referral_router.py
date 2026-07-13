import logging
from typing import Dict, List, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

# Domain to channel mapping
DOMAIN_CHANNEL_MAPPING = {
    "Housing": "#housing-referrals",
    "Food": "#food-referrals",
    "Transportation": "#transport-referrals",
    "Utilities": "#utility-safety-referrals",
    "Safety": "#utility-safety-referrals"
}

# Domain prefix icons
DOMAIN_ICONS = {
    "Housing": "🏠",
    "Food": "🍎",
    "Transportation": "🚗",
    "Utilities": "⚡",
    "Safety": "🛡️"
}

DOMAIN_AGENCY_MAPPING = {
    "Housing": "Harborview Housing Alliance",
    "Food": "Neighbors' Table Food Network",
    "Transportation": "RideWell Community Transit",
    "Utilities": "BrightPath Utility Assistance Fund",
    "Safety": "SafeHaven Family Support Services"
}

def route_referrals(client: WebClient, beneficiary_id: str, flags: List[str], summary: str, timestamp_str: str, followup_responses: Optional[Dict[str, Any]] = None) -> None:
    """Routes flagged SDoH/HRSN domains to their respective Slack channels.

    Args:
        client (WebClient): The Slack Web API client.
        beneficiary_id (str): The ID of the beneficiary.
        flags (List[str]): List of flagged SDoH domains.
        summary (str): The plain-language AI summary sentence.
        timestamp_str (str): The screening completion timestamp.
        followup_responses (Optional[Dict[str, Any]]): Follow-up answers indexed by domain.
    """
    if not flags:
        logger.info("No flags triggered for beneficiary %s. Skipping routing.", beneficiary_id)
        return

    # Group flags by their target channels to avoid double posting
    channel_to_domains: Dict[str, List[str]] = {}
    for flag in flags:
        channel = DOMAIN_CHANNEL_MAPPING.get(flag)
        if channel:
            if channel not in channel_to_domains:
                channel_to_domains[channel] = []
            channel_to_domains[channel].append(flag)

    for channel, domains in channel_to_domains.items():
        # Check if Safety is flagged and is urgent (answers No or Unsure to safe place question)
        is_urgent_safety = False
        safety_ans_val = None
        
        if "Safety" in domains and followup_responses:
            safety_ans_val = followup_responses.get("Safety", {}).get("safety_safe_place")
            if safety_ans_val in ["No", "Unsure"]:
                is_urgent_safety = True

        # Formulate partner agencies and header
        agencies_list = []
        for dom in domains:
            if dom == "Safety" and is_urgent_safety:
                agencies_list.append("Beacon Crisis Shelter Network (emergency safe housing)")
                agencies_list.append("SafeHaven Family Support Services (ongoing support)")
            else:
                agencies_list.append(DOMAIN_AGENCY_MAPPING.get(dom))

        if is_urgent_safety:
            domains_str = " and ".join(domains).lower()
            header = f"🚨 {domains_str.capitalize()} need flagged — urgent"
            partner_label = "Partner Agencies:\n  • " + "\n  • ".join(agencies_list)
            safe_place_str = f"Safe place to stay currently: {safety_ans_val}\n"
        else:
            icons = "".join(DOMAIN_ICONS.get(dom, "") for dom in domains)
            domains_str = " and ".join(domains).lower()
            header = f"{icons} New {domains_str} need flagged"
            agencies_str = ", ".join(agencies_list) if agencies_list else "N/A"
            partner_label = f"Partner Agency: {agencies_str}"
            safe_place_str = ""

        # Format message text
        message_text = (
            f"{header}\n"
            f"Beneficiary ID: {beneficiary_id}\n"
            f"{safe_place_str}"
            f"{partner_label}\n"
            f"Screened: {timestamp_str}\n"
            f"Summary: {summary}"
        )

        # Append relevant follow-up questions and answers if present
        followup_details = []
        if followup_responses:
            for dom in domains:
                dom_followups = followup_responses.get(dom, {})
                if dom_followups:
                    followup_details.append(f"\nFollow-up for {dom}:")
                    from src.session_manager import FOLLOW_UP_QUESTIONS
                    for q_key, ans in dom_followups.items():
                        q_text = ""
                        for q in FOLLOW_UP_QUESTIONS.get(dom, []):
                            if q["key"] == q_key:
                                q_text = q["text"]
                                break
                        followup_details.append(f"  • {q_text or q_key}: {ans}")
                        
        if followup_details:
            message_text += "\n" + "\n".join(followup_details)

        try:
            logger.info("Routing referral to channel %s for domains %s", channel, domains)
            client.chat_postMessage(
                channel=channel,
                text=message_text
            )
            logger.info("Successfully routed referral to channel %s", channel)
        except SlackApiError as e:
            error_code = e.response.get("error", "")
            if error_code in ["not_in_channel", "channel_not_found"]:
                logger.error(
                    "Bot not in channel %s — cannot route %s flag(s). "
                    "Please invite the bot to the channel first.",
                    channel, ", ".join(domains)
                )
            else:
                logger.error(
                    "Slack API error posting to channel %s: %s",
                    channel, e.response.get("error", "unknown"), exc_info=True
                )
        except Exception as e:
            logger.error(
                "Unexpected error routing referral to channel %s: %s",
                channel, e, exc_info=True
            )
