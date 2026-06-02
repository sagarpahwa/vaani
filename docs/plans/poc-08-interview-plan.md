# POC 08 — Interview Pressure Simulator — Implementation Plan

> **This file is the committed, resumable source of truth for POC 08.**
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
   `feat/poc-08-interview`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit.
4. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative**.

**Base branch:** `feat/poc-07-sales-objection`
**Working branch:** `feat/poc-08-interview`

**Status legend:** `TODO` · `DOING` · `DONE` (SHA recorded) · `DEFERRED` (blocker recorded)

---

## KEY CONSTRAINTS

- **Hard DB isolation:** POC only — container `vaani_poc_mongo`, port **27018**, DB
  `public_speaking_intelligence_mock`. Never touch the real DB / port 27017.
- **Python env:** `.venv-poc` only. Never `.venv` / `.venv311`.
- **No new backend schema changes to session flow.** The existing `POST /sessions` →
  `POST /sessions/{id}/utterances` → `GET /sessions/{id}` pipeline is reused as-is.
  The timer is purely a frontend concern; `timer_seconds` is added to the guided_scripts
  seed JSON and surfaced on `ScriptDetail`, not on the session model itself.
- **No LLM required.** Interview scoring is keyword-based (ownership, learning, specificity
  markers). The `GoalSignature` occasion `"interview"` weights activate in `goal_signature.py`.
- **Additive, zero regression.** Existing Mode A/B/persona golden fixtures must stay
  byte-for-byte identical. The Mode A/B/persona backend paths are untouched.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and
  `make poc-app-test` after every sub-task commit.
- **POC schemas isolated:** any new schema in `services/api/db/schemas/` only.
- **Frontend timer is screen-local state.** No changes to the backend session model.
  The `record.tsx` reads `timer_seconds` from the session's script data (fetched via
  `getScript`/`getSession`) and activates a `CountdownTimer` component when set.
- **Git identity:** conventional commits; never `git add -A`.

---

## What to build

A 3-question mock interview where each question has a 60-second countdown timer. The user
records an answer per question. The app scores answers on five interview-relevant dimensions:
**structure** (clarity of answer arc), **specificity** (concrete details, numbers, names),
**ownership** (first-person agency markers), **learning** (lesson / growth language), and
**confidence** (low-filler, steady delivery).

### Architecture

The interview mode reuses the existing guided-session flow end-to-end:

- A new `interview-pressure` entry in `services/api/db/seed_data/guided_scripts.json` with
  3 questions as `lines` and a `timer_seconds: 60` field.
- `timer_seconds` is added to the `ScriptDetail` Pydantic model so the frontend can read it.
- A new `GoalSignature` occasion `"interview"` in `domain/goal_signature.py` with
  interview-specific keyword boosts (ownership, learning, specificity markers).
- A new `CountdownTimer` component (`app/src/ui/CountdownTimer.tsx`) — props: `seconds`,
  `onExpire`, style — renders a countdown with a warning at ≤10 s.
- `record.tsx` reads `timer_seconds` from the loaded session script; when non-null it renders
  `<CountdownTimer>` per line and auto-advances on expire.
- A new `app/src/app/interview.tsx` intro screen: shows "3 questions · 60 seconds each"
  and a Start button that creates a guided session with the interview script.
- Existing record → processing → feedback flow reused unchanged.

---

## P0 — Docs + branch scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | This plan file → `docs/plans/poc-08-interview-plan.md` | TODO | | `test -f docs/plans/poc-08-interview-plan.md` |
| P0.2 | Progress tracker → `docs/plans/poc-08-interview-progress.md` (mirrors this structure; all TODO) | TODO | | `test -f docs/plans/poc-08-interview-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` (add POC 08 row) | TODO | | `grep poc-08 docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend data: interview script + model update

*Checkpoint:* `GET /scripts/interview-pressure` returns 3 lines with `timer_seconds: 60`.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | Add `interview-pressure` entry to `services/api/db/seed_data/guided_scripts.json` — fields: `script_id`, `title`, `description`, 3 `lines` (fail/hire/weakness questions), `timer_seconds: 60`, `mode: "interview"`, goal defaults | TODO | | `python3 -c "import json; d=json.load(open('services/api/db/seed_data/guided_scripts.json')); s=[x for x in d if x['script_id']=='interview-pressure'][0]; assert s['timer_seconds']==60 and len(s['lines'])==3"` |
| P1.2 | Add `timer_seconds: Optional[int] = None` to `ScriptDetail` Pydantic model in `services/api/models.py`; `GET /scripts/{id}` serialises it | TODO | | `pytest services/api/tests/test_api_scripts.py -k interview` |
| P1.3 | Update `services/api/db/schemas/guided_scripts.json` — add `timer_seconds` as an optional integer property | TODO | | `python3 -c "import json; s=json.load(open('services/api/db/schemas/guided_scripts.json')); assert 'timer_seconds' in s['\$jsonSchema']['properties']"` |
| P1.4 | Unit tests for script seed: assert interview-pressure has `timer_seconds==60`, 3 lines, correct `script_id` | TODO | | `pytest services/api/tests/ -k interview_script` |
| P1.5 | `make poc-api-lint && make poc-api-test` green after P1 changes | TODO | | `make poc-api-lint && make poc-api-test` |

---

## P2 — Backend scoring: interview occasion + capability weights

*Checkpoint:* a session with `occasion="interview"` activates ownership/learning/specificity
keyword boosts; `RubricScorer` produces non-trivial variation across strong vs weak answers.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | Add `"interview"` to `OCCASION_BOOSTS` in `services/api/domain/goal_signature.py` — ownership keywords (`"I decided"`, `"I took"`, `"I was responsible"`, `"my decision"`), learning keywords (`"I realized"`, `"I learned"`, `"taught me"`, `"in hindsight"`, `"next time"`), specificity keywords (numbers pattern + `"specifically"`, `"for example"`, `"in particular"`) | TODO | | `python3 -c "from services.api.domain.goal_signature import build_goal_signature; gs=build_goal_signature(occasion='interview'); print(gs.capability_weights)"` |
| P2.2 | Confirm `capability_weights` for `"interview"` occasion amplifies `clarity` (structure), `confidence` (low-filler) and keyword-boosted dimensions relative to a neutral occasion | TODO | | unit test in `services/api/tests/test_goal_signature.py::test_interview_occasion_weights` |
| P2.3 | Unit tests for interview scoring: (a) ownership-rich answer scores higher on `clarity`; (b) learning language present → score higher; (c) heavy filler → `confidence` penalised; (d) weak/empty answer → low overall | TODO | | `pytest services/api/tests/test_goal_signature.py -k interview` |
| P2.4 | `make poc-api-lint && make poc-api-test` green | TODO | | `make poc-api-lint && make poc-api-test` |

---

## P3 — Frontend: CountdownTimer component + record.tsx timer integration

*Checkpoint:* `CountdownTimer` counts down, fires `onExpire`, turns red at ≤10 s; `record.tsx`
shows the timer when the loaded session script has `timer_seconds` set, and auto-advances at 0.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | `app/src/ui/CountdownTimer.tsx` — props: `seconds: number`, `onExpire: () => void`, optional `style`; local state counts down with `setInterval`; stops at 0 and calls `onExpire` once; renders elapsed bar (using theme tokens) and numeric label; text/bar colour shifts to `theme.colors.warning` at ≤10 s | TODO | | `make poc-app-test` green |
| P3.2 | `app/src/ui/CountdownTimer.test.tsx` — (a) renders starting seconds; (b) advances on tick (mock `setInterval`); (c) calls `onExpire` exactly once at 0; (d) colour warning prop at 10 s; (e) does not call `onExpire` twice if parent re-renders | TODO | | `make poc-app-test` green (new timer tests pass) |
| P3.3 | Add `timer_seconds?: number` to `ScriptDetail` in `app/src/api/types.ts` | TODO | | `make poc-app-test` green (typecheck) |
| P3.4 | Modify `app/src/app/record.tsx` — when `session.script.timer_seconds` is set on the loaded session, mount `<CountdownTimer seconds={timer_seconds} onExpire={handleTimerExpire} />` above the current-line display; `handleTimerExpire` auto-advances to the next line (same logic as pressing "Next") and briefly shows "Time's up!" banner for 1.5 s | TODO | | `make poc-app-test` green (typecheck + lint) |
| P3.5 | `make poc-app-test` fully green after P3 changes | TODO | | `make poc-app-test` |

---

## P4 — Frontend: interview intro screen + home card + route

*Checkpoint:* Home → "Interview Pressure Simulator" card → `/interview` intro → Start →
`/record` with the interview session loaded and timer visible.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | `app/src/app/interview.tsx` — screen shows title "Interview Pressure Simulator", subtitle "3 questions · 60 seconds each", brief description, list of 3 question previews, and a "Start" button; Start calls `createSession({ mode: "guided", script_id: "interview-pressure", occasion: "interview", ... })` then routes to `/record?sessionId=…` | TODO | | `make poc-app-test` green (typecheck) |
| P4.2 | Register `/interview` route: add `Stack.Screen` with title "Interview Simulator" in `app/src/app/_layout.tsx` | TODO | | `make poc-app-test` green; `grep interview app/src/app/_layout.tsx` |
| P4.3 | Add "Interview Pressure Simulator" card to `app/src/app/index.tsx` home screen — badge "3 QUESTIONS · 60 SECONDS", links to `/interview` | TODO | | `make poc-app-test` green (typecheck + lint) |
| P4.4 | `make poc-app-test` fully green after P4 | TODO | | `make poc-app-test` |

---

## P5 — E2E verify

*Checkpoint:* full click-through — timer counts down per question, auto-advances, feedback
shows interview-relevant scores. Both test suites green.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P5.1 | Backend integration smoke: `POST /sessions` with `script_id=interview-pressure, occasion=interview` → 201; `GET /scripts/interview-pressure` → `timer_seconds==60`, 3 lines | TODO | | `pytest services/api/tests/ -k interview -m integration` (or manual curl) |
| P5.2 | Frontend: `make poc-app-test` fully green (lint + typecheck + all jest including CountdownTimer tests) | TODO | | `make poc-app-test` |
| P5.3 | Backend: `make poc-api-test` green (coverage ≥70%, no golden regressions for Mode A/B/persona) | TODO | | `make poc-api-test` |
| P5.4 | Manual web verify (or Claude Preview): Home → Interview card → intro screen → Start → record screen shows countdown timer (visible 60 s), first question displayed; skip all three → Get feedback → feedback shows `structure`, `specificity`, `ownership`, `learning`, `confidence` capability scores | TODO | | visual confirmation |

---

## Decisions & notes

- **Timer is pure frontend.** The backend session model is unchanged. `timer_seconds` lives
  in the script seed data and is forwarded through `ScriptDetail`; the backend treats
  the interview session exactly like any guided session.
- **"interview" occasion = keyword boosts in GoalSignature.** No new scorer class needed.
  The existing `RubricScorer` + `GoalSignature` capability weight system handles the
  interview-relevant emphasis through the `OCCASION_BOOSTS` map.
- **3 fixed questions, no randomisation.** All 3 are classic behavioural interview questions
  seeded once in `guided_scripts.json`. Randomisation is post-POC.
- **Auto-advance on timer expire = same code path as tapping "Next".** This avoids any
  hidden state divergence in the recorder flow.
- **Capability labels in feedback for interview mode:** `clarity` renders as "Structure",
  `confidence` as "Confidence", the keyword-boosted dims surface their existing labels.
  Post-POC: rename/relabel capabilities per mode for cleaner UI copy.
- **No new DB collection.** The interview session is a standard `practice_sessions` doc with
  `mode: "guided"` and `occasion: "interview"` in the Goal Signature. No schema migration.
