# POC 17 — Filler Word Detox — Implementation Plan

> **This file is the committed, resumable source of truth for POC 17.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at the progress tracker).
Do exactly this:

1. **Read the companion progress tracker** `poc-17-filler-detox-progress.md` — find the
   **first sub-task whose status is not `DONE`** in the tables there. That is where you resume.
2. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify* command /
   confirm the file exists). A session can die between writing code and committing.
3. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` + record
   the commit SHA → **`git commit` the code and the progress tracker together** → next row.
4. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but the **committed
   progress tracker is authoritative**.

**Status legend:** `TODO` · `DOING` · `DONE` (SHA recorded) · `DEFERRED` (blocker recorded)

---

## KEY CONSTRAINTS (never violate — full rules in CLAUDE.md)

- **Base branch:** `feat/poc-16-emotion-lab` → new branch `feat/poc-17-filler-detox`
- **No LLM required.** All filler analysis is rule-based (regex/word-matching). The endpoint
  works fully offline with no cloud credentials.
- **FILLER_WORDS already exists** in `services/api/providers/base.py`. The new domain module
  imports it from there rather than redefining it.
- **Additive, zero regression.** Mode A/B + persona golden fixtures stay byte-identical.
  The new `filler_detox` routes and domain module are entirely separate from the coaching pipeline.
- **Hard DB isolation.** Mock DB only: port **27018**, database
  `public_speaking_intelligence_mock`. Never touch port 27017.
- **New prompts seed data** goes in `services/api/db/seed_data/filler_prompts.json` and is loaded
  by `seed_mock.py`. If a `filler_prompts` collection is needed it uses a new schema file in
  `services/api/db/schemas/` (NOT shared `schemas/`).
- **Python env:** `.venv-poc` only. **Keep green:** `make poc-api-lint && make poc-api-test`
  (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** personal SSH host `github.com-personal` / username `sagarpahwa`.

---

## Purpose

User selects a random speaking prompt (e.g. "Describe your morning routine") and speaks for about
60 seconds. The app counts filler words, shows filler count per minute, highlights the top 3
repeated fillers, sets a retry challenge (reduce by 50%), and provides replacement phrase
suggestions. The whole flow works without any LLM — pure word-matching on the transcript text.

**Why this is nearly free to build:** `providers/analysis.py` already computes `filler_count` and
the `FILLER_WORDS` list is defined in `providers/base.py`. This POC adds a thin domain module to
produce a richer per-filler breakdown plus replacement suggestions, a dedicated API route, a seed
file of prompts, and a frontend screen.

---

## Architecture notes

- **New domain module:** `services/api/domain/filler.py` — pure functions, no I/O.
  `analyze_fillers(text: str, filler_words: list[str] | None = None) → FillerReport`
  where `FillerReport` is a dataclass with:
  - `total_fillers: int`
  - `per_filler: dict[str, int]` — counts keyed by filler word
  - `filler_per_min: float` — assumes caller passes `duration_seconds`; computed as
    `total_fillers / (duration_seconds / 60)` if duration given, else from word-count heuristic
    (avg speaking rate 130 wpm → duration ≈ word_count / 130 * 60)
  - `top_fillers: list[str]` — top 3 by count
  - `filler_target: float` — `filler_per_min * 0.5` (50% reduction goal)
  - `replacement_map: dict[str, str]` — static map from filler → replacement suggestion
- **New route:** `services/api/routes/filler_detox.py`:
  - `GET /filler-detox/prompts` → list of 10 prompts (seeded from `filler_prompts.json`)
  - `POST /filler-detox/analyze` body: `{text: str, duration_seconds?: float}` → `FillerReport`
    serialized as JSON
- **Frontend screen:** `app/src/app/filler-detox.tsx`:
  - Fetches a random prompt on mount
  - Shows prompt text + 60s countdown timer
  - Record button (reuses existing recorder infra OR a simple text input for paste)
  - Submit → calls `POST /filler-detox/analyze` → renders `FillerBreakdownView`
  - `FillerBreakdownView` shows: total count, filler_per_min bar (color-coded green/yellow/red),
    top 3 fillers list with per-filler counts, retry challenge banner, replacement phrase chips

---

## P0 — Docs / resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of this plan → `docs/plans/poc-17-filler-detox-plan.md` | TODO | | `test -f docs/plans/poc-17-filler-detox-plan.md` |
| P0.2 | Resumable progress tracker → `docs/plans/poc-17-filler-detox-progress.md` | TODO | | `test -f docs/plans/poc-17-filler-detox-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-17-filler-detox docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend domain: filler analysis module

*Checkpoint:* `analyze_fillers` pure function works correctly; 10+ unit test cases pass.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `services/api/domain/filler.py` — `FillerReport` dataclass + `REPLACEMENT_MAP` (static dict mapping ~15 common fillers to replacement suggestions: "um"→"pause", "like"→"specifically", "you know"→"for example", "basically"→"essentially", "literally"→"truly", "actually"→"in practice", "honestly"→"genuinely", "right"→"correct", "so"→"therefore", "kind of"→"somewhat", "sort of"→"approximately", "I mean"→"that is to say", "okay"→"agreed", "well"→"considering this", "just"→"simply") | TODO | | `python3 -c "from services.api.domain.filler import FillerReport, REPLACEMENT_MAP; print('ok')"` |
| P1.2 | `analyze_fillers(text, filler_words=None, duration_seconds=None) → FillerReport` — case-insensitive word tokenization, counts each filler, computes filler_per_min (duration or word-count heuristic), top 3 by count, target = filler_per_min * 0.5, replacement_map filtered to found fillers | TODO | | Unit test: "um yeah I um like totally like" → per_filler={"um":2,"like":2,"yeah":1}, total=5 |
| P1.3 | Unit test: `services/api/tests/test_filler.py` — cases: (a) empty text → zeros, (b) no fillers → zeros, (c) single filler type, (d) multiple filler types → top_fillers len ≤ 3, (e) filler_per_min computed correctly with explicit duration, (f) word-count heuristic when no duration, (g) replacement_map only contains found fillers, (h) case-insensitive matching ("UM" counted same as "um"), (i) multi-word filler "you know" counted, (j) custom filler_words list overrides default | TODO | | `pytest services/api/tests/test_filler.py -v` → ≥10 passed |
| P1.4 | `services/api/db/seed_data/filler_prompts.json` — 10 prompts, each with `prompt_id` (e.g. `fp-001`), `text` (1–2 sentences), `category` ("personal"|"professional"|"technology"|"opinion"): e.g. "Describe your morning routine", "Talk about a technology that changed your life", "Explain what you do for a living to a 10-year-old", "Describe a challenge you faced at work and how you handled it", "What would you do with an extra hour every day?", "Explain why sleep is important", "Describe your ideal vacation", "Talk about a skill you want to learn", "Explain the last book or article you read", "Describe a person who has inspired you" | TODO | | `python3 -c "import json;d=json.load(open('services/api/db/seed_data/filler_prompts.json'));assert len(d)==10"` |

---

## P2 — Backend API: filler detox routes

*Checkpoint:* `GET /filler-detox/prompts` returns 10; `POST /filler-detox/analyze` returns a
correct `FillerReport` JSON.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `services/api/routes/filler_detox.py` — `FillerPromptItem` + `FillerAnalyzeRequest` + `FillerReportResponse` Pydantic models; `GET /filler-detox/prompts` queries the `filler_prompts` collection (seeded); `POST /filler-detox/analyze` calls `analyze_fillers` and returns serialized `FillerReport` | TODO | | `curl localhost:8090/filler-detox/prompts` → 200 with 10 items |
| P2.2 | Register `filler_detox.router` in `services/api/app.py` with prefix `/filler-detox` | TODO | | `curl localhost:8090/docs` shows `/filler-detox/prompts` and `/filler-detox/analyze` |
| P2.3 | `services/api/db/schemas/filler_prompts.json` — `$jsonSchema` for the prompts collection (required: prompt_id, text) | TODO | | `python3 -c "import json;json.load(open('services/api/db/schemas/filler_prompts.json'))"` |
| P2.4 | Register `filler_prompts` collection in `COLLECTION_SPECS` in `services/api/db/init_mock_db.py`; seed it in `seed_mock.py` (upsert by `prompt_id`) | TODO | | `grep filler_prompts services/api/db/init_mock_db.py` |
| P2.5 | Schema test case for `filler_prompts` in `services/api/tests/test_schemas_poc.py` | TODO | | `pytest services/api/tests/test_schemas_poc.py` → all passed (incl. filler_prompts case) |
| P2.6 | API tests in `services/api/tests/test_api_filler_detox.py` — (a) `GET /prompts` returns 10 items, (b) `POST /analyze` with text containing fillers → correct total + top_fillers, (c) `POST /analyze` with empty text → zeros, (d) `POST /analyze` with duration_seconds → filler_per_min uses it | TODO | | `pytest services/api/tests/test_api_filler_detox.py -v` → ≥4 passed |

---

## P3 — Frontend: filler-detox screen

*Checkpoint:* `/filler-detox` screen renders prompt, accepts text input, submits, shows filler
breakdown with retry challenge and replacement chips.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | `app/src/api/types.ts` — add `FillerPrompt`, `FillerAnalyzeRequest`, `FillerReportResponse` wire types | TODO | | `make poc-app-test` → typecheck clean |
| P3.2 | `app/src/api/client.ts` — `listFillerPrompts()`, `analyzeFillers(req)` | TODO | | `make poc-app-test` → new client tests pass |
| P3.3 | `app/src/app/filler-detox.tsx` — (a) fetch random prompt on mount, (b) show prompt text, (c) 60s countdown timer (starts on "Start" press, stops when user presses "Done"), (d) text input for transcript paste (primary path; audio recording optional behind a flag), (e) "Analyze" button → `analyzeFillers` → show `FillerBreakdownView` | TODO | | `make poc-app-test` green |
| P3.4 | `app/src/ui/FillerBreakdownView.tsx` — presentational component: total filler count, filler_per_min bar (green <2, yellow 2–5, red >5), top 3 fillers list with per-filler count badges, retry challenge banner ("Your goal: reduce from X/min to Y/min"), replacement phrase chips (each filler + its replacement) | TODO | | `make poc-app-test` green; `FillerBreakdownView.test.tsx` ≥4 cases pass |
| P3.5 | Register `/filler-detox` route in `app/src/app/_layout.tsx` (`Stack.Screen` title "Filler Detox") | TODO | | `make poc-app-test` green; route registered |
| P3.6 | Home `index.tsx` — add "Filler Word Detox" card → `/filler-detox` | TODO | | Card visible on home; `make poc-app-test` green |

---

## P4 — E2E verify

*Checkpoint:* paste text with known fillers → correct breakdown shown on web.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Start API + app; navigate to `/filler-detox`; confirm random prompt shown and timer works | TODO | | Prompt text visible; timer counts down |
| P4.2 | Paste text: "Um I think like basically you know what I mean um like this is really um important"; submit → breakdown shows um:3, like:2, total≥5, top 3 listed, retry challenge banner, replacement chips | TODO | | FillerBreakdownView renders correct breakdown |
| P4.3 | Paste empty text → breakdown shows zeros, no crash | TODO | | Screen handles empty gracefully |
| P4.4 | Confirm Mode A/B + persona flows still work (regression check) | TODO | | Mode A session scores correctly |
| P4.5 | `make poc-api-test` green (coverage ≥70%); `make poc-app-test` green | TODO | | Both test suites pass |

---

## Acceptance criteria

- Random prompt shown on load; 60-second countdown timer
- User pastes or types transcript text; submits
- App shows: total filler count, filler per minute (color-coded), top 3 fillers with counts
- App shows retry challenge banner ("Your goal: reduce from 8.2/min to 4.1/min")
- App shows replacement phrase chips for found fillers
- Works without any LLM (purely rule-based on transcript text)
- `make poc-api-test` + `make poc-app-test` green

---

## Decisions & notes

- Transcript text is the input (not raw audio) for MVP simplicity. If `PROVIDER_STT=whisper` is
  set and the user records audio, the frontend could auto-transcribe via the existing `/utterances`
  path — but that adds complexity beyond the MVP. The paste path is sufficient for the demo.
- `filler_prompts` is a new collection in the mock DB. It uses the `assert_mock_target` guard like
  all other collections and is seeded idempotently by `seed_mock.py`.
- The `REPLACEMENT_MAP` is a static dict in `domain/filler.py` — no DB, no LLM. It covers the
  ~15 most common English fillers. Extensibility note: the `POST /analyze` endpoint could accept a
  custom filler_words list in the request body for future language support.
- Timer is cosmetic (client-side countdown) — it does not gate the analyze call. A user can
  submit at any time. The `duration_seconds` field on the analyze request should be populated with
  the actual elapsed time if the timer was running, or omitted (the module uses the word-count
  heuristic instead).
