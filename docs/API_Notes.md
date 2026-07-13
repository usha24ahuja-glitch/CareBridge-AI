# API Integration & Data Schema Notes: CareBridge AI

This file documents integration guidelines for the Slack Web/Events API, the Google Generative AI (Gemini) SDK, and the mock data schemas.

---

## 💬 Slack API Integration

### 1. Required Bot Scopes
To handle conversational flow and routing, the Slack App requires:
- `commands`: Allows the bot to register and handle `/hrs-screen` and `/hrs-dashboard` commands.
- `chat:write`: Allows the bot to send screening questions and post referrals.
- `im:write`: Allows the bot to open DMs with clinic staff.
- `im:history`: Allows the bot to receive events and history for direct messages.
- `app_mentions:read`: Allows the bot to listen to app mention events.
- `channels:read` / `groups:read`: Allows listing channels for mapping referrals.

### 2. Bolt Routing Framework
Standard event routing setup:
```python
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

@app.command("/hrs-screen")
def handle_screening_command(ack, respond, command, client):
    ack()
    # Trigger intake flow
    ...

@app.action("submit_screening_response")
def handle_interactive_submit(ack, body, client):
    ack()
    # Handle user answer clicks
    ...
```

---

## 🤖 Gemini API Integration

The app uses the `google-genai` client for structured extraction and summaries.

### 1. Need Extraction Schema
We leverage Pydantic to enforce structured outputs from Gemini:
```python
from pydantic import BaseModel, Field

class NeedClassification(BaseModel):
    housing_insecurity: bool = Field(description="Patient has unstable housing or threat of eviction.")
    food_insecurity: bool = Field(description="Patient lacks reliable access to nutritious food.")
    transportation_barrier: bool = Field(description="Lack of transportation impacts medical/work appointments.")
    utility_instability: bool = Field(description="Utility shutoff warning or past-due balance.")
    safety_concern: bool = Field(description="Patient feels unsafe in their home environment.")
    urgency_score: int = Field(description="Urgency of need from 1 (low) to 5 (immediate danger/crisis).")
    need_explanation: str = Field(description="Clinically oriented summary of positive findings.")
```

### 2. AI Summaries
For Patient Summaries and Executive Briefings, system prompts guide the layout structure. Prompt templates are stored under `prompts/`.

---

## 🗄️ Mock Data Schemas

### 1. Screenings (`data/sample_screenings.json`)
Tracks individual patient screening questionnaires and AI outputs.
```json
[
  {
    "screening_id": "SCR-2026-0001",
    "patient_id": "PAT-8801",
    "zip_code": "90210",
    "language": "English",
    "timestamp": "2026-07-10T10:00:00Z",
    "completed_by": "U123456",
    "raw_responses": {
      "housing": "Worried about paying rent next month.",
      "food": "No, we have food security.",
      "transportation": "Sometimes miss appointments because of no car.",
      "utilities": "No issues.",
      "safety": "Yes, live in a high-crime neighborhood but feel safe indoors."
    },
    "classification": {
      "housing_insecurity": true,
      "food_insecurity": false,
      "transportation_barrier": true,
      "utility_instability": false,
      "safety_concern": false,
      "urgency_score": 3,
      "need_explanation": "Patient reports concern regarding rent payment and transportation limitations."
    },
    "status": "Completed"
  }
]
```

### 2. Referrals (`data/referrals.json`)
Tracks routed actions, who is assigned, and status.
```json
[
  {
    "referral_id": "REF-2026-0001",
    "screening_id": "SCR-2026-0001",
    "domain": "housing",
    "assigned_channel": "#referral-housing",
    "status": "Pending",
    "matched_resources": ["RES-0001", "RES-0003"],
    "created_at": "2026-07-10T10:05:00Z",
    "updated_at": "2026-07-10T10:05:00Z"
  }
]
```

### 3. Resources (`data/resources.json`)
A static list of local social services that can be matched dynamically.
```json
[
  {
    "resource_id": "RES-0001",
    "name": "Metro Shelter & Housing Assistance",
    "domain": "housing",
    "contact": "555-0192",
    "address": "123 Shelter Way, Metro City",
    "description": "Short-term housing grants, emergency sheltering, and landlord negotiation services."
  }
]
```
