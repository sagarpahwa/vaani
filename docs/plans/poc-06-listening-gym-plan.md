# POC 06 — Listening Skill Gym — Implementation Plan

> **This file is the committed, resumable source of truth for POC 06.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at
[`poc-06-listening-gym-progress.md`](poc-06-listening-gym-progress.md)).
Do exactly this:

1. **Read this whole file** — understand the full design before touching code.
2. **Read the progress tracker:** [`docs/plans/poc-06-listening-gym-progress.md`](poc-06-listening-gym-progress.md)
   — find the **first sub-task whose status is not `DONE`**. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify* command).
   A session can die between writing code and committing — if the last `DONE` row isn't on disk,
   redo **only** that one step. **Never redo work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record commit SHA → **`git commit` the code and the progress tracker together** (branch
   `feat/poc-06-listening-gym`, conventional commit) → next row.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` · `DOING` · `DONE` (SHA recorded) · `DEFERRED` (blocker recorded).

---

## KEY CONSTRAINTS

- **Base branch:** `feat/poc-05-founder-oneonone`. Branch: `feat/poc-06-listening-gym`.
- **Not multi-turn.** This is a single prompt → single user response → analysis flow. It does NOT
  use the conversation engine from POC 04/05. It is architecturally closer to Mode B but with a
  specialized listening rubric. New route family: `/listening-scenarios`.
- **Keyword-based, deterministic scoring.** Five listening dimensions are scored by detecting
  presence/absence of marker patterns in the user's text response. No LLM, no STT (for the text
  path). The analysis is fully offline.
- **Optional audio input.** The frontend offers a mic button so users can respond by voice; the
  backend accepts optional `audio_base64` and transcribes via `PROVIDER_STT` (mock default).
  Scoring always operates on the text transcript — the audio path just fills the text field.
- **New domain module + new route.** `domain/listening.py` and `routes/listening.py` are new
  files. They follow the same patterns as existing domain/route modules.
- **Hard DB isolation.** Mock DB only: container `vaani_poc_mongo`, port **27018**, database
  `public_speaking_intelligence_mock`. Never touch the real DB / 27017.
- **Python env:** `.venv-poc` only. Never `.venv` / `.venv311`.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** branch `feat/poc-06-listening-gym`; conventional commits; never `git add -A`.

---

## Part A — Product design

### Concept

The app shows the user a complaint or concern statement (from a colleague, direct report, or
client). The user must respond as a good listener — summarizing what was said, acknowledging the
emotion, asking a clarifying question, and avoiding premature advice or blame. The app then scores
the response on 5 listening dimensions and shows evidence-grounded highlights plus a model response.

### User flow

```
home screen  →  Listening Gym card  →  listening-gym.tsx
    ↓
Display scenario prompt (text, optionally TTS read-aloud via expo-speech)
    ↓
User types response OR records via mic (optional audio)
    ↓
Tap "Analyze my response"
    ↓
POST /listening-scenarios/{id}/analyze  →  analysis JSON
    ↓
Show 5 dimension score cards + overall + model response
```

### Five listening dimensions

| Dimension | Key | What is detected |
|---|---|---|
| Summarization | `summarization` | User restates key words/phrases from the scenario |
| Emotional validation | `emotional_validation` | Empathy markers: "I hear", "I understand", "sounds frustrating", "that makes sense", "I can see why" |
| Clarifying question | `clarifying_question` | A question mark is present AND question-starter words ("what", "how", "can you", "could you", "tell me more", "which") |
| Avoided premature advice | `avoided_premature_advice` | Absence of advice markers: "you should", "you need to", "you must", "you have to", "the answer is", "just do" |
| Avoided blame | `avoided_blame` | Absence of blame markers: "your fault", "you always", "you never", "you didn't", "that was wrong of you" |

Score per dimension: 0.0 or 1.0 for binary markers; partial credit (0.0–1.0) for count-based
dimensions (summarization: fraction of scenario key-phrases restated; emotional_validation: at
least 1 marker = 1.0). Overall = weighted average (summarization 25%, emotional_validation 25%,
clarifying_question 20%, avoided_premature_advice 15%, avoided_blame 15%).

### Evidence highlights (returned per dimension)

Each dimension response includes a `highlight` string: a short sentence explaining what was found
(or not found). Examples:

- `summarization`: "You restated 'blocked' and 'no context' — good." / "No key phrases from the prompt were restated."
- `emotional_validation`: "Found: 'I can see why'." / "No empathy marker detected."
- `clarifying_question`: "Found: 'What specifically is blocking you?'" / "No clarifying question detected."
- `avoided_premature_advice`: "Clean — no premature advice found." / "Found: 'you should' — advice before understanding."
- `avoided_blame`: "Clean — no blame language." / "Found: 'you always' — avoid accusatory language."

### Model response

The API returns a `better_response` field: a single polished example response that would score
highly on all 5 dimensions. This is a static string baked into the scenario seed data.

### Five seed scenarios

| # | `scenario_id` | Source persona | Core complaint |
|---|---|---|---|
| 1 | `defensive_junior` | Junior engineer | Feels blockers are treated as excuses; no context or support given |
| 2 | `overloaded_pm` | Product manager | Too many stakeholders changing priorities; team is demoralized |
| 3 | `unhappy_client` | External client | Delayed delivery with no proactive communication |
| 4 | `peer_conflict` | Peer colleague | Feeling sidelined in key decisions; not consulted |
| 5 | `burned_out_lead` | Tech lead | Working nights/weekends; feels invisible; no recognition |

---

## Part B — Backend

### B.1 — Seed data

File: `services/api/db/seed_data/listening_scenarios.json`

Array of 5 scenario objects. Each has:

```
scenario_id       string   unique, lowercase_underscore
title             string
prompt            string   the complaint/concern text shown to the user
key_phrases       list     words/phrases from prompt used for summarization scoring
better_response   string   the model response shown after analysis
```

### B.2 — Domain: `services/api/domain/listening.py`

Pure functions, fully unit-testable (no DB, no IO).

```python
EMPATHY_MARKERS: list[str]          # "i hear", "i understand", "sounds frustrating", ...
QUESTION_STARTERS: list[str]        # "what", "how", "can you", "could you", "tell me more", ...
ADVICE_MARKERS: list[str]           # "you should", "you need to", "you must", ...
BLAME_MARKERS: list[str]            # "your fault", "you always", "you never", ...

def score_summarization(user_text: str, key_phrases: list[str]) -> tuple[float, str]:
    """Returns (score 0–1, highlight string). Score = matched/total key_phrases."""

def score_emotional_validation(user_text: str) -> tuple[float, str]:
    """Returns (1.0 if any empathy marker found, 0.0 otherwise, highlight string)."""

def score_clarifying_question(user_text: str) -> tuple[float, str]:
    """Returns (1.0 if question marker + '?' found, 0.0 otherwise, highlight string)."""

def score_avoided_premature_advice(user_text: str) -> tuple[float, str]:
    """Returns (0.0 if advice marker found, 1.0 otherwise, highlight string)."""

def score_avoided_blame(user_text: str) -> tuple[float, str]:
    """Returns (0.0 if blame marker found, 1.0 otherwise, highlight string)."""

def score_listening_response(
    user_text: str, scenario: dict
) -> dict:
    """
    Returns full analysis dict:
    {
      "scores": {
        "summarization": float,
        "emotional_validation": float,
        "clarifying_question": float,
        "avoided_premature_advice": float,
        "avoided_blame": float
      },
      "overall": float,    # weighted average
      "highlights": { dimension → highlight_string },
      "better_response": str
    }
    """
```

All marker matching is **case-insensitive**. Markers are matched as substrings (not whole words)
to stay simple. Compound phrases (e.g. "you should") are checked before single words.

### B.3 — Pydantic models (`services/api/models.py`)

Add:

```
ListeningScenarioSummary(scenario_id, title, prompt)
ListeningAnalysisRequest(user_text: str, audio_base64: str | None = None)
ListeningDimensionResult(score: float, highlight: str)
ListeningAnalysisResponse(
    scenario_id: str,
    scores: dict[str, ListeningDimensionResult],
    overall: float,
    better_response: str
)
```

### B.4 — Routes: `services/api/routes/listening.py`

```
GET  /listening-scenarios              → list[ListeningScenarioSummary]
GET  /listening-scenarios/{id}         → ListeningScenarioSummary (+ full prompt)
POST /listening-scenarios/{id}/analyze → ListeningAnalysisResponse
```

`POST /analyze` flow:
1. Load scenario from DB (404 if not found).
2. If `audio_base64` provided: decode → `STTProvider.transcribe()` → use transcript text.
3. If no audio: use `user_text` directly.
4. Call `score_listening_response(text, scenario)`.
5. Return `ListeningAnalysisResponse`.

Register router in `services/api/app.py`.

### B.5 — DB: seed + collection registration

Add `listening_scenarios` collection:
- Schema: `services/api/db/schemas/listening_scenarios.json` (`$jsonSchema` with required fields).
- Register in `COLLECTION_SPECS` in `services/api/db/init_mock_db.py` + add unique index on `scenario_id`.
- Add seed upsert in `services/api/db/seed_mock.py`.
- Add schema test case in `services/api/tests/test_schemas_poc.py`.

### B.6 — Tests

`services/api/tests/test_listening_domain.py` — unit tests for `domain/listening.py`:

- `test_score_summarization_all_matched` — all key_phrases present → score 1.0
- `test_score_summarization_none_matched` — no key_phrases restated → score 0.0
- `test_score_summarization_partial` — some key_phrases → fractional score
- `test_score_emotional_validation_found` — empathy marker → 1.0
- `test_score_emotional_validation_missing` — no marker → 0.0
- `test_score_clarifying_question_found` — question starter + "?" → 1.0
- `test_score_clarifying_question_no_question_mark` — question words but no "?" → 0.0
- `test_score_avoided_premature_advice_clean` — no advice markers → 1.0
- `test_score_avoided_premature_advice_found` — "you should" → 0.0
- `test_score_avoided_blame_clean` — no blame markers → 1.0
- `test_score_avoided_blame_found` — "you always" → 0.0
- `test_score_listening_response_full` — a well-formed response hits all 5 dimensions
- `test_score_listening_response_overall_weighted` — verify overall = weighted average formula

`services/api/tests/test_api_listening.py` — API tests (TestClient):

- `GET /listening-scenarios` returns 5 items
- `GET /listening-scenarios/defensive_junior` returns 200 with prompt
- `GET /listening-scenarios/nonexistent` returns 404
- `POST /listening-scenarios/defensive_junior/analyze` with good text → 200 + all 5 dimensions
- `POST /listening-scenarios/defensive_junior/analyze` with empty text → all scores deterministic

---

## Part C — Frontend

### C.1 — `listening-gym.tsx`

New screen at `app/src/app/listening-gym.tsx`. Layout:

1. **Scenario selector** (5 radio/tab choices, by `title`). Default: first scenario.
2. **Scenario prompt card** — displays the complaint/concern text. Optional TTS read-aloud button
   (expo-speech, behind `readAloud` feature flag).
3. **Response input** — multi-line text input for typing + optional mic button (behind `liveProgress`
   flag or a new `audioInput` flag). Mic state mirrors the recorder component from Mode B.
4. **"Analyze my response" button** — disabled until response is non-empty (or recording complete);
   shows loading spinner while request is in-flight.
5. **Results panel** (revealed after analysis):
   - Overall score bar (color-coded: ≥0.8 green, 0.5–0.8 amber, <0.5 red).
   - 5 dimension score cards (score + highlight text).
   - "Better response" card with model text.
   - "Try again" button to reset and respond again.

Reuse: `Screen`, `Button`, `Card`, `ScoreBar`, `Banner` from `app/src/ui/`.

### C.2 — Route registration

Register `/listening-gym` in `app/src/app/_layout.tsx` — `Stack.Screen title="Listening Skill Gym"`.

### C.3 — Home screen card

Add card in `app/src/app/index.tsx`:

```
Title: "Listening Skill Gym"
Badge: "LISTENING"
Subtitle: "Hear a complaint, respond, and get scored on 5 listening dimensions."
CTA: → /listening-gym
```

### C.4 — API client methods

Add to `app/src/api/client.ts`:

```typescript
listListeningScenarios(): Promise<ListeningScenarioSummary[]>
analyzeListeningResponse(scenarioId: string, payload: ListeningAnalysisRequest): Promise<ListeningAnalysisResponse>
```

Add matching types to `app/src/api/types.ts`:
`ListeningScenarioSummary`, `ListeningAnalysisRequest`, `ListeningDimensionResult`,
`ListeningAnalysisResponse`.

### C.5 — Tests

- `app/src/app/listening-gym.test.tsx` — renders scenario selector; Analyze button disabled on
  empty input; calls `analyzeListeningResponse` with correct payload; renders 5 dimension cards
  after analysis; renders "Better response" card; "Try again" resets results.
- Client test additions: `listListeningScenarios` returns typed list; `analyzeListeningResponse`
  sends correct body.

---

## Part D — Acceptance criteria

1. User can open the Listening Skill Gym from the home screen.
2. The screen shows a complaint/concern text from one of 5 scenarios.
3. User can type a response (and optionally record audio).
4. After tapping "Analyze", the screen shows 5 listening dimension scores with specific highlight
   evidence strings, an overall score, and a model "better response".
5. The scoring is deterministic and works with no LLM, no cloud credentials, no running STT service
   (text-only path).
6. `make poc-api-test` green (≥70% coverage, all domain + API tests pass, including new
   `listening_scenarios` schema test).
7. `make poc-app-test` green (lint + typecheck + jest, including `listening-gym.test.tsx`).

---

## Decisions & notes

- **Single-response, not multi-turn.** This is a deliberate simplification. The listening skill is
  judged on the quality of a single response — adding turns would obscure the specific coaching
  signal.
- **Text-first scoring.** Keyword detection on text is fully offline and deterministic. Audio input
  is optional enrichment (the STT transcribes it, then the same text scorer runs). This keeps CI
  clean and avoids any STT dependency for the core feature.
- **Binary dimensions with exceptions.** `avoided_premature_advice` and `avoided_blame` are inverse
  scores (presence of bad markers = 0.0). `summarization` gives partial credit. This asymmetry
  makes the coaching signal sharper — "you were clean on blame" is a clear positive.
- **5 scenarios is enough for a demo.** Each covers a distinct workplace archetype. Expanding the
  scenario bank is purely additive (new seed data, no code change).
- **`better_response` is static.** It is baked into the seed JSON. A real LLM-generated ideal
  response is a future iteration; for the POC the static example demonstrates the concept.
- **No new DB collection schema risk.** The `listening_scenarios` collection is isolated in the
  mock DB. If the feature is cut, the collection is benign.
