from unittest.mock import MagicMock
import pytest
from slack_sdk.errors import SlackApiError
from src.referral_router import route_referrals

def test_route_referrals_success():
    """Tests that domains are mapped and posted to the correct Slack channels."""
    client_mock = MagicMock()
    
    # Test routing multiple flags
    # Housing -> #housing-referrals
    # Utilities -> #utility-safety-referrals
    flags = ["Housing", "Utilities"]
    summary = "Patient is facing housing instability and utility shutoff."
    
    route_referrals(
        client=client_mock,
        beneficiary_id="C1234",
        flags=flags,
        summary=summary,
        timestamp_str="2026-07-11 02:58 AM"
    )
    
    # Should call postMessage twice (once for #housing-referrals, once for #utility-safety-referrals)
    assert client_mock.chat_postMessage.call_count == 2
    
    calls = client_mock.chat_postMessage.call_args_list
    channels_posted = [call.kwargs["channel"] for call in calls]
    assert set(channels_posted) == {"#housing-referrals", "#utility-safety-referrals"}

def test_route_referrals_combines_utilities_and_safety():
    """Tests that Utilities and Safety are grouped together for #utility-safety-referrals."""
    client_mock = MagicMock()
    
    flags = ["Utilities", "Safety"]
    summary = "Patient is at risk of utility shutoff and safety concerns."
    
    route_referrals(
        client=client_mock,
        beneficiary_id="C1234",
        flags=flags,
        summary=summary,
        timestamp_str="2026-07-11 02:58 AM"
    )
    
    # Should call postMessage exactly once since both map to the same channel
    assert client_mock.chat_postMessage.call_count == 1
    call_kwargs = client_mock.chat_postMessage.call_args.kwargs
    assert call_kwargs["channel"] == "#utility-safety-referrals"
    assert "⚡🛡️ New utilities and safety need flagged" in call_kwargs["text"]

def test_route_referrals_handles_not_in_channel_gracefully(caplog):
    """Tests that the router logs a clear error instead of crashing if the bot is not in the channel."""
    client_mock = MagicMock()
    
    # Simulate SlackApiError (not_in_channel)
    from slack_sdk.web.slack_response import SlackResponse
    
    headers = {"content-type": "application/json"}
    raw_response = SlackResponse(
        client=client_mock,
        http_verb="POST",
        api_url="https://slack.com/api/chat.postMessage",
        req_args={},
        data={"ok": False, "error": "not_in_channel"},
        headers=headers,
        status_code=200
    )
    client_mock.chat_postMessage.side_effect = SlackApiError("Slack API Error", response=raw_response)
    
    with caplog.at_level("ERROR"):
        route_referrals(
            client=client_mock,
            beneficiary_id="C1234",
            flags=["Housing"],
            summary="Housing needs summary",
            timestamp_str="2026-07-11 02:58 AM"
        )
        
    assert "Bot not in channel #housing-referrals — cannot route Housing flag(s)" in caplog.text
