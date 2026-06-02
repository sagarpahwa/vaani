# POC 17 — Filler Word Detox — Implementation Progress Tracker

> **This file is the committed, resumable source of truth for POC 17.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at
[`poc-17-filler-detox-plan.md`](poc-17-filler-detox-plan.md)). Do exactly this:

1. **Read the plan:** [`docs/plans/poc-17-filler-detox-plan.md`](poc-17-filler-detox-plan.md) —
   the full approved design. This tracker is its checklist.
2. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify*
   command / confirm the file exists). A session can die between writing code and committing,
   so the last row marked `DONE` might not be on disk. If it didn't land, redo **only** that
   one step. **Never redo work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-17-filler-detox`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in the plan & CLAUDE.md)

- **Base branch:** `feat/poc-16-emotion-lab` → new branch `feat/poc-17-filler-detox`
- **No LLM required.** All filler analysis is rule-based (word-matching).
- **`FILLER_WORDS` already exists** in `services/api/providers/base.py`. Import from there.
- **Additive, zero regression.** Mode A/B + persona golden fixtures stay byte-identical.
- **Hard DB isolation.** Mock DB only: port **27018**. Never touch port 27017.
- **Python env:** `.venv-poc` only. **Keep green:** `make poc-api-lint && make poc-api-test`
  (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** personal SSH host `github.com-personal` / username `sagarpahwa`.

---

## P0 — Docs / resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of this plan → `docs/plans/poc-17-filler-detox-plan.md` | TODO | | `test -f docs/plans/poc-17-filler-detox-plan.md` |
| P0.2 | This resumable tracker → `poc-17-filler-detox-progress.md` | TODO | | `test -f docs/plans/poc-17-filler-detox-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-17-filler-detox docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend domain: filler analysis module

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `services/api/domain/filler.py` — `FillerReport` dataclass + `REPLACEMENT_MAP` (15 common fillers → replacements) | TODO | | `python3 -c "from services.api.domain.filler import FillerReport, REPLACEMENT_MAP; print('ok')"` |
| P1.2 | `analyze_fillers(text, filler_words=None, duration_seconds=None) → FillerReport` — counts, filler_per_min, top 3, target, replacement_map filtered to found fillers | TODO | | Unit test: "um yeah I um like totally like" → per_filler={"um":2,"like":2,"yeah":1} |
| P1.3 | Unit tests `test_filler.py` — ≥10 cases (empty, no fillers, single type, multiple, filler_per_min, word-count heuristic, replacement_map, case-insensitive, multi-word filler, custom filler_words) | TODO | | `pytest services/api/tests/test_filler.py -v` → ≥10 passed |
| P1.4 | `services/api/db/seed_data/filler_prompts.json` — 10 prompts with prompt_id, text, category | TODO | | `python3 -c "import json;d=json.load(open('services/api/db/seed_data/filler_prompts.json'));assert len(d)==10"` |

---

## P2 — Backend API: filler detox routes

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `services/api/routes/filler_detox.py` — Pydantic models; `GET /filler-detox/prompts`; `POST /filler-detox/analyze` | TODO | | `curl localhost:8090/filler-detox/prompts` → 200 with 10 items |
| P2.2 | Register `filler_detox.router` in `services/api/app.py` | TODO | | `curl localhost:8090/docs` shows filler-detox routes |
| P2.3 | `services/api/db/schemas/filler_prompts.json` — `$jsonSchema` (required: prompt_id, text) | TODO | | `python3 -c "import json;json.load(open('services/api/db/schemas/filler_prompts.json'))"` |
| P2.4 | Register `filler_prompts` in `COLLECTION_SPECS`; seed in `seed_mock.py` (upsert by `prompt_id`) | TODO | | `grep filler_prompts services/api/db/init_mock_db.py` |
| P2.5 | Schema test case for `filler_prompts` in `test_schemas_poc.py` | TODO | | `pytest services/api/tests/test_schemas_poc.py` → all passed |
| P2.6 | API tests `test_api_filler_detox.py` — 4 cases: list returns 10, analyze with fillers → correct, empty text → zeros, duration_seconds used | TODO | | `pytest services/api/tests/test_api_filler_detox.py -v` → ≥4 passed |

---

## P3 — Frontend: filler-detox screen

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | `app/src/api/types.ts` — `FillerPrompt`, `FillerAnalyzeRequest`, `FillerReportResponse` | TODO | | `make poc-app-test` → typecheck clean |
| P3.2 | `app/src/api/client.ts` — `listFillerPrompts()`, `analyzeFillers(req)` | TODO | | `make poc-app-test` → new client tests pass |
| P3.3 | `app/src/app/filler-detox.tsx` — random prompt, 60s timer, text input, "Analyze" button → `FillerBreakdownView` | TODO | | `make poc-app-test` green |
| P3.4 | `app/src/ui/FillerBreakdownView.tsx` — total count, filler_per_min bar (green/yellow/red), top 3 list, retry challenge banner, replacement chips | TODO | | `FillerBreakdownView.test.tsx` ≥4 cases pass |
| P3.5 | Register `/filler-detox` route in `_layout.tsx` ("Filler Detox") | TODO | | `make poc-app-test` green; route registered |
| P3.6 | Home `index.tsx` — add "Filler Word Detox" card | TODO | | Card visible on home; `make poc-app-test` green |

---

## P4 — E2E verify

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Navigate to `/filler-detox`; random prompt shown; timer works | TODO | | Prompt text visible; timer counts down |
| P4.2 | Paste filler-heavy text; submit → correct breakdown (um:3, like:2, retry challenge, chips) | TODO | | `FillerBreakdownView` renders correct breakdown |
| P4.3 | Paste empty text → zeros, no crash | TODO | | Screen handles empty gracefully |
| P4.4 | Mode A/B + persona flows still work (regression check) | TODO | | Mode A session scores correctly |
| P4.5 | `make poc-api-test` green; `make poc-app-test` green | TODO | | Both test suites pass |

---

## Decisions & open notes

- Transcript text is the input (not raw audio) for MVP simplicity.
- `REPLACEMENT_MAP` is a static dict in `domain/filler.py` — no DB, no LLM.
- Timer is cosmetic client-side; does not gate the analyze call.
- `filler_prompts` is a new mock DB collection using `assert_mock_target` guard.
