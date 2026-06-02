# POC 18 — Pause & Emphasis Gym — Implementation Progress Tracker

> **This file is the committed, resumable source of truth for POC 18.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at
[`poc-18-pause-gym-plan.md`](poc-18-pause-gym-plan.md)). Do exactly this:

1. **Read the plan:** [`docs/plans/poc-18-pause-gym-plan.md`](poc-18-pause-gym-plan.md) — the
   full approved design. This tracker is its checklist.
2. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify*
   command / confirm the file exists). A session can die between writing code and committing,
   so the last row marked `DONE` might not be on disk. If it didn't land, redo **only** that
   one step. **Never redo work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-18-pause-gym`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in the plan & CLAUDE.md)

- **Base branch:** `feat/poc-17-filler-detox` → new branch `feat/poc-18-pause-gym`
- **Mock acoustic is sufficient for CI.** Real librosa is opt-in via `PROVIDER_ACOUSTIC=librosa`.
- **Additive, zero regression.** Mode A/B + persona golden fixtures stay byte-identical.
- **Hard DB isolation.** Mock DB only: port **27018**. Never touch port 27017.
- **Seed data isolated.** `services/api/db/seed_data/pause_scripts.json` + schema in
  `services/api/db/schemas/pause_scripts.json` (NOT shared `schemas/`).
- **Python env:** `.venv-poc` only. **Keep green:** `make poc-api-lint && make poc-api-test`
  (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** personal SSH host `github.com-personal` / username `sagarpahwa`.

---

## P0 — Docs / resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of this plan → `docs/plans/poc-18-pause-gym-plan.md` | TODO | | `test -f docs/plans/poc-18-pause-gym-plan.md` |
| P0.2 | This resumable tracker → `poc-18-pause-gym-progress.md` | TODO | | `test -f docs/plans/poc-18-pause-gym-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-18-pause-gym docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend data + scoring module

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `services/api/db/seed_data/pause_scripts.json` — 5 scripts with `[pause]` markers, display_lines, clean_lines, expected_pause_count | TODO | | `python3 -c "import json;d=json.load(open('services/api/db/seed_data/pause_scripts.json'));assert len(d)==5"` |
| P1.2 | `services/api/db/schemas/pause_scripts.json` — `$jsonSchema` (required: script_id, title, display_lines, clean_lines, expected_pause_count) | TODO | | `python3 -c "import json;json.load(open('services/api/db/schemas/pause_scripts.json'))"` |
| P1.3 | Register `pause_scripts` in `COLLECTION_SPECS`; seed in `seed_mock.py` (upsert by `script_id`) | TODO | | `grep pause_scripts services/api/db/init_mock_db.py` |
| P1.4 | Schema test case for `pause_scripts` in `test_schemas_poc.py` | TODO | | `pytest services/api/tests/test_schemas_poc.py` → all pass |
| P1.5 | `services/api/domain/pause_scorer.py` — `score_pause_discipline(actual, expected) → float` + `build_retry_instruction(actual, expected, script_title) → str` | TODO | | `python3 -c "from services.api.domain.pause_scorer import score_pause_discipline; print(score_pause_discipline(4,4))"` → `1.0` |
| P1.6 | Unit tests `test_pause_scorer.py` — ≥8 cases (equal→1.0, zero→0.0, too-many penalized, too-few, expected==0→1.0, retry instructions for each scenario) | TODO | | `pytest services/api/tests/test_pause_scorer.py -v` → ≥8 passed |

---

## P2 — Backend API: pause gym routes

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `services/api/routes/pause_gym.py` — Pydantic models; `GET /pause-gym/scripts`; `GET /pause-gym/scripts/{id}`; `POST /pause-gym/scripts/{id}/analyze` | TODO | | `curl localhost:8090/pause-gym/scripts` → 200 with 5 items |
| P2.2 | Register `pause_gym.router` in `services/api/app.py` | TODO | | `curl localhost:8090/docs` shows pause-gym routes |
| P2.3 | API tests `test_api_pause_gym.py` — ≥6 cases (list 5, get by id with display_lines, 404, analyze null audio, score equal→1.0, score zero→low+instruction) | TODO | | `pytest services/api/tests/test_api_pause_gym.py -v` → ≥6 passed |

---

## P3 — Frontend: pause gym screen

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | `app/src/api/types.ts` — `PauseScriptSummary`, `PauseScriptDetail`, `PauseAnalyzeRequest`, `PauseAnalysisResult` | TODO | | `make poc-app-test` → typecheck clean |
| P3.2 | `app/src/api/client.ts` — `listPauseScripts()`, `getPauseScript(id)`, `analyzePauseScript(id, req)` | TODO | | `make poc-app-test` → new client tests pass |
| P3.3 | `app/src/app/pause-gym.tsx` — script picker; detail with `PauseMarker` visual gaps; submit → `PauseResultView` | TODO | | `make poc-app-test` green |
| P3.4 | `app/src/ui/PauseMarker.tsx` — visual pause indicator component | TODO | | `PauseMarker.test.tsx` → renders without crash |
| P3.5 | `app/src/ui/PauseResultView.tsx` — expected vs actual count, pause discipline `ScoreBar`, retry instruction `Banner` | TODO | | `PauseResultView.test.tsx` ≥3 cases pass |
| P3.6 | Register `/pause-gym` route in `_layout.tsx` ("Pause Gym") | TODO | | `make poc-app-test` green |
| P3.7 | Home `index.tsx` — add "Pause & Emphasis Gym" card | TODO | | Card visible on home; `make poc-app-test` green |

---

## P4 — E2E verify

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Navigate to `/pause-gym`; 5 scripts listed with expected_pause_count badges | TODO | | 5 scripts listed |
| P4.2 | Select Script 1; `[pause]` items rendered as `PauseMarker` visual gaps | TODO | | Visual pause indicators appear |
| P4.3 | Submit null audio → pause_discipline_score + retry instruction shown | TODO | | `PauseResultView` renders expected vs actual |
| P4.4 | Mode A/B + persona flows still work (regression check) | TODO | | Mode A session scores correctly |
| P4.5 | `make poc-api-test` green; `make poc-app-test` green | TODO | | Both test suites pass |

---

## Decisions & open notes

- `display_lines` includes `[pause]` as regular entries; frontend maps `line === '[pause]'` →
  `<PauseMarker />`.
- `clean_lines` has `[pause]` removed for acoustic analysis.
- Scoring penalizes both too-few AND too-many (ratio > 1.5 penalized).
- Mock acoustic returns `pause_count=2`; inject custom mock for specific-count test cases.
