from src.slack_ai import generate_slack_ai_summary

def test_slack_ai_summary_generation():
    """Tests the natural language summary generation for various flagging states."""
    
    # 1. Multiple flags (Housing, Transportation, Utilities)
    flags_3 = ["Housing", "Transportation", "Utilities"]
    expected_3 = (
        "This beneficiary is currently facing housing instability, lacking reliable transportation, "
        "and at risk of utility shutoff. These needs may benefit from coordinated referral support."
    )
    assert generate_slack_ai_summary(flags_3) == expected_3

    # 2. Single flag (Food)
    flags_1 = ["Food"]
    expected_1 = (
        "This beneficiary is lacking reliable access to food. "
        "These needs may benefit from coordinated referral support."
    )
    assert generate_slack_ai_summary(flags_1) == expected_1

    # 3. Two flags (Housing, Safety)
    flags_2 = ["Housing", "Safety"]
    expected_2 = (
        "This beneficiary is currently facing housing instability and facing safety concerns. "
        "These needs may benefit from coordinated referral support."
    )
    assert generate_slack_ai_summary(flags_2) == expected_2

    # 4. Empty flags
    expected_empty = (
        "This beneficiary has screened negative for all core health-related social needs. "
        "No immediate referral support is required at this time."
    )
    assert generate_slack_ai_summary([]) == expected_empty
