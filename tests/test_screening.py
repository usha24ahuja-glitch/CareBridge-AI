import pytest
from src.session_manager import (
    session_manager, 
    SessionState, 
    ScreeningSession, 
    get_question_blocks, 
    QUESTIONS
)

def test_session_lifecycle():
    """Tests starting, advancing, recording, and clearing screening sessions."""
    user_id = "U_TEST_USER"
    
    # 1. Start Session
    session = session_manager.start_session(user_id)
    assert isinstance(session, ScreeningSession)
    assert session.user_id == user_id
    assert session.state == SessionState.WELCOME
    assert session.beneficiary_id == ""
    assert len(session.responses) == 0

    # Retrieve Session
    retrieved = session_manager.get_session(user_id)
    assert retrieved == session

    # 2. Advance to Q1
    next_state = session.advance()
    assert next_state == SessionState.Q1_BENEFICIARY
    assert session.state == SessionState.Q1_BENEFICIARY

    # Record Beneficiary ID
    session.beneficiary_id = "PAT-9901"
    session.record_response("beneficiary_id", "PAT-9901")
    assert session.responses["beneficiary_id"] == "PAT-9901"

    # 3. Advance to Q2 (Housing Concern)
    next_state = session.advance()
    assert next_state == SessionState.Q2_HOUSING_CONCERN
    session.record_response("housing_concern", "Yes")
    assert session.responses["housing_concern"] == "Yes"

    # 4. Advance through all remaining domains
    # Q3 (Stability)
    assert session.advance() == SessionState.Q3_HOUSING_STABILITY
    session.record_response("housing_stability", "No")
    
    # Q4 (Food)
    assert session.advance() == SessionState.Q4_FOOD_SECURITY
    session.record_response("food_security", "Sometimes true")

    # Q5 (Transportation)
    assert session.advance() == SessionState.Q5_TRANSPORTATION
    session.record_response("transportation", "Yes")

    # Q6 (Utilities)
    assert session.advance() == SessionState.Q6_UTILITIES
    session.record_response("utilities", "Already shut off")

    # Q7 (Safety)
    assert session.advance() == SessionState.Q7_SAFETY
    session.record_response("safety", "No")

    # Completed state
    assert session.advance() == SessionState.COMPLETED

    # 5. Clear Session
    session_manager.clear_session(user_id)
    assert session_manager.get_session(user_id) is None


def test_question_block_generation():
    """Tests that get_question_blocks generates correct Slack Block structures."""
    # Test WELCOME (should return empty since it's hardcoded welcome in command/event)
    welcome_blocks = get_question_blocks("non_existent_state")
    assert welcome_blocks == []

    # Test Q1 (Text Input Type)
    q1_blocks = get_question_blocks(SessionState.Q1_BENEFICIARY)
    assert len(q1_blocks) > 0
    # Q1 contains context block, main text section, instructions context, and cancel action
    assert q1_blocks[0]["type"] == "context"
    assert q1_blocks[1]["type"] == "section"
    assert "Please enter" in q1_blocks[1]["text"]["text"]
    assert q1_blocks[3]["type"] == "actions"
    assert q1_blocks[3]["elements"][0]["action_id"] == "hrs_cancel"

    # Test Q2 (Choice / Selection Button Type)
    q2_blocks = get_question_blocks(SessionState.Q2_HOUSING_CONCERN)
    assert len(q2_blocks) > 0
    assert q2_blocks[0]["type"] == "context"
    assert q2_blocks[1]["type"] == "section"
    assert "worried about losing" in q2_blocks[1]["text"]["text"]
    
    actions_block = q2_blocks[2]
    assert actions_block["type"] == "actions"
    # Yes, No, Cancel (3 elements)
    elements = actions_block["elements"]
    assert len(elements) == 3
    assert elements[0]["text"]["text"] == "Yes"
    assert elements[0]["action_id"] == "hrs_choice_housing_concern_yes"
    assert elements[1]["text"]["text"] == "No"
    assert elements[1]["action_id"] == "hrs_choice_housing_concern_no"
    assert elements[2]["text"]["text"] == "Cancel"
    assert elements[2]["action_id"] == "hrs_cancel"

    # Test Q7 (Contains Header / Notice)
    q7_blocks = get_question_blocks(SessionState.Q7_SAFETY)
    assert len(q7_blocks) > 0
    # Contains: context title, header warning, main question, actions (4 blocks)
    assert len(q7_blocks) == 4
    assert q7_blocks[1]["type"] == "section"
    assert "equitable and consistent" in q7_blocks[1]["text"]["text"]
    assert q7_blocks[2]["type"] == "section"
    assert "physical harm" in q7_blocks[2]["text"]["text"]
