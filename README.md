# CareBridge AI — HRSN Screening Navigator

A Slack agent that digitizes Health-Related Social Needs (HRSN) screening for healthcare clinics and nonprofits — built for the Slack Agent Builder Challenge (Slack Agent for Good track).

Grounded in a real capstone research problem: a healthcare nonprofit implementing CMS's Accountable Health Communities Model saw HRSN screening completion rates as low as 1%, due to paper forms, physician-only burden, and a two-month manual Excel reporting cycle. CareBridge AI replaces that entire process with a conversational Slack agent.

## Features
- Conversational HRSN screening across five domains: Housing, Food, Transportation, Utilities, Safety
- Deterministic rule engine that flags needs transparently
- Domain-specific follow-up questions, triggered only for flagged domains
- AI-generated plain-language summaries via Slack's native Agents & AI Apps framework
- Automatic referral routing to topic-based channels, with named partner agencies
- Dedicated emergency shelter referral path for safety-critical cases
- On-demand leadership dashboard (`/hrs-dashboard`) with real-time completion metrics

## Tech Stack
- Python, Slack Bolt framework
- Slack Socket Mode (no public server required)
- Slack Agents & AI Apps framework (Assistant thread lifecycle, `assistant:write`)
- JSON file storage for completed screenings and dashboard analytics

## Setup

1. Clone this repo and create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # (Windows)
   # or
   source .venv/bin/activate # (Mac/Linux)
   pip install -r requirements.txt
   ```

2. Create a Slack app using the manifest in this repo (`slack.yaml` or `config/slack_manifest.yaml`) at api.slack.com/apps.

3. Generate credentials:
   - Bot Token (`xoxb-...`) from OAuth & Permissions
   - App-Level Token (`xapp-...`) with `connections:write` from Basic Information

4. Copy `.env.example` to `.env` and fill in your credentials.

5. Run the app:
   ```bash
   python -m src.app
   ```

6. In Slack, invite the bot to the required channels: `#housing-referrals`, `#food-referrals`, `#transport-referrals`, `#utility-safety-referrals`, and `#leadership-dashboard`.

## Usage
- DM or open a Chat conversation with CareBridge AI to start a screening
- Use `/hrs-screen` to start a screening via slash command
- Use `/hrs-dashboard` to view the leadership summary

## Project Structure
- `config/`
  - [slack_manifest.yaml](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/config/slack_manifest.yaml): App manifest configurations for the Slack Agent Settings.
- `data/`
  - `completed_screenings.json`: Database file storing persistent completed/cancelled screening logs.
- `src/`
  - [app.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/src/app.py): Entry point initializing Bolt Socket Mode and starting the dashboard daemon thread.
  - [config.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/src/config.py): Configuration helper loading environment variables from `.env`.
  - [dashboard.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/src/dashboard.py): Storage database utilities and leadership summary digest calculations.
  - [referral_router.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/src/referral_router.py): Routes referral cards including agency names and conditional follow-up details.
  - [rule_engine.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/src/rule_engine.py): Scores responses against deterministic SDoH / HRSN rules.
  - [session_manager.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/src/session_manager.py): Session manager tracking clinical intakes and domain follow-up logic.
  - [slack_ai.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/src/slack_ai.py): Generates conversational summaries of screening outcomes.
  - [utils.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/src/utils.py): Common helper utilities.
  - `handlers/`
    - [actions.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/src/handlers/actions.py): Handles Block Kit interactive clicks for choice selections, follow-ups, and cancellations.
    - [commands.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/src/handlers/commands.py): Registers `/hrs-screen` and `/hrs-dashboard` slash commands.
    - [events.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/src/handlers/events.py): Listens to message events and handles active thread contexts.
- `tests/`
  - [test_assistant_thread.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/tests/test_assistant_thread.py): Asserts thread TS context persistence.
  - [test_dashboard.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/tests/test_dashboard.py): Asserts dashboard summary computations and storage.
  - [test_partner_and_followup.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/tests/test_partner_and_followup.py): Asserts per-domain conditional follow-ups and routing formats.
  - [test_referral_router.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/tests/test_referral_router.py): Asserts domain referral mapping correctness.
  - [test_rule_engine.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/tests/test_rule_engine.py): Asserts rule engine flagging accuracy.
  - [test_screening.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/tests/test_screening.py): Asserts core state machine transitions.
  - [test_slack_ai.py](file:///c:/Users/Puja%20Ahuja/Desktop/CareBridge-AI/tests/test_slack_ai.py): Asserts formatting of screening summaries.

## Note on Partner Agencies
Partner agency names referenced in referrals (e.g. Harborview Housing Alliance) are illustrative placeholders for this hackathon build. A production version would integrate with a real community resource directory.
