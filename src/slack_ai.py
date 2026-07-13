from typing import List

def generate_slack_ai_summary(flags: List[str]) -> str:
    """Uses simulated Slack AI text generation capabilities to build a natural language summary.

    Args:
        flags (List[str]): List of SDoH flagged domains.

    Returns:
        str: A clean, human-readable summary sentence.
    """
    if not flags:
        return "This beneficiary has screened negative for all core health-related social needs. No immediate referral support is required at this time."

    mappings = {
        "Housing": "currently facing housing instability",
        "Food": "lacking reliable access to food",
        "Transportation": "lacking reliable transportation",
        "Utilities": "at risk of utility shutoff",
        "Safety": "facing safety concerns"
    }

    # Extract descriptions for the flagged domains
    desc_list = [mappings[flag] for flag in flags if flag in mappings]

    if not desc_list:
        return "This beneficiary has screened negative for all core health-related social needs. No immediate referral support is required at this time."

    # Format descriptions with correct English punctuation
    if len(desc_list) == 1:
        phrase = desc_list[0]
    elif len(desc_list) == 2:
        phrase = f"{desc_list[0]} and {desc_list[1]}"
    else:
        phrase = ", ".join(desc_list[:-1]) + f", and {desc_list[-1]}"

    return f"This beneficiary is {phrase}. These needs may benefit from coordinated referral support."
