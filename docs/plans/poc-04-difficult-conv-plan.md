# POC 04 — Difficult Conversation Coach — Implementation Plan

> **This file is the approved design and resumable tracker for POC 04.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## ▶ HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file). Do exactly this:

1. **Branch:** `feat/poc-04-difficult-conv` (off `feat/poc-01-audio-lab`). Run:
   ```bash
   git checkout feat/poc-01-audio-lab && git checkout -b feat/poc-04-difficult-conv
   ```
   If `feat/poc-01-audio-lab` is not yet merged, base off it directly. If it has been merged into
   `feat/poc-coaching-app`, base off that instead.
2. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify* command /
   confirm the file exists). A session can die between writing code and committing, so the last row
   marked `DONE` might not be on disk. If it didn't land, redo **only** that one step. **Never redo
   work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` + record
   the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-04-difficult-conv`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit. A crash then costs at most one in-flight step.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed file
   is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed;
SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in CLAUDE.md)

- **No LLM required.** The persona's responses are driven by a deterministic `StateEngine` — a
  state machine keyed on keyword markers in the user's text. The mock is the CI default and the
  POC demo default. A real `ConversationEngine` (LLM-backed) is pluggable later via `PROVIDER_*`.
- **New mode, no regression.** Mode A / Mode B / Persona sessions are completely untouched. The
  `conversation_sessions` and `conversation_turns` collections are new — they never affect existing
  collection schemas, routes, or tests.
- **Hard DB isolation.** All new schemas go in `services/api/db/schemas/` (NOT shared `schemas/`).
  `init_mock_db.py` gets two new entries in `COLLECTION_SPECS`. `assert_mock_target` guard must
  still prevent running against port 27017.
- **New schemas: two collections only.** `conversation_sessions` and `conversation_turns`. Scenario
  data lives in `seed_data/conversation_scenarios.json` and is seeded into `conversation_sessions`
  indirectly — actually scenarios are a separate seed table. See P2 for details.
- **Audio is optional per turn.** Each turn accepts `text` (required) and `audio_base64` (optional,
  for a future "speak your turn" mode). The MVP is text-only.
- **Telemetry is best-effort.** New events: `conversation_started`, `conversation_turn`,
  `conversation_completed`. They follow the existing pattern in `telemetry.py` — write attempt
  swallowed on failure, never blocks the API response.
- **Python env:** `.venv-poc` only. Never `.venv` / `.venv311`.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test`
  must stay green at every commit.
- **Git identity:** branch `feat/poc-04-difficult-conv`; conventional commits; never `git add -A`,
  never force-push / `reset --hard` without explicit ask.

---

## Purpose

This POC introduces the **conversation mode** — a multi-turn interactive roleplay where the app
plays a defensive junior employee and the user (as manager) practices handling a difficult
conversation. After 6 turns (or ≥4 if the user ends early), the app scores 6 interpersonal
dimensions and shows what the user could have said differently.

The conversation mode proves Vaani can coach interpersonal communication, not just public speaking.
The `StateEngine` and scoring logic built here are reusable by POC 05, 06, 07, and 15.

---

## Architecture overview

```
Frontend (Expo)                     Backend (FastAPI)
  /conversation-setup    ────────▶  POST /conversations
  /conversation          ────────▶  POST /conversations/{id}/turns
  /conversation-review   ────────▶  GET  /conversations/{id}/review

New backend files:
  domain/conversation.py            StateEngine + scorer + review builder
  providers/base.py                 ConversationEngine ABC (added)
  providers/mock_conversation.py    Deterministic StateEngine impl
  routes/conversations.py           3 endpoints above
  db/schemas/conversation_sessions.json
  db/schemas/conversation_turns.json
  db/seed_data/conversation_scenarios.json
```

---

## API contract

### POST /conversations
```
Body: { "user_id": "demo-user", "scenario_id": "defensive_junior_ownership" }
Response 201:
{
  "session_id": "conv-...",
  "scenario_title": "Defensive Junior Employee",
  "scenario_brief": "You are a manager. Your team member repeatedly deflects ...",
  "persona_opening": "Honestly, I feel like I am the only one being blamed here ..."
}
```

### POST /conversations/{id}/turns
```
Body: { "text": "I hear that you feel ...", "audio_base64": null }
Response 200:
{
  "persona_response": "I mean, I get that it is hard, but ...",
  "turn_index": 1,
  "session_complete": false
}
-- session_complete becomes true when turn_index >= MAX_TURNS (6) or user ends early
```

### GET /conversations/{id}/review
```
Response 200:
{
  "session_id": "conv-...",
  "turn_count": 6,
  "overall_score": 0.71,
  "capability_scores": {
    "listening":      0.80,
    "empathy":        0.65,
    "firmness":       0.60,
    "clarity":        0.75,
    "de_escalation":  0.70,
    "next_step":      0.55
  },
  "strengths": ["Asked a clarifying question", "Acknowledged their feelings"],
  "issues": [
    {
      "title": "Assigned blame",
      "evidence": "\"You need to be more proactive\" — this reads as accusatory",
      "better_line": "\"What would help you feel more supported on this?\" — invites a solution"
    }
  ],
  "retry_drill": "Try starting your next message with an empathy opener"
}
```

---

## StateEngine: deterministic persona turns

The `StateEngine` in `domain/conversation.py` drives the persona response for each turn index
based on marker detection in the user's cumulative messages.

**Marker sets (baked into `conversation.py` as module-level constants):**
```python
EMPATHY_MARKERS   = {"understand", "hear", "feel", "appreciate", "sounds", "must be"}
BLAME_MARKERS     = {"your fault", "you need to", "should have", "irresponsible", "blame"}
QUESTION_MARKERS  = {"?", "what", "how", "why", "can you", "could you", "would you"}
NEXT_STEP_MARKERS = {"let's", "we could", "action", "plan", "next", "by when", "agree"}
```

**Turn scripts (scenario `defensive_junior_ownership`):**

| Turn | Condition | Persona response |
|---|---|---|
| 0 (opening) | — | "Honestly, I feel like I am the only one being blamed here. Other teams never respond on time." |
| 1 | empathy detected | "I mean, I get that it is hard, but I still need support from other teams to make progress." |
| 1 | no empathy | "But what am I supposed to do if they do not give me context?" |
| 2 | blame detected | "So you are saying this is all my fault?" |
| 2 | no blame | "I have already tried following up. Nobody listens." |
| 3 | question detected | "Well, the backend API has not been updated in three weeks and nobody told me about the change." |
| 3 | no question | "Fine, but I need someone senior to escalate this." |
| 4 | empathy_score ≥ 2 turns | "I suppose I could try a different approach, but I am not sure it will work." |
| 4 | empathy_score < 2 | "Okay, but if this goes wrong it is not on me." |
| 5 (closing) | — | "Okay, I can try that, but I do not want to be blamed again if things go wrong." |

`empathy_score` = count of prior user turns where `EMPATHY_MARKERS` detected ≥1 word.

**Scoring (pure function `score_conversation` in `domain/conversation.py`):**

| Dimension | Weight | How scored |
|---|---|---|
| `listening` | 25% | question_markers detected across turns / total_turns |
| `empathy` | 20% | empathy_score / total_turns |
| `firmness` | 15% | turns with `next_step_markers` / total_turns |
| `clarity` | 15% | avg word count per turn ∈ [10, 40] → 1.0; outside → proportional penalty |
| `de_escalation` | 15% | (total_turns − blame_turns) / total_turns |
| `next_step` | 10% | next_step_markers in last 2 turns |

`overall_score` = weighted sum of the six dimensions.

---

## Data model

### `conversation_sessions`
```json
{
  "session_id":    "conv-<uuid>",
  "user_id":       "demo-user",
  "scenario_id":   "defensive_junior_ownership",
  "status":        "active | completed",
  "turn_count":    6,
  "scores":        { "listening": 0.8, ... },
  "overall_score": 0.71,
  "created_at":    "...",
  "updated_at":    "...",
  "schema_version":"1.0"
}
```

### `conversation_turns`
```json
{
  "turn_id":                "turn-<uuid>",
  "session_id":             "conv-...",
  "turn_index":             2,
  "speaker":                "user | persona",
  "text":                   "...",
  "empathy_markers_detected":  true,
  "blame_markers_detected":    false,
  "question_markers_detected": true,
  "created_at":             "...",
  "schema_version":         "1.0"
}
```

### `conversation_scenarios` (seed-only, no schema validation — plain seed document)
Seeded into a lightweight `conversation_scenarios` collection (no JSON Schema validator — just a
plain collection holding the scenario docs). `init_mock_db.py` creates it; `seed_mock.py` seeds it.

```json
{
  "scenario_id":    "defensive_junior_ownership",
  "title":          "Defensive Junior Employee",
  "brief":          "You are a manager. Your team member repeatedly deflects responsibility ...",
  "persona_role":   "defensive junior employee",
  "user_role":      "manager",
  "opening_message": "Honestly, I feel like I am the only one being blamed here ...",
  "max_turns":      6,
  "min_turns":      4,
  "rubric_weights": { "listening": 0.25, "empathy": 0.20, "firmness": 0.15,
                      "clarity": 0.15, "de_escalation": 0.15, "next_step": 0.10 },
  "goals": ["acknowledge emotion", "clarify blocker", "identify controllable action", "agree next step"]
}
```

---

## P0 — Docs + branch setup

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | This plan file at `docs/plans/poc-04-difficult-conv-plan.md` | TODO | | `test -f docs/plans/poc-04-difficult-conv-plan.md` |
| P0.2 | Link this milestone in `docs/plans/poc-implementation-progress.md` (new row for POC 04) | TODO | | `grep "poc-04-difficult-conv" docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend domain: `domain/conversation.py`

*Checkpoint:* state machine, scorer, and review builder are pure functions, fully unit-tested.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `EMPATHY_MARKERS`, `BLAME_MARKERS`, `QUESTION_MARKERS`, `NEXT_STEP_MARKERS` constants + `detect_markers(text, marker_set) -> bool` helper in `services/api/domain/conversation.py` | TODO | | `pytest services/api/tests/test_conversation_domain.py::test_markers` green |
| P1.2 | `ConversationTurn` dataclass (turn_id, session_id, turn_index, speaker, text, empathy/blame/question/next_step detected booleans) and `ConversationSession` dataclass (session_id, scenario_id, user_id, status, turns list) in `domain/conversation.py` | TODO | | `grep "ConversationTurn" services/api/domain/conversation.py` |
| P1.3 | `StateEngine` class with `next_turn(scenario_data: dict, history: list[ConversationTurn], user_text: str) -> str` — implement the 6 turn scripts + branching from the table above | TODO | | `pytest services/api/tests/test_conversation_domain.py::test_state_engine_empathy_branch` green |
| P1.4 | `score_conversation(turns: list[ConversationTurn], rubric_weights: dict) -> dict` pure function — returns the 6 dimension scores + `overall_score` per the scoring table above | TODO | | `pytest services/api/tests/test_conversation_domain.py::test_score_conversation` green |
| P1.5 | `build_conversation_review(session_id, turns, scores) -> dict` — assembles the full review payload (strengths list, issues list with evidence + better_line, retry_drill string); strengths: detected empathy→"Acknowledged their feelings", question→"Asked a clarifying question", next_step→"Proposed a concrete next step"; issues: blame_turns→evidence+better_line; retry_drill keyed on lowest scoring dimension | TODO | | `pytest services/api/tests/test_conversation_domain.py::test_build_review` green |
| P1.6 | Full `services/api/tests/test_conversation_domain.py` with ≥10 tests covering: marker detection (empathy/blame/question), state engine empathy branch, state engine blame branch, question reveal branch, turn 4 cooperation split, score_conversation happy path, score_conversation all-blame, review strengths, review issues, review retry_drill | TODO | | `pytest services/api/tests/test_conversation_domain.py` ≥10 passed |
| P1.7 | `make poc-api-lint` clean after P1 additions | TODO | | `make poc-api-lint` exits 0 |

---

## P2 — Backend DB + seed data

*Checkpoint:* two new schemas valid; `init_mock_db.py` creates 3 new collections; seed populates scenario.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `services/api/db/schemas/conversation_sessions.json` — `$jsonSchema` with required fields: session_id, user_id, scenario_id, status (enum: active/completed), schema_version | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/schemas/conversation_sessions.json')); assert '\$jsonSchema' in d"` |
| P2.2 | `services/api/db/schemas/conversation_turns.json` — `$jsonSchema` with required fields: turn_id, session_id, turn_index, speaker (enum: user/persona), text, schema_version | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/schemas/conversation_turns.json')); assert '\$jsonSchema' in d"` |
| P2.3 | `services/api/db/seed_data/conversation_scenarios.json` — one scenario document: `defensive_junior_ownership` with title, brief, persona_role, user_role, opening_message, max_turns, min_turns, rubric_weights, goals, and turn_scripts array (6 entries with condition/response pairs) | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/seed_data/conversation_scenarios.json')); assert d[0]['scenario_id']=='defensive_junior_ownership'"` |
| P2.4 | Register `conversation_sessions`, `conversation_turns`, and `conversation_scenarios` in `COLLECTION_SPECS` in `services/api/db/init_mock_db.py`; add indexes: `conversation_sessions` on `session_id` (unique), `status`; `conversation_turns` on `session_id`, `turn_id` (unique); `conversation_scenarios` on `scenario_id` (unique) | TODO | | `grep "conversation_sessions" services/api/db/init_mock_db.py` |
| P2.5 | Seed `conversation_scenarios` in `services/api/db/seed_mock.py` (upsert by `scenario_id`); idempotent | TODO | | init + seed on mongomock → 1 scenario; re-seed inserts 0 |
| P2.6 | Add 3 test cases to `services/api/tests/test_schemas_poc.py` for `conversation_sessions.json`, `conversation_turns.json` (check `$jsonSchema`, required list, enum values); update expected schema file count | TODO | | `pytest services/api/tests/test_schemas_poc.py` green |
| P2.7 | `make poc-api-test` green after P2 — no regression | TODO | | `make poc-api-test` green |

---

## P3 — Backend API: routes + provider wiring + telemetry

*Checkpoint:* all 3 conversation endpoints reachable via TestClient; mock engine drives branching.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Add `ConversationEngine` ABC to `services/api/providers/base.py` — method `next_turn(scenario_data: dict, history: list, user_text: str) -> str`; add `conversation_engine: ConversationEngine` to `ProviderBundle` | TODO | | `grep "ConversationEngine" services/api/providers/base.py` |
| P3.2 | `services/api/providers/mock_conversation.py` — `MockConversationEngine` wraps `StateEngine` from `domain/conversation.py`; deterministic, no external deps | TODO | | `python3 -c "from services.api.providers.mock_conversation import MockConversationEngine; print('ok')"` from `.venv-poc` |
| P3.3 | Wire `ConversationEngine` in `services/api/providers/registry.py`: add `_build_conversation` (mock default; raise `ValueError` on unknown name); add `provider_conversation = "mock"` to `services/api/config.py` | TODO | | `grep "provider_conversation" services/api/config.py services/api/providers/registry.py` |
| P3.4 | Add repo helpers to `services/api/repository.py`: `create_conversation_session`, `get_conversation_session`, `save_conversation_turn`, `list_conversation_turns`, `update_conversation_session_scores` | TODO | | `grep "create_conversation_session" services/api/repository.py` |
| P3.5 | Pydantic models in `services/api/models.py`: `CreateConversationRequest`, `ConversationStartResponse`, `SubmitTurnRequest`, `SubmitTurnResponse`, `ConversationReviewResponse` (with `capability_scores`, `strengths`, `issues`, `retry_drill`) | TODO | | `grep "CreateConversationRequest" services/api/models.py` |
| P3.6 | `services/api/routes/conversations.py` — implement `POST /conversations`, `POST /conversations/{id}/turns`, `GET /conversations/{id}/review`; call `StateEngine` for persona response; call `score_conversation` and `build_conversation_review` on review; save all turns + session to DB | TODO | | `grep "APIRouter" services/api/routes/conversations.py` |
| P3.7 | Mount conversations router in `services/api/app.py` under prefix `/api/conversations`; confirm in `/openapi.json` | TODO | | `grep "conversations" services/api/app.py` |
| P3.8 | Add `conversation_started`, `conversation_turn`, `conversation_completed` event emitters to `services/api/telemetry.py` (best-effort pattern, same as existing emitters) | TODO | | `grep "conversation_started" services/api/telemetry.py` |
| P3.9 | `services/api/tests/test_api_conversations.py` — TestClient tests: (a) POST /conversations creates session + returns opening; (b) POST /turns empathy branch → softer response; (c) POST /turns blame branch → harder response; (d) question branch → reveals context; (e) session_complete when turn_count reaches max_turns; (f) GET /review after 6 turns → scores + strengths + issues; (g) 404 on unknown session_id | TODO | | `pytest services/api/tests/test_api_conversations.py` ≥7 passed |
| P3.10 | `make poc-api-lint && make poc-api-test` green; coverage ≥70%; no regression on Mode A/B/Persona | TODO | | `make poc-api-lint && make poc-api-test` both exit 0 |

---

## P4 — Frontend types + API client

*Checkpoint:* new types compile clean; client functions tested.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Add to `app/src/api/types.ts`: `ConversationScenario`, `ConversationStartResponse`, `SubmitTurnResponse`, `ConversationCapabilityScores`, `ConversationIssue`, `ConversationReviewResponse` | TODO | | `grep "ConversationScenario" app/src/api/types.ts` |
| P4.2 | Add to `app/src/api/client.ts`: `createConversation(userId, scenarioId)`, `submitTurn(sessionId, text, audioBase64?)`, `getConversationReview(sessionId)` | TODO | | `grep "createConversation" app/src/api/client.ts` |
| P4.3 | `app/src/api/__tests__/conversation.test.ts` — test `createConversation` calls correct endpoint; `submitTurn` passes `turn_index`; `getConversationReview` returns typed response; `ApiError` thrown on 404 | TODO | | `make poc-app-test` green; grep test file exists |

---

## P5 — Frontend screens

*Checkpoint:* full click-through (home → setup → chat → end → review).

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P5.1 | `app/src/app/conversation-setup.tsx` — scenario brief, persona role label, user role label, "Start conversation" button (calls `createConversation` → navigates to `/conversation?sessionId=...&opening=...`) | TODO | | `test -f app/src/app/conversation-setup.tsx` |
| P5.2 | `app/src/app/conversation.tsx` — chat UI: (a) opening persona message at top, (b) alternating message bubbles (user = right/accent, persona = left/muted), (c) `TextInput` + "Send" button per turn, (d) optional mic record button (behind `flags.liveProgress` or similar gate — text-first for MVP), (e) loading indicator while waiting for persona response, (f) "End session" button visible after `min_turns` reached, (g) navigates to `/conversation-review?sessionId=...` on completion | TODO | | `test -f app/src/app/conversation.tsx` |
| P5.3 | `app/src/app/conversation-review.tsx` — post-session review: overall score headline, 6 `ScoreBar` capability rows (reuse existing `ScoreBar` component), strengths list, issues list (each with title/evidence/better_line), retry_drill tip, "Try again" button back to `/conversation-setup` | TODO | | `test -f app/src/app/conversation-review.tsx` |
| P5.4 | Register all 3 conversation routes in `app/src/app/_layout.tsx` (`Stack.Screen` titles: "Difficult Conversation", "Practice Conversation", "Conversation Review") | TODO | | `grep "conversation-setup" app/src/app/_layout.tsx` |
| P5.5 | Add "Handle a difficult conversation" card to `app/src/app/index.tsx` — links to `/conversation-setup`; place below the metrics-lab card (or personas card if metrics-lab not merged yet) | TODO | | `grep "conversation-setup" app/src/app/index.tsx` |
| P5.6 | Co-located component tests: `app/src/app/__tests__/conversation-review.test.tsx` — render `ConversationReviewResponse` mock data, assert 6 ScoreBar rows render, assert strengths/issues list items render, assert overall score visible | TODO | | `make poc-app-test` green; jest output shows conversation-review tests |
| P5.7 | `make poc-app-test` (lint + typecheck + jest) green — no regression | TODO | | `make poc-app-test` exits 0 |

---

## P6 — E2E verify (web browser walkthrough)

*Checkpoint:* 6-turn conversation flows end-to-end; review screen shows scores.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P6.1 | Start backend (`make poc-db-up && make poc-db-setup && make poc-api-run`) and frontend (`make poc-app-web`). Confirm both healthy | TODO | | `curl http://localhost:8090/health` → 200; web app at :8081 |
| P6.2 | Navigate to `/conversation-setup` from home card. Confirm scenario brief, persona role, user role displayed. Click "Start conversation" | TODO | | conversation-setup screen renders; button enabled |
| P6.3 | Send a turn with empathy marker (e.g. "I hear that you feel frustrated"). Confirm persona responds with the softer empathy-branch message, not the blame-branch message | TODO | | persona response matches empathy branch script |
| P6.4 | Send a turn with a question (e.g. "What would help you feel unblocked?"). Confirm persona reveals the backend API blocker context (turn 3 question branch) | TODO | | persona reveals context on question turn |
| P6.5 | Complete 6 turns. Confirm "End session" appears after turn 4 and navigates to `/conversation-review` | TODO | | review screen loads with 6 capability ScoreBars |
| P6.6 | Review screen: confirm overall score, all 6 capability rows, at least 1 strength, at least 1 issue with evidence + better_line, retry_drill tip | TODO | | review screen fully populated |
| P6.7 | Confirm no console errors; existing home screen cards (Mode A, personas, metrics-lab) still present | TODO | | browser console clean; home cards intact |
| P6.8 | Final: `make poc-api-test && make poc-app-test` green on committed state | TODO | | both exit 0 |

---

## Acceptance criteria

- [ ] User can start a "Difficult Conversation" from the home screen.
- [ ] Persona opens with the scripted opening message.
- [ ] Persona becomes measurably more cooperative when user uses empathy markers.
- [ ] Persona becomes more defensive when user uses blame markers.
- [ ] Persona reveals blocker context when user asks a question.
- [ ] "End session" button appears after ≥4 turns.
- [ ] Review shows: overall score, 6 capability scores (listening/empathy/firmness/clarity/
  de_escalation/next_step), at least 1 strength, at least 1 issue with evidence + better_line.
- [ ] `make poc-api-test` green (coverage ≥70%).
- [ ] `make poc-app-test` green (lint + typecheck + jest).
- [ ] No regression on existing Mode A / Mode B / Persona session tests.
- [ ] All new schemas pass `test_schemas_poc.py`.
- [ ] No LLM or cloud credential required to run the full flow.

---

## Decisions & open notes

- **StateEngine is pure and in `domain/`.** It takes `scenario_data` (a plain dict loaded from
  `conversation_scenarios.json`) and `history` (list of `ConversationTurn`), so it is fully
  unit-testable with no DB dependency. The provider wrapper `MockConversationEngine` is just a thin
  shim that loads scenario data and delegates to `StateEngine`.
- **`ConversationEngine` ABC is minimal.** One method: `next_turn(scenario_data, history, user_text)
  → str`. An LLM-backed impl would inject a prompt template and call the LLM API. The ABC lives in
  `providers/base.py` alongside the other ABCs (STTProvider, Scorer, etc.).
- **Three new DB collections, not two.** `conversation_scenarios` is technically a third collection
  needed to store scenario definitions. It has no `$jsonSchema` validator (it's reference/seed data,
  not user-generated), so it is a plain collection. The two validated collections are
  `conversation_sessions` and `conversation_turns`.
- **`better_line` generation in `build_conversation_review`.** For the POC, better_line strings are
  static per blame turn (keyed on the turn's text pattern). An LLM-backed impl would generate them
  dynamically. The static versions are sufficient to make the review screen meaningful.
- **No retry/fork on conversation sessions.** Unlike the coaching path, conversation sessions are
  not retried by forking a child session — the user clicks "Try again" to start a fresh session
  (new session_id). The retry_drill string in the review is a plain coaching tip, not a session
  fork.
- **Text-first MVP, audio optional.** The chat screen has a `TextInput` as the primary input. A
  mic button (behind a feature flag) is a UI placeholder for a future "speak your turn" mode where
  the user's audio is transcribed before being sent as a turn. No STT runs in POC 04.
- **`min_turns = 4`, `max_turns = 6`.** After the user submits turn 4, the "End session" button
  appears. After turn 6, the session auto-completes and navigates to review. These constants come
  from `conversation_scenarios.json` (configurable per scenario for future flexibility).
- **Telemetry event design:** `conversation_turn` emits after every successful turn (includes
  `turn_index`, `speaker`, `empathy/blame/question` booleans for analytics). `conversation_completed`
  includes `turn_count` and `overall_score`. Events follow the existing best-effort pattern in
  `telemetry.py` — never block the response.
- **Reusable engine seam.** The `StateEngine` class in `domain/conversation.py` is the shared
  contract that POC 05/06/07/15 will extend with different scenario files and possibly different
  branching logic. The scenario JSON format (with `turn_scripts`, `rubric_weights`, `goals`) is
  designed to be scenario-agnostic from day one.
- **Android:** same constraint as prior POCs — no SDK in this env, emulator run deferred. The chat
  screen uses only cross-platform RN primitives (`View`, `TextInput`, `FlatList`, `Pressable`).
  Android compat is verified at code level via the platform-aware config in `config.ts`.
