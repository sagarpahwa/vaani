# POC 06 — Listening Skill Gym — Implementation Progress Tracker

> **This file is the committed, resumable source of truth for POC 06.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at
[`poc-06-listening-gym-plan.md`](poc-06-listening-gym-plan.md)). Do exactly this:

1. **Read the plan:** [`docs/plans/poc-06-listening-gym-plan.md`](poc-06-listening-gym-plan.md)
   — the full approved design (Parts A–D, acceptance criteria). This tracker is its checklist.
2. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify* command /
   confirm the file exists). A session can die between writing code and committing, so the last row
   marked `DONE` might not be on disk. If it didn't land, redo **only** that one step.
   **Never redo work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-06-listening-gym`, conventional commit) → next row. Never batch multiple
   sub-tasks into one commit.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in the plan & CLAUDE.md)

- **Base branch:** `feat/poc-05-founder-oneonone`. Branch: `feat/poc-06-listening-gym`.
- **Single-response flow.** No multi-turn conversation engine. New route family `/listening-scenarios`.
- **Keyword-based scoring.** Pure text analysis — 5 marker lists, fully offline, deterministic.
- **New domain module + route.** `domain/listening.py` + `routes/listening.py` — both new files.
- **New collection.** `listening_scenarios` in mock DB only; schema in `services/api/db/schemas/`.
- **Hard DB isolation.** Mock DB only: container `vaani_poc_mongo`, port **27018**, database
  `public_speaking_intelligence_mock`. Never touch the real DB / 27017.
- **Python env:** `.venv-poc` only (via `make poc-api-install`). Never `.venv` / `.venv311`.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** branch `feat/poc-06-listening-gym`; conventional commits; never `git add -A`,
  never force-push / `reset --hard` without explicit ask.

---

## P0 — Docs & resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of full plan → [`poc-06-listening-gym-plan.md`](poc-06-listening-gym-plan.md) | TODO | | `test -f docs/plans/poc-06-listening-gym-plan.md` |
| P0.2 | This resumable tracker → `poc-06-listening-gym-progress.md` | TODO | | `test -f docs/plans/poc-06-listening-gym-progress.md` |
| P0.3 | Link this milestone from [`poc-implementation-progress.md`](poc-implementation-progress.md) | TODO | | `grep "poc-06" docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend domain: `domain/listening.py`

*Checkpoint:* all 13 unit tests in `test_listening_domain.py` pass.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `services/api/domain/listening.py` — define marker lists: `EMPATHY_MARKERS`, `QUESTION_STARTERS`, `ADVICE_MARKERS`, `BLAME_MARKERS` | TODO | | `python3 -c "from services.api.domain.listening import EMPATHY_MARKERS; assert len(EMPATHY_MARKERS) >= 5"` |
| P1.2 | `score_summarization(user_text, key_phrases)` — case-insensitive substring match; returns `(float, highlight_str)`; score = matched/total, 1.0 if key_phrases empty | TODO | | unit test: all matched → 1.0; none matched → 0.0 |
| P1.3 | `score_emotional_validation(user_text)` — first matching marker found → `(1.0, "Found: '...'")`, none → `(0.0, "No empathy marker detected.")` | TODO | | unit test: "I hear you" → 1.0; "sure" → 0.0 |
| P1.4 | `score_clarifying_question(user_text)` — question starter present AND "?" present → 1.0; either missing → 0.0 | TODO | | unit test: "What do you mean?" → 1.0; "What do you mean" (no "?") → 0.0 |
| P1.5 | `score_avoided_premature_advice(user_text)` — advice marker found → `(0.0, "Found: '...'"`); absent → `(1.0, "Clean...")` | TODO | | unit test: "you should" → 0.0; "let me understand first" → 1.0 |
| P1.6 | `score_avoided_blame(user_text)` — blame marker found → 0.0; absent → 1.0 | TODO | | unit test: "you always" → 0.0; "this has been hard" → 1.0 |
| P1.7 | `score_listening_response(user_text, scenario)` — calls all 5 scorers; computes weighted overall (25/25/20/15/15); returns full analysis dict with `scores`, `overall`, `highlights`, `better_response` | TODO | | unit test: well-formed response → all 5 scores present; overall = weighted formula |
| P1.8 | `services/api/tests/test_listening_domain.py` — 13 test cases covering all scorer functions + overall weighted formula | TODO | | `pytest services/api/tests/test_listening_domain.py` → 13 passed |

---

## P2 — Backend API: route + seed + collection

*Checkpoint:* `GET /listening-scenarios` returns 5 items; `POST /{id}/analyze` returns full analysis.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `services/api/db/seed_data/listening_scenarios.json` — 5 scenarios (defensive_junior, overloaded_pm, unhappy_client, peer_conflict, burned_out_lead): each with `scenario_id`, `title`, `prompt`, `key_phrases` list, `better_response` | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/seed_data/listening_scenarios.json')); assert len(d)==5"` |
| P2.2 | `services/api/db/schemas/listening_scenarios.json` — `$jsonSchema` validator with required fields (`scenario_id`, `title`, `prompt`, `key_phrases`, `better_response`, `created_at`, `updated_at`, `schema_version`) | TODO | | `python3 -c "import json; s=json.load(open('services/api/db/schemas/listening_scenarios.json')); assert '\$jsonSchema' in s"` |
| P2.3 | Register `listening_scenarios` in `COLLECTION_SPECS` in `services/api/db/init_mock_db.py`; add unique index on `scenario_id` | TODO | | `grep listening_scenarios services/api/db/init_mock_db.py` |
| P2.4 | Add upsert for `listening_scenarios` in `services/api/db/seed_mock.py` | TODO | | `grep listening_scenarios services/api/db/seed_mock.py` |
| P2.5 | Add `ListeningScenarioSummary`, `ListeningAnalysisRequest`, `ListeningDimensionResult`, `ListeningAnalysisResponse` Pydantic models to `services/api/models.py` | TODO | | `grep ListeningAnalysisResponse services/api/models.py` |
| P2.6 | `services/api/routes/listening.py` — `GET /listening-scenarios`, `GET /listening-scenarios/{id}`, `POST /listening-scenarios/{id}/analyze` (text path + optional audio → STT → score) | TODO | | `test -f services/api/routes/listening.py` |
| P2.7 | Register listening router in `services/api/app.py` | TODO | | `grep listening services/api/app.py` |
| P2.8 | Schema test case for `listening_scenarios` in `services/api/tests/test_schemas_poc.py` | TODO | | `pytest services/api/tests/test_schemas_poc.py` |
| P2.9 | `services/api/tests/test_api_listening.py` — 5 API test cases (list returns 5, get by id, 404, analyze good text, analyze empty text) | TODO | | `pytest services/api/tests/test_api_listening.py` → 5 passed |

---

## P3 — Frontend: `listening-gym.tsx` + home card

*Checkpoint:* Screen renders; user can select a scenario, type a response, and see 5 score cards.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | `app/src/api/types.ts` — add `ListeningScenarioSummary`, `ListeningAnalysisRequest`, `ListeningDimensionResult`, `ListeningAnalysisResponse` types | TODO | | `grep ListeningAnalysisResponse app/src/api/types.ts` |
| P3.2 | `app/src/api/client.ts` — add `listListeningScenarios()` and `analyzeListeningResponse(scenarioId, payload)` methods | TODO | | `grep listListeningScenarios app/src/api/client.ts` |
| P3.3 | `app/src/app/listening-gym.tsx` — scenario selector, prompt card, text input, "Analyze" button (disabled until non-empty input), loading state, results panel (5 dimension cards + overall + better_response + Try again) | TODO | | `test -f app/src/app/listening-gym.tsx` |
| P3.4 | Register `/listening-gym` route in `app/src/app/_layout.tsx` — `Stack.Screen title="Listening Skill Gym"` | TODO | | `grep listening-gym app/src/app/_layout.tsx` |
| P3.5 | Add home card in `app/src/app/index.tsx` — "Listening Skill Gym", badge "LISTENING", CTA → `/listening-gym` | TODO | | `grep listening-gym app/src/app/index.tsx` |
| P3.6 | `app/src/app/listening-gym.test.tsx` — 6 test cases: renders selector, Analyze disabled on empty input, calls `analyzeListeningResponse` with correct payload, renders 5 dimension cards on success, renders better_response card, Try Again resets | TODO | | `make poc-app-test` |

---

## P4 — E2E verify

*Checkpoint:* Full browser flow from home → scenario → type response → 5 score cards visible.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Start backend (`make poc-api-run`) and web app (`make poc-app-web`); navigate home → "Listening Skill Gym" card | TODO | | Browser shows listening-gym screen |
| P4.2 | Select `defensive_junior` scenario — verify prompt text renders | TODO | | Complaint prompt displayed |
| P4.3 | Type a response that includes empathy marker + clarifying question + no advice → Analyze → verify emotional_validation = 1.0 and clarifying_question = 1.0 | TODO | | Score cards show ≥2 green dimensions |
| P4.4 | Type a response with "you should" → Analyze → verify `avoided_premature_advice` = 0.0 and highlight cites "you should" | TODO | | Score card shows 0.0 for advice dimension with evidence |
| P4.5 | Verify "Better response" card renders with the static model text from seed | TODO | | Better response visible on screen |

---

## P5 — Tests polish & CI green

*Checkpoint:* Both test suites green with no coverage regression.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P5.1 | `make poc-api-lint` clean (ruff + black) | TODO | | `make poc-api-lint` exits 0 |
| P5.2 | `make poc-api-test` green — all domain + API + schema tests pass; coverage ≥70% | TODO | | `make poc-api-test` exits 0 |
| P5.3 | `make poc-app-test` green — lint + typecheck + jest (including `listening-gym.test.tsx`) | TODO | | `make poc-app-test` exits 0 |
| P5.4 | Update `docs/plans/poc-implementation-progress.md` — add POC 06 row to Milestone Status table | TODO | | `grep "POC 06" docs/plans/poc-implementation-progress.md` |
| P5.5 | Update CLAUDE.md — add `listening_scenarios` to POC Data Model table; add `domain/listening.py` and `routes/listening.py` to backend tree | TODO | | `grep listening_scenarios CLAUDE.md` |

---

## Decisions & open notes (carry across sessions)

- **Marker lists are baked into `domain/listening.py`, not seed data.** They are pure Python
  constants — testable, versionable in git, no DB roundtrip. The scenario seed carries `key_phrases`
  (specific to each prompt) but the generic empathy/advice/blame/question markers are domain-level.
- **Case-insensitive substring matching.** Normalise both the user text and the marker to lowercase
  before checking. This catches "I Hear you", "YOU SHOULD", etc. without regex complexity.
- **`score_summarization` gives partial credit.** A user who restates 2 of 4 key phrases gets 0.5.
  All other dimensions are binary to keep feedback sharp.
- **Optional audio path.** If `audio_base64` is provided, the STT provider transcribes it and the
  text scorer runs on the transcript. The mock STT is the default (no real STT needed for the demo).
- **`better_response` is static in seed.** A future iteration can replace it with an LLM-generated
  ideal. For now, a hand-crafted example per scenario is sufficient and avoids any model dependency.
- **`listening_scenarios` collection sits in the mock DB only.** It follows the same isolation
  rules as all other POC collections: schema in `services/api/db/schemas/`, never in shared
  `schemas/`; seeded via `seed_mock.py`; init via `init_mock_db.py`.
