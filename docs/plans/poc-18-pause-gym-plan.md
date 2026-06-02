# POC 18 — Pause & Emphasis Gym — Implementation Plan

> **This file is the committed, resumable source of truth for POC 18.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at the progress tracker).
Do exactly this:

1. **Read the companion progress tracker** `poc-18-pause-gym-progress.md` — find the
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

- **Base branch:** `feat/poc-17-filler-detox` → new branch `feat/poc-18-pause-gym`
- **Mock acoustic is sufficient for CI.** Pause detection from audio requires either the mock
  acoustic analyzer (deterministic, returns fixed `pause_count`) or the real librosa analyzer
  (`PROVIDER_ACOUSTIC=librosa`, not in CI). The mock path returns deterministic values that are
  sufficient to exercise the full scoring flow in CI.
- **Additive, zero regression.** Mode A/B + persona golden fixtures stay byte-identical. The
  new `pause_gym` routes and scoring module are entirely separate.
- **Hard DB isolation.** Mock DB only: port **27018**. Never touch port 27017.
- **Seed data isolated.** `services/api/db/seed_data/pause_scripts.json` + schema in
  `services/api/db/schemas/pause_scripts.json` (NOT shared `schemas/`).
- **Python env:** `.venv-poc` only. **Keep green:** `make poc-api-lint && make poc-api-test`
  (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** personal SSH host `github.com-personal` / username `sagarpahwa`.

---

## Purpose

The app shows a short script with embedded `[pause]` markers. The user records their delivery.
The backend runs the acoustic analyzer to estimate actual pause count from the audio. It compares
actual vs expected pause count and produces a `pause_discipline_score` plus a specific retry
instruction ("You had 2 pauses but the script needs 4 — add pauses after the key claims in lines
2 and 4"). The frontend renders the script with visual pause indicator gaps.

**Why this uses the existing acoustic path:** the persona path already runs `AcousticAnalyzer` per
utterance to measure `pause_count`. This POC adds a thin scoring function on top of that
measurement — expected vs actual — plus seed scripts with explicit `[pause]` markers. No new audio
pipeline code needed.

---

## Architecture notes

- **Pause scripts** are a new collection `pause_scripts` in the mock DB. Each document:
  - `script_id`, `title`, `full_text` (with `[pause]` markers embedded for reference),
    `display_lines` (list of strings with `[pause]` items included for UI rendering),
    `clean_lines` (list of strings with `[pause]` stripped for STT/acoustic input),
    `expected_pause_count: int` (count of `[pause]` markers), `expected_long_pause_count: int`
    (count of `[pause]` markers preceded by a major claim or period)
- **New domain module:** `services/api/domain/pause_scorer.py` — pure functions:
  - `score_pause_discipline(actual: int, expected: int) → float`:
    - If `actual == 0` and `expected > 0` → `0.0`
    - `ratio = actual / expected`; capped at `2.0` (too many pauses also penalized):
      `score = 1.0 - abs(1.0 - min(ratio, 2.0)) / 2.0` → maps ratio=1.0 to 1.0, ratio=0 to 0.0,
      ratio=2.0 to 0.5
    - Returns `round(score, 3)`
  - `build_retry_instruction(actual: int, expected: int, script_title: str) → str`:
    returns a human-readable string, e.g.:
    - `actual < expected * 0.5` → "You had {actual} pause(s) but the script needs {expected}. Add meaningful pauses after the key claims."
    - `actual > expected * 1.5` → "You had {actual} pauses — that's more than needed ({expected}). Aim for intentional pauses only."
    - Otherwise → "Good pause count. Focus on placing pauses precisely at the [pause] markers."
- **New route:** `services/api/routes/pause_gym.py`:
  - `GET /pause-gym/scripts` → list of 5 pause scripts (summary: id, title, expected_pause_count)
  - `GET /pause-gym/scripts/{script_id}` → full detail with display_lines
  - `POST /pause-gym/scripts/{script_id}/analyze` body: `{audio_base64: str | null}`:
    - If `audio_base64` is null → use mock acoustic (returns fixed `pause_count=2`)
    - Else → decode + run `AcousticAnalyzer.analyze` (from `app.state.providers`)
    - Compute `pause_discipline_score` + `retry_instruction`
    - Return `PauseAnalysisResult`: `actual_pause_count`, `expected_pause_count`,
      `pause_discipline_score`, `retry_instruction`

---

## P0 — Docs / resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of this plan → `docs/plans/poc-18-pause-gym-plan.md` | TODO | | `test -f docs/plans/poc-18-pause-gym-plan.md` |
| P0.2 | Resumable progress tracker → `docs/plans/poc-18-pause-gym-progress.md` | TODO | | `test -f docs/plans/poc-18-pause-gym-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-18-pause-gym docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend data + scoring module

*Checkpoint:* 5 pause scripts loadable; `score_pause_discipline` unit tests pass.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `services/api/db/seed_data/pause_scripts.json` — 5 scripts with `[pause]` markers embedded. Script 1: "The difference between a good speaker and a great speaker is not vocabulary. [pause] It is control. [pause] Control over pace. [pause] Control over silence. [pause] Control over what the listener feels next." (4 pauses). Scripts 2–5 authored with 3–6 pause markers each, covering different rhetorical styles (persuasive, narrative, instructional, motivational) | TODO | | `python3 -c "import json;d=json.load(open('services/api/db/seed_data/pause_scripts.json'));assert len(d)==5"` |
| P1.2 | `services/api/db/schemas/pause_scripts.json` — `$jsonSchema` for pause_scripts (required: script_id, title, display_lines, clean_lines, expected_pause_count) | TODO | | `python3 -c "import json;json.load(open('services/api/db/schemas/pause_scripts.json'))"` |
| P1.3 | Register `pause_scripts` in `COLLECTION_SPECS` in `services/api/db/init_mock_db.py`; seed in `seed_mock.py` (upsert by `script_id`) | TODO | | `grep pause_scripts services/api/db/init_mock_db.py` |
| P1.4 | Schema test case for `pause_scripts` in `services/api/tests/test_schemas_poc.py` | TODO | | `pytest services/api/tests/test_schemas_poc.py` → all pass |
| P1.5 | `services/api/domain/pause_scorer.py` — `score_pause_discipline(actual, expected) → float` + `build_retry_instruction(actual, expected, script_title) → str` | TODO | | `python3 -c "from services.api.domain.pause_scorer import score_pause_discipline; print(score_pause_discipline(4,4))"` → `1.0` |
| P1.6 | Unit tests `services/api/tests/test_pause_scorer.py` — cases: (a) actual==expected → 1.0, (b) actual==0, expected>0 → 0.0, (c) actual>expected*1.5 → penalized (score < 0.75), (d) actual==expected//2 → partial credit, (e) expected==0 → 1.0 (no pauses needed), (f) retry_instruction when too few, (g) retry_instruction when too many, (h) retry_instruction when on target | TODO | | `pytest services/api/tests/test_pause_scorer.py -v` → ≥8 passed |

---

## P2 — Backend API: pause gym routes

*Checkpoint:* `GET /pause-gym/scripts` returns 5; `POST /analyze` returns correct score.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `services/api/routes/pause_gym.py` — `PauseScriptSummary` + `PauseScriptDetail` + `PauseAnalyzeRequest` + `PauseAnalysisResult` Pydantic models; `GET /pause-gym/scripts`, `GET /pause-gym/scripts/{id}`, `POST /pause-gym/scripts/{id}/analyze` | TODO | | `curl localhost:8090/pause-gym/scripts` → 200 with 5 items |
| P2.2 | Register `pause_gym.router` in `services/api/app.py` | TODO | | `curl localhost:8090/docs` shows pause-gym routes |
| P2.3 | API tests `services/api/tests/test_api_pause_gym.py` — (a) list returns 5 scripts, (b) get by id returns display_lines with `[pause]` entries, (c) 404 for unknown id, (d) analyze with null audio → mock pause_count → valid score, (e) score for actual=expected → 1.0, (f) score for actual=0 → low score + "too few" instruction | TODO | | `pytest services/api/tests/test_api_pause_gym.py -v` → ≥6 passed |

---

## P3 — Frontend: pause gym screen

*Checkpoint:* `/pause-gym` shows script list; detail shows visual pause markers; results show
pause discipline score and retry instruction.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | `app/src/api/types.ts` — add `PauseScriptSummary`, `PauseScriptDetail`, `PauseAnalyzeRequest`, `PauseAnalysisResult` wire types | TODO | | `make poc-app-test` → typecheck clean |
| P3.2 | `app/src/api/client.ts` — `listPauseScripts()`, `getPauseScript(id)`, `analyzePauseScript(id, req)` | TODO | | `make poc-app-test` → new client tests pass |
| P3.3 | `app/src/app/pause-gym.tsx` — (a) script picker list (title + expected_pause_count badge), (b) script detail: render `display_lines` where `[pause]` items appear as a visual gap component (`PauseMarker`), (c) record button (reuse skip path for demo: null audio), (d) submit → `analyzePauseScript` → show `PauseResultView` | TODO | | `make poc-app-test` green |
| P3.4 | `app/src/ui/PauseMarker.tsx` — small presentational component: a horizontal bar or ellipsis "— pause —" in a muted accent color that visually represents an expected pause in the script | TODO | | `PauseMarker.test.tsx` → renders without crash |
| P3.5 | `app/src/ui/PauseResultView.tsx` — shows: expected vs actual pause count (e.g. "Expected: 4 / You had: 2"), pause_discipline_score as a `ScoreBar` labeled "Pause Discipline", retry instruction text in a `Banner` | TODO | | `PauseResultView.test.tsx` ≥3 cases pass (on-target, too-few, too-many) |
| P3.6 | Register `/pause-gym` route in `app/src/app/_layout.tsx` (`Stack.Screen` title "Pause Gym") | TODO | | `make poc-app-test` green |
| P3.7 | Home `index.tsx` — add "Pause & Emphasis Gym" card → `/pause-gym` | TODO | | Card visible on home; `make poc-app-test` green |

---

## P4 — E2E verify

*Checkpoint:* full click-through on web with mock acoustic; scoring logic verified.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Start API + app; navigate to `/pause-gym`; confirm script list with 5 entries | TODO | | 5 scripts listed with expected_pause_count badges |
| P4.2 | Select Script 1; confirm display shows `[pause]` items rendered as `PauseMarker` visual gaps | TODO | | Visual pause indicators appear at correct positions |
| P4.3 | Submit with null audio → backend returns mock `pause_count`; results show pause_discipline_score + retry instruction | TODO | | PauseResultView renders expected vs actual count |
| P4.4 | Confirm Mode A/B + persona flows still work (regression check) | TODO | | Mode A session scores correctly |
| P4.5 | `make poc-api-test` green (coverage ≥70%); `make poc-app-test` green | TODO | | Both test suites pass |

---

## Acceptance criteria

- 5 short scripts available, each with `[pause]` markers at key rhetorical moments
- Frontend renders scripts with visual pause indicators (not just raw `[pause]` text)
- User can submit (with or without real audio) to get pause discipline score
- Feedback shows: expected pause count, actual pause count, pause_discipline_score, retry instruction
- Works with mock acoustic (no librosa required for the demo flow)
- `make poc-api-test` + `make poc-app-test` green

---

## Decisions & notes

- The `display_lines` array in each pause_script includes `[pause]` as regular entries in the
  line list. The frontend maps each entry: if `line === '[pause]'` → render `<PauseMarker />`;
  else → render as text. This keeps the data model simple and the rendering logic trivial.
- The `clean_lines` array has `[pause]` entries removed — used for acoustic analysis (the backend
  passes each clean line as `expected_text` to `AcousticAnalyzer.analyze`). For the mock analyzer
  this is moot (returns fixed values); for librosa it avoids confusing the silence segmentation
  with literal `[pause]` text.
- Scoring formula penalizes both too-few AND too-many pauses (ratio > 1.5 is penalized), which
  discourages users from inserting excessive pauses to game the metric.
- The mock acoustic analyzer returns `pause_count=2` by default for any input. Test cases that
  need a specific pause count should inject a custom mock acoustic via the existing provider
  injection pattern used in `test_persona_e2e.py`.
