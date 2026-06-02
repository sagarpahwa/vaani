# POC 20 — Coach/Persona Studio — Implementation Progress Tracker

> **This file is the committed, resumable source of truth for POC 20.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at
[`poc-20-coach-studio-plan.md`](poc-20-coach-studio-plan.md)). Do exactly this:

1. **Read the plan:** [`docs/plans/poc-20-coach-studio-plan.md`](poc-20-coach-studio-plan.md) —
   the full approved design. This tracker is its checklist.
2. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify*
   command / confirm the file exists). A session can die between writing code and committing,
   so the last row marked `DONE` might not be on disk. If it didn't land, redo **only** that
   one step. **Never redo work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-20-coach-studio`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in the plan & CLAUDE.md)

- **Base branch:** `feat/poc-19-human-vs-ai` → new branch `feat/poc-20-coach-studio`
- **Frontend-first.** Custom coaches stored in `AsyncStorage`. Works fully offline.
  Backend sync is optional and never blocks the offline path.
- **Custom personas flow through existing infrastructure** (`mode=persona` + existing personas
  route + existing record/feedback screens). No new pipeline code.
- **Additive, zero regression.** Built-in personas + Mode A/B + golden fixtures unchanged.
- **Hard DB isolation.** Mock DB only: port **27018**. Never touch port 27017.
- **Python env:** `.venv-poc` only. **Keep green:** `make poc-api-lint && make poc-api-test`
  (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** personal SSH host `github.com-personal` / username `sagarpahwa`.

---

## P0 — Docs / resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of this plan → `docs/plans/poc-20-coach-studio-plan.md` | TODO | | `test -f docs/plans/poc-20-coach-studio-plan.md` |
| P0.2 | This resumable tracker → `poc-20-coach-studio-progress.md` | TODO | | `test -f docs/plans/poc-20-coach-studio-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-20-coach-studio docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend (optional sync)

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `services/api/routes/studio.py` — `CustomCoachPayload` Pydantic model; `POST /studio/coaches` (upsert to `personas` with `archetype="custom"`); `DELETE /studio/coaches/{id}` (only `archetype=="custom"` docs) | TODO | | `curl -X POST localhost:8090/studio/coaches -H 'Content-Type: application/json' -d '{"name":"Test",...}' → 201` |
| P1.2 | Register `studio.router` in `services/api/app.py` | TODO | | `curl localhost:8090/docs` shows `/studio/coaches` routes |
| P1.3 | API tests `test_api_studio.py` — ≥5 cases (create→GET includes it, delete→gone, delete non-existent→404, delete built-in→403, missing field→422) | TODO | | `pytest services/api/tests/test_api_studio.py -v` → ≥5 passed |

---

## P2 — Frontend storage layer

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | Install `@react-native-async-storage/async-storage` via `expo install` | TODO | | `grep async-storage app/package.json` |
| P2.2 | `app/src/coaching/customCoaches.ts` — `CustomCoach` type, `RubricDimension` type, `saveCustomCoach`, `listCustomCoaches`, `deleteCustomCoach`, `customCoachToPersonaDetail` | TODO | | `make poc-app-test` → tsc clean |
| P2.3 | Jest mock for `@react-native-async-storage/async-storage` in jest config or `__mocks__` | TODO | | `make poc-app-test` → no "module not found" for async-storage |
| P2.4 | Unit tests `customCoaches.test.ts` — ≥5 cases (save+list, save two+delete one, empty storage, corrupted storage, customCoachToPersonaDetail produces correct PersonaDetail) | TODO | | `make poc-app-test` → ≥5 new tests pass |

---

## P3 — Frontend creation form

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | `app/src/app/coach-studio.tsx` — controlled form (all fields); Save disabled if name or script_lines empty; dynamic rubric list (add/remove rows) | TODO | | `make poc-app-test` green; form renders |
| P3.2 | Save flow: validate → `saveCustomCoach` → navigate to `/`; optional fire-and-forget `POST /studio/coaches` | TODO | | Save calls `saveCustomCoach`; navigates to home |
| P3.3 | Component tests `coach-studio.test.tsx` — ≥5 cases (Save disabled when name empty, disabled when script empty, enabled when both filled, "Add dimension" increases count, "Remove" decreases count) | TODO | | `make poc-app-test` → ≥5 coach-studio tests pass |
| P3.4 | Register `/coach-studio` route in `_layout.tsx` ("Coach Studio") | TODO | | `make poc-app-test` green |

---

## P4 — Frontend integration

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | `app/src/app/index.tsx` — on mount: `listCustomCoaches()`; if non-empty, render "My Custom Coaches" section; each card: name + archetype chip + delete button | TODO | | Home shows "My Custom Coaches" section after save |
| P4.2 | Tap custom coach → persona detail panel via `customCoachToPersonaDetail`; "Speak as …" → `createSession` with `mode=persona` + `persona_id=coach.id` | TODO | | Tapping custom coach starts persona session |
| P4.3 | Delete button → `deleteCustomCoach(id)` → refresh list; optional fire-and-forget `DELETE /studio/coaches/{id}` | TODO | | Delete removes card from home without reload |
| P4.4 | "Coach Studio" card always visible on home → `/coach-studio` | TODO | | "Coach Studio" card visible; navigates to form |
| P4.5 | Home index tests — ≥3 cases ("My Custom Coaches" shows with 1 item, absent when empty, delete button present per card) | TODO | | `make poc-app-test` → new home tests pass |

---

## P5 — E2E verify

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P5.1 | Create "Direct Mentor" coach via form → home shows it in "My Custom Coaches" | TODO | | Custom coach card visible on home |
| P5.2 | Tap "Direct Mentor" → session starts → record → feedback renders style_match | TODO | | Full flow completes; feedback screen renders |
| P5.3 | Delete "Direct Mentor" → card disappears from home | TODO | | Card removed |
| P5.4 | Built-in personas + Mode A/B still work (regression check) | TODO | | Mode A session + 20 legends unaffected |
| P5.5 | `make poc-api-test` green; `make poc-app-test` green | TODO | | Both test suites pass |
| P5.6 | `docs/plans/poc-implementation-progress.md` — add POC 20 milestone row | TODO | | `grep poc-20 docs/plans/poc-implementation-progress.md` |

---

## Decisions & open notes

- `AsyncStorage` wraps `localStorage` on web, native async storage on Android/iOS — works on all
  three platforms without conditional code.
- `customCoachToPersonaDetail` uses default rubric values for acoustic dimensions not explicitly
  set. Rubric dimension weights are normalized to sum to 1.0 before constructing `PersonaDetail`.
- Custom coaches in mock DB have `archetype="custom"` — never included in golden fixtures
  (golden tests seed deterministically with no custom coaches).
- AsyncStorage mock: either the package's own `jest/async-storage-mock` or a manual `__mocks__`
  in-memory implementation. In-memory is simpler; avoid extra jest module mapper entries if
  possible.
- "Coach Studio" card on home is always visible (even with no custom coaches) for discoverability.
