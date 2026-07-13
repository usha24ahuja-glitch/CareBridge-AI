import pytest
from unittest.mock import MagicMock
from src.session_manager import ScreeningSession, SessionState, FOLLOW_UP_QUESTIONS
from src.referral_router import route_referrals

def test_session_followup_traversal():
    """Verifies that follow-up questions are traversed sequentially for a active domain."""
    session = ScreeningSession("user_123")
    
    # Simulate flagging Housing domain
    session.followup_domain = "Housing"
    session.followup_questions = FOLLOW_UP_QUESTIONS["Housing"]
    session.followup_index = 0
    session.resume_state = SessionState.Q4_FOOD_SECURITY
    
    # First follow-up question
    q1 = session.get_current_followup_question()
    assert q1 is not None
    assert q1["domain"] == "Housing"
    assert q1["key"] == "housing_staying"
    
    session.record_followup_response("Housing", q1["key"], "In own home")
    
    # Advance to second question
    session.followup_index += 1
    q2 = session.get_current_followup_question()
    assert q2 is not None
    assert q2["domain"] == "Housing"
    assert q2["key"] == "housing_referral_request"
    
    session.record_followup_response("Housing", q2["key"], "Yes")
    
    # Out of range
    session.followup_index += 1
    q3 = session.get_current_followup_question()
    assert q3 is None
    
    # Check recorded followups
    assert session.followup_responses == {
        "Housing": {
            "housing_staying": "In own home",
            "housing_referral_request": "Yes"
        }
    }

def test_route_referrals_includes_partner_agencies_and_followups():
    """Verifies that referral messages include the partner agency name and relevant follow-up details."""
    client_mock = MagicMock()
    
    flags = ["Housing", "Food"]
    summary = "Beneficiary needs food and housing help."
    followup_responses = {
        "Housing": {
            "housing_staying": "In a shelter",
            "housing_referral_request": "Yes"
        },
        "Food": {
            "food_assistance_access": "No"
        }
    }
    
    route_referrals(
        client=client_mock,
        beneficiary_id="C999",
        flags=flags,
        summary=summary,
        timestamp_str="2026-07-12 02:30 AM",
        followup_responses=followup_responses
    )
    
    assert client_mock.chat_postMessage.call_count == 2
    calls = client_mock.chat_postMessage.call_args_list
    
    # Extract housing call
    housing_call = [call for call in calls if call.kwargs["channel"] == "#housing-referrals"][0]
    housing_text = housing_call.kwargs["text"]
    assert "Partner Agency: Harborview Housing Alliance" in housing_text
    assert "Is the beneficiary currently staying in their own home" in housing_text
    assert "In a shelter" in housing_text
    # Should NOT contain food follow-up questions
    assert "food_assistance_access" not in housing_text
    assert "Neighbors' Table Food Network" not in housing_text
    
    # Extract food call
    food_call = [call for call in calls if call.kwargs["channel"] == "#food-referrals"][0]
    food_text = food_call.kwargs["text"]
    assert "Partner Agency: Neighbors' Table Food Network" in food_text
    assert "Does the beneficiary currently have access to a food pantry" in food_text
    assert "No" in food_text
    # Should NOT contain housing follow-up questions
    assert "housing_staying" not in food_text
    assert "Harborview Housing Alliance" not in food_text

def test_route_referrals_safety_urgent():
    """Verifies that an urgent Safety flag (safe place = No or Unsure) triggers both agencies and the urgent marker."""
    client_mock = MagicMock()
    
    flags = ["Safety"]
    summary = "Safety concerns flagged."
    followup_responses = {
        "Safety": {
            "safety_safe_place": "No"
        }
    }
    
    route_referrals(
        client=client_mock,
        beneficiary_id="C888",
        flags=flags,
        summary=summary,
        timestamp_str="2026-07-12 02:40 AM",
        followup_responses=followup_responses
    )
    
    assert client_mock.chat_postMessage.call_count == 1
    call_kwargs = client_mock.chat_postMessage.call_args.kwargs
    assert call_kwargs["channel"] == "#utility-safety-referrals"
    
    msg_text = call_kwargs["text"]
    assert "🚨 Safety need flagged — urgent" in msg_text
    assert "Safe place to stay currently: No" in msg_text
    assert "Beacon Crisis Shelter Network (emergency safe housing)" in msg_text
    assert "SafeHaven Family Support Services (ongoing support)" in msg_text

def test_route_referrals_safety_non_urgent():
    """Verifies that a standard Safety flag (safe place = Yes) triggers only SafeHaven and no urgent marker."""
    client_mock = MagicMock()
    
    flags = ["Safety"]
    summary = "Safety concerns flagged."
    followup_responses = {
        "Safety": {
            "safety_safe_place": "Yes"
        }
    }
    
    route_referrals(
        client=client_mock,
        beneficiary_id="C888",
        flags=flags,
        summary=summary,
        timestamp_str="2026-07-12 02:40 AM",
        followup_responses=followup_responses
    )
    
    assert client_mock.chat_postMessage.call_count == 1
    call_kwargs = client_mock.chat_postMessage.call_args.kwargs
    assert call_kwargs["channel"] == "#utility-safety-referrals"
    
    msg_text = call_kwargs["text"]
    assert "🚨" not in msg_text
    assert "urgent" not in msg_text
    assert "Safe place to stay currently:" not in msg_text
    assert "SafeHaven Family Support Services" in msg_text
    assert "Beacon Crisis Shelter Network" not in msg_text
def test_route_referrals_utilities():
    """Verifies that Utilities domain mapping correctly routes and includes BrightPath Utility Assistance Fund."""
    client_mock = MagicMock()
    
    flags = ["Utilities"]
    summary = "Utility shutoff risk flagged."
    
    route_referrals(
        client=client_mock,
        beneficiary_id="C777",
        flags=flags,
        summary=summary,
        timestamp_str="2026-07-12 02:50 AM"
    )
    
    assert client_mock.chat_postMessage.call_count == 1
    call_kwargs = client_mock.chat_postMessage.call_args.kwargs
    assert call_kwargs["channel"] == "#utility-safety-referrals"
    
    msg_text = call_kwargs["text"]
    assert "Partner Agency: BrightPath Utility Assistance Fund" in msg_text
