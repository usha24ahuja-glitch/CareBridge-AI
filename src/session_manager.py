import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# State Constants
class SessionState:
    WELCOME = "welcome"
    Q1_BENEFICIARY = "q1_beneficiary"
    Q2_HOUSING_CONCERN = "q2_housing_concern"
    Q3_HOUSING_STABILITY = "q3_housing_stability"
    Q4_FOOD_SECURITY = "q4_food_security"
    Q5_TRANSPORTATION = "q5_transportation"
    Q6_UTILITIES = "q6_utilities"
    Q7_SAFETY = "q7_safety"
    COMPLETED = "completed"

# Question Registry containing Block Kit configurations
QUESTIONS: Dict[str, Dict[str, Any]] = {
    SessionState.Q1_BENEFICIARY: {
        "text": "Please enter the Beneficiary ID.",
        "type": "text",
        "key": "beneficiary_id",
        "title": "Beneficiary Intake"
    },
    SessionState.Q2_HOUSING_CONCERN: {
        "text": "In the past 12 months, has the beneficiary been worried about losing their housing?",
        "type": "select",
        "key": "housing_concern",
        "title": "Housing Domain",
        "options": ["Yes", "No"]
    },
    SessionState.Q3_HOUSING_STABILITY: {
        "text": "Is the beneficiary's current housing situation stable?",
        "type": "select",
        "key": "housing_stability",
        "title": "Housing Domain",
        "options": ["Yes", "No", "Unsure"]
    },
    SessionState.Q4_FOOD_SECURITY: {
        "text": "In the past 12 months, did the beneficiary worry that food would run out before there was money to buy more?",
        "type": "select",
        "key": "food_security",
        "title": "Food Domain",
        "options": ["Often true", "Sometimes true", "Never true"]
    },
    SessionState.Q5_TRANSPORTATION: {
        "text": "Has lack of reliable transportation prevented the beneficiary from attending medical appointments, work, or obtaining daily necessities?",
        "type": "select",
        "key": "transportation",
        "title": "Transportation Domain",
        "options": ["Yes", "No"]
    },
    SessionState.Q6_UTILITIES: {
        "text": "Has the utility company threatened to disconnect services in the beneficiary's home?",
        "type": "select",
        "key": "utilities",
        "title": "Utility Domain",
        "options": ["Yes", "No", "Already shut off"]
    },
    SessionState.Q7_SAFETY: {
        "header": "The following questions are asked of every beneficiary to ensure equitable and consistent screening.",
        "text": "During the past year, has the beneficiary experienced fear of, or physical harm from, a current or former partner?",
        "type": "select",
        "key": "safety",
        "title": "Interpersonal Safety Domain",
        "options": ["Yes", "No", "Prefer not to answer"]
    }
}

# The ordered sequence of questionnaire states
STATE_SEQUENCE: List[str] = [
    SessionState.WELCOME,
    SessionState.Q1_BENEFICIARY,
    SessionState.Q2_HOUSING_CONCERN,
    SessionState.Q3_HOUSING_STABILITY,
    SessionState.Q4_FOOD_SECURITY,
    SessionState.Q5_TRANSPORTATION,
    SessionState.Q6_UTILITIES,
    SessionState.Q7_SAFETY,
    SessionState.COMPLETED
]

class ScreeningSession:
    """Represents a single active clinical screening workflow."""
    
    def __init__(self, user_id: str):
        self.user_id: str = user_id
        self.state: str = SessionState.WELCOME
        self.beneficiary_id: str = ""
        self.responses: Dict[str, str] = {}
        self.thread_ts: str = ""
        self.followup_responses: Dict[str, Dict[str, str]] = {}
        self.followup_domain: Optional[str] = None
        self.followup_questions: List[Dict[str, Any]] = []
        self.followup_index: int = -1
        self.resume_state: Optional[str] = None
        
    def advance(self) -> str:
        """Advances the state machine to the next state."""
        current_index = STATE_SEQUENCE.index(self.state)
        if current_index < len(STATE_SEQUENCE) - 1:
            self.state = STATE_SEQUENCE[current_index + 1]
        logger.info("Session for user %s advanced to state: %s", self.user_id, self.state)
        return self.state

    def record_response(self, key: str, value: str) -> None:
        """Records an answer in the session responses registry.

        Args:
            key (str): The response domain key.
            value (str): The value/answer selected.
        """
        self.responses[key] = value
        logger.info("Recorded response for %s: '%s'", key, value)

    def record_followup_response(self, domain: str, key: str, value: str) -> None:
        if domain not in self.followup_responses:
            self.followup_responses[domain] = {}
        self.followup_responses[domain][key] = value
        logger.info("Recorded follow-up response for %s -> %s: '%s'", domain, key, value)

    def get_current_followup_question(self) -> Optional[Dict[str, Any]]:
        if not self.followup_domain or self.followup_index < 0 or self.followup_index >= len(self.followup_questions):
            return None
        q = self.followup_questions[self.followup_index]
        return {
            "domain": self.followup_domain,
            "key": q["key"],
            "text": q["text"],
            "options": q["options"],
            "question_index": self.followup_index
        }


class SessionManager:
    """Manages in-memory active patient screening sessions."""
    
    def __init__(self):
        self._sessions: Dict[str, ScreeningSession] = {}
        
    def get_session(self, user_id: str) -> Optional[ScreeningSession]:
        """Retrieves an existing session if active.

        Args:
            user_id (str): The Slack user ID.

        Returns:
            Optional[ScreeningSession]: The active session or None.
        """
        return self._sessions.get(user_id)
        
    def start_session(self, user_id: str) -> ScreeningSession:
        """Initializes a new session, replacing any existing active session.

        Args:
            user_id (str): The Slack user ID.

        Returns:
            ScreeningSession: The new active session.
        """
        session = ScreeningSession(user_id)
        self._sessions[user_id] = session
        logger.info("New screening session started for user: %s", user_id)
        return session
        
    def clear_session(self, user_id: str) -> None:
        """Discards an active session.

        Args:
            user_id (str): The Slack user ID.
        """
        if user_id in self._sessions:
            del self._sessions[user_id]
            logger.info("Screening session cleared for user: %s", user_id)


# Global singleton instance of SessionManager
session_manager = SessionManager()


def get_question_blocks(state: str) -> List[Dict[str, Any]]:
    """Generates Slack Block Kit components for the given screening state.

    Args:
        state (str): The current questionnaire state.

    Returns:
        List[Dict[str, Any]]: Array of Slack message blocks.
    """
    config = QUESTIONS.get(state)
    if not config:
        return []

    blocks = []

    # 1. Header or context indicating domain
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"📋 *CareBridge AI Screening* | *{config['title']}*"
            }
        ]
    })

    # 2. Optional warning/header notice (e.g. safety warning)
    if "header" in config:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⚠️ _{config['header']}_"
            }
        })

    # 3. Main Question Text
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*{config['text']}*"
        }
    })

    # 4. Input options / button elements
    elements = []
    if config["type"] == "text":
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "✍️ _Please reply directly in this chat window with the Beneficiary ID (letters, numbers, or dashes)._"
                }
            ]
        })
        # For text inputs, we still want a cancel button
        elements.append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Cancel Screening"
            },
            "style": "danger",
            "value": "cancel",
            "action_id": "hrs_cancel"
        })
        blocks.append({
            "type": "actions",
            "elements": elements
        })
    elif config["type"] == "select":
        for opt in config["options"]:
            elements.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": opt
                },
                "value": opt,
                "action_id": f"hrs_choice_{config['key']}_{opt.lower().replace(' ', '_')}"
            })
        
        # Add Cancel button at the end
        elements.append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Cancel"
            },
            "style": "danger",
            "value": "cancel",
            "action_id": "hrs_cancel"
        })
        
        blocks.append({
            "type": "actions",
            "elements": elements
        })

    return blocks


# Conditional follow-up questions for flagged domains
FOLLOW_UP_QUESTIONS = {
    "Housing": [
        {
            "key": "housing_staying",
            "text": "Is the beneficiary currently staying in their own home, with others temporarily, or in a shelter?",
            "options": ["In own home", "With others temporarily", "In a shelter"]
        },
        {
            "key": "housing_referral_request",
            "text": "Would the beneficiary like a referral to housing assistance services?",
            "options": ["Yes", "No"]
        }
    ],
    "Food": [
        {
            "key": "food_assistance_access",
            "text": "Does the beneficiary currently have access to a food pantry or SNAP/food assistance benefits?",
            "options": ["Yes", "No", "Unsure"]
        }
    ],
    "Transportation": [
        {
            "key": "transport_reliability",
            "text": "Does the beneficiary have any reliable access to transportation currently (public transit, family, rideshare)?",
            "options": ["Yes", "No"]
        }
    ],
    "Utilities": [
        {
            "key": "utility_at_risk",
            "text": "Which utility is at risk (electric, gas, water, multiple)?",
            "options": ["Electric", "Gas", "Water", "Multiple"]
        },
        {
            "key": "utility_contacted",
            "text": "Has the beneficiary already contacted the utility company about a payment plan?",
            "options": ["Yes", "No", "Unsure"]
        }
    ],
    "Safety": [
        {
            "key": "safety_safe_place",
            "text": "Does the beneficiary currently have a safe place to stay?",
            "options": ["Yes", "No", "Unsure"]
        }
    ]
}

def get_followup_question_blocks(q_detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    domain = q_detail["domain"]
    text = q_detail["text"]
    key = q_detail["key"]
    options = q_detail["options"]
    
    blocks = [
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📋 *CareBridge AI Screening* | *{domain} Follow-up*"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{text}*"
            }
        }
    ]
    
    elements = []
    for opt in options:
        elements.append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": opt
            },
            "value": opt,
            "action_id": f"hrs_followup_choice_{domain.lower()}_{key}_{opt.lower().replace(' ', '_')}"
        })
        
    elements.append({
        "type": "button",
        "text": {
            "type": "plain_text",
            "text": "Cancel"
        },
        "style": "danger",
        "value": "cancel",
        "action_id": "hrs_cancel"
    })
    
    blocks.append({
        "type": "actions",
        "elements": elements
    })
    
    return blocks

