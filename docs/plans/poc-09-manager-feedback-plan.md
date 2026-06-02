# POC 09 — Manager Feedback Coach — Implementation Plan

> **This file is the committed, resumable source of truth for POC 09.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

1. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
2. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify*
   command / confirm the file exists). A session can die between writing code and committing,
   so the last row marked `DONE` might not be on disk. If it didn't land, redo **only** that
   one step. **Never redo work already `DONE` and verified.**
3. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-09-manager-feedback`, conventional commit) → next row. Never batch multiple
   sub-tasks into one commit.
4. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative**.

**Base branch:** `feat/poc-08-interview`
**Working branch:** `feat/poc-09-manager-feedback`

**Status legend:** `TODO` · `DOING` · `DONE` (SHA recorded) · `DEFERRED` (blocker recorded)

---

## KEY CONSTRAINTS

- **Hard DB isolation:** POC only — container `vaani_poc_mongo`, port **27018**, DB
  `public_speaking_intelligence_mock`. Never touch the real DB / port 27017.
- **Python env:** `.venv-poc` only. Never `.venv` / `.venv311`.
- **New dedicated endpoint, not a session.** The feedback coach does not use
  `POST /sessions` / `POST /sessions/{id}/utterances`. It exposes its own
  `GET /feedback-coach/scenarios` and `POST /feedback-coach/scenarios/{id}/analyze`
  routes so it stays decoupled from the coached-speech pipeline.
- **No LLM required.** SBI component detection and tone classification are purely
  keyword/phrase-based. The "better script" is a deterministic template fill, not
  generated text.
- **Additive, zero regression.** Existing Mode A/B/persona pipelines and golden fixtures
  are completely untouched.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and
  `make poc-app-test` after every sub-task commit.
- **POC schemas isolated:** any new schema in `services/api/db/schemas/` only.
- **Frontend is text-input only (no audio recording).** The user types (or pastes) what
  they would say to the employee. Audio recording is out of scope for this POC.
- **Git identity:** conventional commits; never `git add -A`.

---

## What to build

The user is shown an employee scenario (e.g. "An employee missed two back-to-back deadlines").
They type what they would actually say to that employee. The app checks their response against
the **SBI + Empathy + Expectation + Support** feedback framework:

- **S** — Situation: did they ground the feedback in a specific moment?
- **B** — Behavior: did they name the observable behavior (not the person)?
- **I** — Impact: did they state the impact on the team/project?
- **E** — Empathy: did they acknowledge the employee's perspective?
- **Ex** — Expectation: did they state what they expect going forward?
- **Su** — Support: did they offer help or resources?

The app also classifies the **tone**: too soft (hedge phrases), balanced, or too harsh
(absolutes, judgment words). It shows a "better script" that hits all six components in
a balanced tone.

### Architecture

- `services/api/domain/feedback_coach.py` — pure domain module: marker lists for each of the
  6 SBI-E-Ex-Su components, tone classifier, `score_feedback_response(text)` function that
  returns `FeedbackCoachResult` (6 boolean/float component scores + `tone_label` + `better_script`).
- `services/api/db/seed_data/feedback_scenarios.json` — 2 scenarios with `scenario_id`,
  `employee_situation` description, `context_detail`, and a `better_script` template.
- `services/api/routes/feedback_coach.py` — two routes registered into `app.py`.
- `app/src/app/manager-feedback.tsx` — screen with scenario text, text area, submit button,
  and result cards showing each SBI-E-Ex-Su component with a check/cross, tone badge, and
  the better script.

---

## P0 — Docs + branch scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | This plan file → `docs/plans/poc-09-manager-feedback-plan.md` | TODO | | `test -f docs/plans/poc-09-manager-feedback-plan.md` |
| P0.2 | Progress tracker → `docs/plans/poc-09-manager-feedback-progress.md` (all TODO) | TODO | | `test -f docs/plans/poc-09-manager-feedback-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-09 docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend domain: SBI-E-Ex-Su scorer + tone classifier

*Checkpoint:* `score_feedback_response(text)` returns correct component flags and tone label
for a set of contrived inputs; 12+ unit test cases pass.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | Create `services/api/domain/feedback_coach.py` — define `FeedbackCoachResult` dataclass (fields: `situation_present`, `behavior_present`, `impact_present`, `empathy_present`, `expectation_present`, `support_present`, `tone_label: str`, `component_count: int`, `better_script: str`) | TODO | | `python3 -c "from services.api.domain.feedback_coach import FeedbackCoachResult"` |
| P1.2 | Implement component marker lists in `feedback_coach.py`: `SITUATION_MARKERS` (`"last week"`, `"on monday"`, `"during"`, `"when you"`, `"in the meeting"`), `BEHAVIOR_MARKERS` (`"the report was"`, `"you submitted"`, `"the deadline"`, `"was not delivered"`, `"missed"`), `IMPACT_MARKERS` (`"the team"`, `"caused"`, `"delayed"`, `"affected"`, `"client"`, `"project"`), `EMPATHY_MARKERS` (`"i understand"`, `"i know"`, `"it sounds"`, `"that must"`, `"i appreciate"`), `EXPECTATION_MARKERS` (`"going forward"`, `"next time"`, `"i expect"`, `"i need"`, `"by"` + date-hint), `SUPPORT_MARKERS` (`"how can i help"`, `"what do you need"`, `"i can"`, `"let's"`, `"support"`) | TODO | | `grep SITUATION_MARKERS services/api/domain/feedback_coach.py` |
| P1.3 | Implement `TOO_SOFT_MARKERS` (`"i wonder if"`, `"maybe you could"`, `"it might be"`, `"perhaps"`, `"if you don't mind"`) and `TOO_HARSH_MARKERS` (`"always"`, `"never"`, `"unacceptable"`, `"disappointing"`, `"you failed"`, `"ridiculous"`) in `feedback_coach.py`; tone classifier: ≥2 soft markers and 0 harsh = `"too_soft"`, ≥1 harsh marker = `"too_harsh"`, else `"balanced"` | TODO | | unit test: `score_feedback_response("maybe you could perhaps consider")["tone_label"] == "too_soft"` |
| P1.4 | Implement `score_feedback_response(text: str, scenario_id: str) -> FeedbackCoachResult` — lowercase + detect each component via substring match on marker lists; compute `component_count`; look up `better_script` from in-module scenario templates keyed by `scenario_id` | TODO | | import works; function callable with sample text |
| P1.5 | Unit tests `services/api/tests/test_feedback_coach.py` — 12+ cases: (a) all 6 components present → `component_count==6`; (b) situation missing; (c) impact missing; (d) empathy missing; (e) too-soft tone; (f) too-harsh tone; (g) balanced tone; (h) better_script is non-empty string; (i) empty input → 0 components; (j) case-insensitive detection; (k) expectation marker detected; (l) support marker detected | TODO | | `pytest services/api/tests/test_feedback_coach.py` → ≥12 passed |
| P1.6 | `make poc-api-lint && make poc-api-test` green | TODO | | `make poc-api-lint && make poc-api-test` |

---

## P2 — Backend API: scenarios seed + routes

*Checkpoint:* `GET /feedback-coach/scenarios` returns 2 scenarios;
`POST /feedback-coach/scenarios/missed-deadlines/analyze` with sample text returns 200 with
all 6 component keys and `tone_label`.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | Create `services/api/db/seed_data/feedback_scenarios.json` — 2 scenarios: `missed-deadlines` (employee missed back-to-back deadlines) and `attitude-problem` (employee showed dismissive attitude in team meetings); each has `scenario_id`, `title`, `employee_situation` (3-4 sentences of context), `context_detail` (what the manager knows), `better_script` (a ~100-word example hitting all 6 components in a balanced tone) | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/seed_data/feedback_scenarios.json')); assert len(d)==2"` |
| P2.2 | Create `services/api/routes/feedback_coach.py` — `GET /feedback-coach/scenarios` (returns list of scenario summaries); `POST /feedback-coach/scenarios/{scenario_id}/analyze` (body: `{ "user_text": "..." }`, response: `FeedbackCoachResult` dict + HTTP 404 on unknown `scenario_id`) | TODO | | `grep "feedback-coach" services/api/routes/feedback_coach.py` |
| P2.3 | Register `feedback_coach` router in `services/api/app.py` with prefix `/feedback-coach` | TODO | | `grep feedback_coach services/api/app.py` |
| P2.4 | API tests `services/api/tests/test_api_feedback_coach.py` — (a) GET /scenarios → 200, list length 2; (b) POST analyze with SBI-complete text → all 6 components True; (c) POST analyze with hedge text → `tone_label=="too_soft"`; (d) POST analyze with harsh text → `tone_label=="too_harsh"`; (e) POST unknown scenario_id → 404; (f) POST empty user_text → 0 components, `component_count==0` | TODO | | `pytest services/api/tests/test_api_feedback_coach.py` → ≥6 passed |
| P2.5 | `make poc-api-lint && make poc-api-test` green (coverage ≥70%) | TODO | | `make poc-api-lint && make poc-api-test` |

---

## P3 — Frontend: manager-feedback screen + route + home card

*Checkpoint:* Home → "Manager Feedback Coach" → scenario shown → user types → submit →
results display 6 component cards (check/cross), tone badge, and better script.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Add `FeedbackScenario`, `FeedbackCoachResult`, `listFeedbackScenarios`, `analyzeFeedback` to `app/src/api/types.ts` and `app/src/api/client.ts` | TODO | | `make poc-app-test` green (typecheck) |
| P3.2 | Create `app/src/app/manager-feedback.tsx` — on mount: `listFeedbackScenarios()` → pick first scenario (expandable post-POC); show scenario `employee_situation` text; render a multi-line text input (`TextInput multiline`); "Analyze" button (disabled when input empty); on submit: call `analyzeFeedback(scenarioId, userText)` → show results | TODO | | `make poc-app-test` green (typecheck + lint) |
| P3.3 | Results section in `manager-feedback.tsx`: 6 `Card` components (one per SBI-E-Ex-Su component), each showing component label + ✓ or ✗ based on the boolean field; tone badge (label: "too soft" / "balanced" / "too harsh", colour coded with theme tokens — `warning` for soft/harsh, `success` for balanced); `component_count` summary line; collapsible "Better Script" card showing `better_script` text | TODO | | `make poc-app-test` green |
| P3.4 | Register `/manager-feedback` route in `app/src/app/_layout.tsx` with title "Manager Feedback Coach" | TODO | | `grep manager-feedback app/src/app/_layout.tsx` |
| P3.5 | Add "Manager Feedback Coach" card to `app/src/app/index.tsx` home — badge "SBI FRAMEWORK", links to `/manager-feedback` | TODO | | `make poc-app-test` green |
| P3.6 | `make poc-app-test` fully green (lint + typecheck + all jest) | TODO | | `make poc-app-test` |

---

## P4 — E2E verify

*Checkpoint:* end-to-end flow works; both test suites green.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Backend smoke: `GET /feedback-coach/scenarios` → 200, 2 items; `POST /feedback-coach/scenarios/missed-deadlines/analyze` with an SBI-complete body → `component_count==6`, `tone_label=="balanced"` | TODO | | curl or `pytest -k feedback_coach -m integration` |
| P4.2 | `make poc-api-test` fully green (no golden regressions for Mode A/B/persona) | TODO | | `make poc-api-test` |
| P4.3 | `make poc-app-test` fully green | TODO | | `make poc-app-test` |
| P4.4 | Manual / Claude Preview: Home → "Manager Feedback Coach" → "missed-deadlines" scenario shown → type a hedging response → submit → tone badge shows "too soft" → 3–4 components missing (✗) → better script visible | TODO | | visual confirmation |

---

## Decisions & notes

- **No `practice_sessions` involvement.** The manager feedback coach is a stateless
  analyze-on-demand endpoint. There is nothing to retry, no per-line recording, no Goal
  Signature. If a session concept is needed post-POC it can be layered on later.
- **Better script is seed data, not generated.** Each `feedback_scenarios.json` entry
  carries a pre-authored `better_script`. This keeps the POC offline and deterministic.
  Post-POC: swap in an LLM prompt to tailor the better script to the user's actual words.
- **Two scenarios seed data.** `missed-deadlines` and `attitude-problem` cover the two
  most common managerial feedback scenarios. More can be added by appending to the JSON.
- **SBI detection is substring / lowercased.** Precision is deliberately low for a POC.
  Post-POC: add phrase-length weighting and negation detection ("I don't think there was
  any impact" should not count as `impact_present`).
- **Tone classification uses a count threshold.** ≥2 soft markers triggers "too_soft";
  a single harsh marker triggers "too_harsh". Rationale: one hedge is normal; two or more
  signals over-softening. Any harsh word is immediately actionable.
- **No new MongoDB collection.** Scenarios are loaded from seed JSON in memory by the
  route handler. If scenario persistence is needed (user history, analytics) that is a
  separate post-POC collection.
