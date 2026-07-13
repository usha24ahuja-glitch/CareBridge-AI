# Development Log: CareBridge AI

This file documents critical milestones, iterations, design pivots, and release statuses during the development of CareBridge AI.

---

## [2026-07-10] Project Initialization

### 📅 Activities
- Set up project structure on the Desktop.
- Wrote foundational documents:
  - `Project_Overview.md`
  - `Architecture.md`
  - `Workflow.md`
  - `API_Notes.md`
  - `Future_Improvements.md`
- Created system prompt skeletons in the `prompts/` folder.
- Generated mock data sets inside `data/` folder.
- Defined Python dependency manifest (`requirements.txt`).

### 📌 Decision Log
- **Multi-turn vs Modal screening**: Opted to structure the primary screening flow as a multi-turn chat sequence rather than a long single-form modal. Conversational turn-taking feels more interactive, works better for recording text replies, and allows step-by-step guidance.
- **Mock database**: Standard JSON files will serve as the initial database to keep deployment light and isolated for the Slack Agent Challenge, with Pydantic validating schema consistency.

---

## [2026-07-10] Guided HRSN Screening Conversation

### 📅 Activities
- Created the core `SessionManager` state machine in `src/session_manager.py`.
- Formulated the full 7-step guided questionnaire in Slack Block Kit (Section, Context, and Action elements).
- Structured the DM flow redirection for channel invocations to preserve patient SDoH privacy.
- Enabled message button cleanups (editing original button blocks into text selection states) to prevent out-of-order repeats.
- Added comprehensive unit tests in `tests/test_screening.py` asserting session states, response tracking, and block structure rendering.

### 📌 Decision Log
- **In-Memory Sessions**: Decided to run sessions in-memory for the conversational engine, mapping states by `user_id`. This keeps the bot responsive and clean, discarding the session once it completes.
- **Button choice lock-ins**: Configured handlers to replace Block Kit action elements with text (e.g. `Selected: Yes`) in-place immediately after user input. This locks in choices and keeps chat scrolls readable.
- **Privacy Redirection**: Configured `/hrs-screen` to detect channel type. If executed in a public channel, it redirects the workflow into a private DM with the bot, posting an ephemeral privacy warning message.

