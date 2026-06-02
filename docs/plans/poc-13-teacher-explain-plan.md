# POC 13 — Teacher Explainer Mode — Implementation Plan & Progress Tracker

> **This file is the committed, resumable source of truth for POC 13.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## ▶ HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file). Do exactly this:

1. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
2. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify*
   command). A session can die between writing code and committing, so the last row marked
   `DONE` might not be on disk. If it didn't land, redo **only** that one step. **Never redo
   work already `DONE` and verified.**
3. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-13-teacher-explain`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit.
4. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in CLAUDE.md)

- **Base branch:** `feat/poc-12-ted-story`. New branch: `feat/poc-13-teacher-explain` (branch off base, never commit to base).
- **No LLM.** All scoring is deterministic marker/heuristic logic in Python. No cloud credentials required.
- **Additive, zero regression.** Existing Mode A/B/persona/storytelling paths and their golden fixtures stay byte-for-byte identical. `make poc-api-test` must pass with the same golden values after every commit.
- **Python env:** `.venv-poc` only (via `make poc-api-install`). Never `.venv` / `.venv311`.
- **DB isolation.** Mock DB only: container `vaani_poc_mongo`, port **27018**, database `public_speaking_intelligence_mock`. Never touch port 27017 or the real DB.
- **POC schemas isolated.** New schema → `services/api/db/schemas/` (NOT shared `schemas/`).
- **Audio never in Mongo.** ObjectStore abstraction only.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test` after every commit.
- **Git identity:** conventional commits; never `git add -A`; never force-push without explicit request.

---

## P0 — Docs & resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | This plan/tracker file → `docs/plans/poc-13-teacher-explain-plan.md` | TODO | | `test -f docs/plans/poc-13-teacher-explain-plan.md` |
| P0.2 | Link this milestone in `docs/plans/poc-implementation-progress.md` (add POC 13 row to Milestone Status table) | TODO | | `grep "poc-13" docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend domain: explainer scorer

*Checkpoint:* `from services.api.domain.explainer import score_explanation` works; 10+ unit tests green.

The scorer is **pure Python** — no DB, no audio, no LLM. It receives the full explanation text and a `concept_id` (to look up the concept-specific jargon list), and returns a dict with five sub-scores plus improvement suggestions.

**Concepts and jargon lists (matched case-insensitively as whole-word or substring):**
- `ai_agents`: jargon = `["neural", "embedding", "inference", "gradient", "backprop", "transformer", "llm", "token", "latent"]`
- `compound_interest`: jargon = `["apr", "compounding rate", "annualized", "yield", "basis point", "amortization"]`
- `electric_vehicles`: jargon = `["kilowatt-hour", "kwh", "regenerative braking", "torque curve", "inverter", "bms", "range anxiety"]`
- `machine_learning`: jargon = `["overfitting", "gradient descent", "hyperparameter", "epoch", "loss function", "regularization", "feature vector"]`
- `inflation`: jargon = `["cpi", "monetary policy", "quantitative easing", "aggregate demand", "velocity of money", "purchasing power parity"]`

**Scoring dimensions:**

1. `simplicity_score` — computed from the explanation text (ignoring any detected jargon words):
   - avg syllables per word (estimate: vowel-group count per word): < 1.6 → 1.0; > 2.4 → 0.0; linearly interpolated.
   - avg words per sentence: < 12 → 1.0; > 22 → 0.0; linearly interpolated.
   - `simplicity_score = (syllable_score + sentence_score) / 2`

2. `analogy_score` — presence of analogy markers: `"like a"`, `"similar to"`, `"imagine if"`, `"think of it as"`, `"it is like"`, `"just like"`, `"kind of like"`, `"you know how"`, `"picture this"`. Score = min(1.0, count / 2) — two distinct analogies = full score.

3. `stepwise_score` — presence of sequencing markers: `"first"`, `"second"`, `"third"`, `"then"`, `"next"`, `"finally"`, `"step 1"`, `"step 2"`, `"step 3"`, `"to start"`, `"to begin"`, `"after that"`. Score = min(1.0, count / 3) — three sequencing words = full score.

4. `jargon_score` — inverse: `jargon_score = max(0.0, 1.0 - jargon_count * 0.25)`. Zero jargon = 1.0; four or more jargon terms = 0.0. The detected jargon words are returned as `jargon_found: list[str]` for frontend display.

5. `check_score` — presence of check-for-understanding markers: `"does that make sense"`, `"with me so far"`, `"got it"`, `"any questions"`, `"so far so good"`, `"make sense?"`, `"follow me?"`, `"are you with me"`. Score = min(1.0, count / 1) — any one = full score.

**Derived outputs:**
- `overall_score` — weighted: simplicity 0.30, analogy 0.25, stepwise 0.20, jargon_free 0.15, check 0.10.
- `jargon_found` — list of jargon words detected.
- `simpler_analogy_suggestion` — if `analogy_score < 0.5`: concept-specific canned suggestion (e.g. for AI agents: "Try: 'Think of it like a team of assistants, each handling one job'"); else `None`.
- `simpler_version_note` — if `jargon_count > 0`: "Replace [jargon_found] with simpler words your audience already knows"; else `None`.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `services/api/domain/explainer.py` — `CONCEPT_JARGON: dict[str, list[str]]` constant (5 concepts); `score_explanation(text: str, concept_id: str) -> dict` implementing all 5 dimensions plus `jargon_found`, `simpler_analogy_suggestion`, `simpler_version_note`, `overall_score` | TODO | | `python3 -c "from services.api.domain.explainer import score_explanation; r=score_explanation('Think of it like a helper. First it reads. Then it acts.','ai_agents'); assert 'overall_score' in r"` |
| P1.2 | `services/api/tests/test_explainer.py` — 10+ unit tests: simplicity low-syllable vs high-syllable; analogy present vs absent; stepwise present vs absent; jargon-free vs jargon-heavy (check jargon_found list); check_for_understanding present vs absent; unknown concept_id handled gracefully (empty jargon list); overall_score in [0,1]; simpler_analogy_suggestion returned when analogy low | TODO | | `pytest services/api/tests/test_explainer.py -v` → 10+ passed |
| P1.3 | `make poc-api-lint && make poc-api-test` green after P1 | TODO | | `make poc-api-lint && make poc-api-test` → 0 errors, coverage ≥70% |

---

## P2 — Backend API: explainer routes + seed data

*Checkpoint:* `GET /explain-concepts` returns 5 concepts; `POST /explain-concepts/{id}/analyze` returns all 5 dimension scores.

**Seed data — `services/api/db/seed_data/explain_concepts.json` (5 concepts):**
```
[
  { "concept_id": "ai_agents",         "title": "AI Agents",
    "description": "Explain how AI agents work and what makes them useful.",
    "target_audience": "12-year-old" },
  { "concept_id": "compound_interest", "title": "Compound Interest",
    "description": "Explain how money grows over time with compound interest.",
    "target_audience": "12-year-old" },
  { "concept_id": "electric_vehicles", "title": "Electric Vehicles",
    "description": "Explain how electric cars work differently from petrol cars.",
    "target_audience": "12-year-old" },
  { "concept_id": "machine_learning",  "title": "Machine Learning",
    "description": "Explain what machine learning is and why it matters.",
    "target_audience": "12-year-old" },
  { "concept_id": "inflation",         "title": "Inflation",
    "description": "Explain what inflation is and how it affects everyday life.",
    "target_audience": "12-year-old" }
]
```

Pydantic models:
- `ExplainConcept` — `concept_id`, `title`, `description`, `target_audience`
- `ExplainAnalysisRequest` — `text: str`
- `ExplainAnalysisResponse` — `concept_id`, `simplicity_score`, `analogy_score`, `stepwise_score`, `jargon_score`, `check_score`, `jargon_found`, `overall_score`, `simpler_analogy_suggestion`, `simpler_version_note`

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `services/api/db/seed_data/explain_concepts.json` — 5 concepts with fields above | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/seed_data/explain_concepts.json')); assert len(d)==5"` |
| P2.2 | `services/api/routes/explainer.py` — `GET /explain-concepts` (list), `POST /explain-concepts/{id}/analyze` (validates concept_id, calls `score_explanation`, returns response) | TODO | | `curl -s http://localhost:8090/explain-concepts \| python3 -c "import sys,json;d=json.load(sys.stdin);assert len(d)==5"` |
| P2.3 | Register explainer router in `services/api/app.py` | TODO | | `grep explainer services/api/app.py` |
| P2.4 | Add `ExplainConcept`, `ExplainAnalysisRequest`, `ExplainAnalysisResponse` to `services/api/models.py` | TODO | | `python3 -c "from services.api.models import ExplainAnalysisResponse"` |
| P2.5 | `services/api/tests/test_api_explainer.py` — 4+ API tests: list concepts (5 items), analyze valid text (all 5 score fields present, overall in [0,1]), invalid concept_id → 404, empty text → valid response (low scores) | TODO | | `pytest services/api/tests/test_api_explainer.py -v` → 4+ passed |
| P2.6 | `make poc-api-lint && make poc-api-test` green after P2 | TODO | | `make poc-api-lint && make poc-api-test` → 0 errors, coverage ≥70% |

---

## P3 — Frontend: `teacher-explain.tsx` screen

*Checkpoint:* browser shows a concept picker grid; user selects a concept, types explanation, submits; results show 5 score cards + jargon list + suggestion.

**Screen layout — two views within one route (`/teacher-explain`):**

**View 1: Concept picker (shown on mount)**
- Header: "Explain Like I'm 12" + back arrow.
- Subtitle: "Pick a complex topic. Explain it simply."
- Grid of 5 concept cards (2-column grid on web): each card shows title + target_audience badge. Tapping navigates to View 2.

**View 2: Explanation input (shown after concept selected)**
- Header: selected concept title.
- Target audience badge: "Audience: 12-year-old".
- Concept description in a subdued box.
- Large multiline `TextInput` ("Explain this in your own words…").
- Character hint: "Aim for 100+ words for meaningful feedback".
- Submit button: "Analyse My Explanation" (disabled if text < 30 chars).
- Back link to concept picker.
- Results section (shown after submit):
  - 5 score cards in a 2-column grid: Simplicity, Analogy, Stepwise, Jargon-Free, Check-In — each with a score bar + label (e.g. "Jargon-Free: 60%").
  - If `jargon_found` non-empty: a warning strip "Watch out for: [jargon words as chips]".
  - Overall score badge.
  - Suggestions: "Try a simpler analogy: …" (if `simpler_analogy_suggestion` set) and/or "Replace jargon: …" (if `simpler_version_note` set).

**Route integration:**
- Register `teacher-explain` in `app/src/app/_layout.tsx`.
- Add home card: "Explain Like I'm 12" with subtitle "Simplicity, analogies, step-by-step clarity".

**API wiring:**
- Add `listExplainConcepts()`, `analyzeExplanation(conceptId, text)` to `app/src/api/client.ts`.
- Add `ExplainConcept`, `ExplainAnalysisResponse` to `app/src/api/types.ts`.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Add `ExplainConcept`, `ExplainAnalysisResponse` to `app/src/api/types.ts` | TODO | | `grep ExplainAnalysisResponse app/src/api/types.ts` |
| P3.2 | Add `listExplainConcepts()`, `analyzeExplanation(conceptId, text)` to `app/src/api/client.ts` + tests in `client.test.ts` | TODO | | `make poc-app-test` green; client test covers both new methods |
| P3.3 | `app/src/app/teacher-explain.tsx` — concept picker grid + explanation input + results with 5 score cards + jargon chip strip + suggestions | TODO | | screen file exists; no TypeScript errors |
| P3.4 | Register `/teacher-explain` route in `app/src/app/_layout.tsx` (Stack.Screen title "Explain Like I'm 12") | TODO | | `grep "teacher-explain" app/src/app/_layout.tsx` |
| P3.5 | Add "Explain Like I'm 12" home card to `app/src/app/index.tsx` → navigates to `/teacher-explain` | TODO | | `grep "teacher-explain" app/src/app/index.tsx` |
| P3.6 | Co-located test `app/src/app/teacher-explain.test.ts` — submit disabled < 30 chars, score card rendering from mock response, jargon chip list renders correctly | TODO | | `make poc-app-test` green (new test cases counted) |
| P3.7 | `make poc-app-test` green after all P3 | TODO | | `make poc-app-test` → lint + typecheck + jest all pass |

---

## P4 — End-to-end verify

*Checkpoint:* explanation text for "AI Agents" submitted via API → all 5 dimension scores returned, jargon correctly detected.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Backend E2E: `POST /explain-concepts/ai_agents/analyze` with a jargon-heavy text → `jargon_score < 0.5` and `jargon_found` non-empty; with a jargon-free + analogy text → `jargon_score > 0.75` and `analogy_score > 0` | TODO | | `curl -s -X POST http://localhost:8090/explain-concepts/ai_agents/analyze -H 'Content-Type: application/json' -d '{"text":"Think of it like a helper. First it reads the task. Then it acts. Does that make sense?"}' \| python3 -c "import sys,json;d=json.load(sys.stdin);assert d['analogy_score']>0 and d['check_score']>0"` |
| P4.2 | Full `make poc-api-test` + `make poc-app-test` green | TODO | | `make poc-api-test && make poc-app-test` |
| P4.3 | Update `docs/plans/poc-implementation-progress.md` to mark POC 13 `DONE` | TODO | | `grep "POC 13\|poc-13" docs/plans/poc-implementation-progress.md` |

---

## Decisions & notes

- **Text-first, no audio in the primary path.** Same rationale as POC 12 — keeps the POC verifiable without a microphone while the scoring logic is the genuine deliverable.
- **No new MongoDB collection.** Concepts served from a static JSON file at startup — no schema migration required.
- **Jargon lists are per-concept, not per-word-globally.** This prevents false positives: "neural" is jargon in an AI explanation but not in a biology one.
- **`unknown_concept_id`** → `score_explanation` uses `CONCEPT_JARGON.get(concept_id, [])` — returns empty jargon list, all other scores still computed. The route returns 404 if the concept_id is not in the seed JSON.
- **`simpler_version_note`** is a canned template, not a generated rewrite. A real LLM rewrite is an Iteration 2 upgrade. The POC surfaces the principle (jargon identified → actionable note) without requiring inference.
- **Existing golden fixtures stay byte-identical.** `explainer.py` is a new module with no imports from the coaching pipeline.
