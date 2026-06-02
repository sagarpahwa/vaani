# POC 20 — Coach/Persona Studio — Implementation Plan

> **This file is the committed, resumable source of truth for POC 20.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at the progress tracker).
Do exactly this:

1. **Read the companion progress tracker** `poc-20-coach-studio-progress.md` — find the
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

- **Base branch:** `feat/poc-19-human-vs-ai` → new branch `feat/poc-20-coach-studio`
- **Frontend-first.** Custom coaches are stored in `localStorage` (via a typed wrapper). The
  feature works fully offline. Backend sync is optional and additive — its absence never breaks
  the offline path.
- **Custom personas flow through existing infrastructure.** A custom speaker persona flows
  through `mode=persona` via the existing personas API. A custom conversation scenario (if
  implemented) uses the existing conversation path. No new pipeline code needed.
- **Additive, zero regression.** Built-in personas, Mode A/B, and all golden fixtures stay
  byte-identical. Custom coaches are purely additive data.
- **Hard DB isolation.** Mock DB only: port **27018**. Never touch port 27017. The optional
  backend sync saves to the mock DB's `personas` collection (existing) or a new `custom_coaches`
  collection.
- **Python env:** `.venv-poc` only. **Keep green:** `make poc-api-lint && make poc-api-test`
  (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** personal SSH host `github.com-personal` / username `sagarpahwa`.

---

## Purpose

A local UI for creating custom coaches or personas. User fills out a form (name, archetype, type,
scenario, script lines, rubric dimensions, feedback style). Created coaches are saved to
`localStorage` and appear on the home screen under "My Custom Coaches". User can start a practice
session with a custom coach — which flows through the existing persona recording + feedback
infrastructure. Custom coaches can be deleted.

**Why localStorage-first:** the feature is most useful as a rapid prototyping tool for coaches
who want to try out a persona idea immediately, without waiting for backend round-trips. The data
is small (text fields only) and does not require persistence across devices for the POC.

---

## Architecture notes

### localStorage layer (`app/src/coaching/customCoaches.ts`)

Thin wrapper around `AsyncStorage` (React Native's async-safe localStorage equivalent, available
in Expo). API:

- `CustomCoach` type: `{ id: string, name: string, archetype: string, type: 'speaker_persona',
  goal_line: string, description: string, script_lines: string[], rubric_dimensions:
  RubricDimension[], feedback_style: string, created_at: string }`
- `RubricDimension` type: `{ name: string, weight: number }` (weights are user-input floats,
  normalized to sum to 1 before display)
- `saveCustomCoach(coach: Omit<CustomCoach, 'id' | 'created_at'>) → Promise<CustomCoach>`:
  generate `id = 'custom-' + Date.now()`, set `created_at = new Date().toISOString()`, save
  under key `'vaani:custom_coaches'` as JSON array
- `listCustomCoaches() → Promise<CustomCoach[]>`: read from AsyncStorage, parse, return list
  (empty array if key missing or parse fails)
- `deleteCustomCoach(id: string) → Promise<void>`: filter out by id, save back
- `customCoachToPersonaDetail(coach: CustomCoach) → PersonaDetail`: adapter that maps a
  `CustomCoach` to the existing `PersonaDetail` type so it can flow through the existing
  persona record screen without modification

### Backend sync route (`services/api/routes/studio.py`) — optional

- `POST /studio/coaches` body: `CustomCoach` JSON → upserts into `personas` collection with
  `archetype: "custom"`; returns `persona_id` (same as `coach.id`)
- `DELETE /studio/coaches/{id}` → deletes from `personas` where `persona_id == id AND archetype
  == 'custom'` (never deletes built-in personas)
- No new collection needed (reuses `personas`); no new schema changes (existing schema is
  permissive enough for custom entries)

### Frontend creation form (`app/src/app/coach-studio.tsx`)

Fields:
1. **Name** — text input (required)
2. **Archetype** — text input (e.g. "Assertive mentor", "Warm encourager") — optional hint chips
3. **Goal line** — text input (what the user should sound like after practicing)
4. **Description** — multiline text (brief persona description)
5. **Script lines** — multiline text input (each line is a new paragraph; split on `\n` to
   produce `script_lines[]`)
6. **Rubric dimensions** — dynamic list: "Add dimension" button adds a row with name + weight
   number input; "Remove" button per row
7. **Feedback style** — text input (e.g. "Be direct and specific", "Be encouraging")
8. **Save** button → `saveCustomCoach` → navigate back to home

---

## P0 — Docs / resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of this plan → `docs/plans/poc-20-coach-studio-plan.md` | TODO | | `test -f docs/plans/poc-20-coach-studio-plan.md` |
| P0.2 | Resumable progress tracker → `docs/plans/poc-20-coach-studio-progress.md` | TODO | | `test -f docs/plans/poc-20-coach-studio-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-20-coach-studio docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend (optional sync)

*Checkpoint:* `POST /studio/coaches` + `DELETE /studio/coaches/{id}` work against the mock DB.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | `services/api/routes/studio.py` — `CustomCoachPayload` Pydantic model (name, archetype, type, goal_line, description, script_lines, rubric_dimensions, feedback_style); `POST /studio/coaches` (upsert to `personas` with `archetype="custom"`); `DELETE /studio/coaches/{id}` (delete only `archetype=="custom"` docs) | TODO | | `curl -X POST localhost:8090/studio/coaches -H 'Content-Type: application/json' -d '{"name":"Test","archetype":"custom",...}' → 201` |
| P1.2 | Register `studio.router` in `services/api/app.py` | TODO | | `curl localhost:8090/docs` shows `/studio/coaches` routes |
| P1.3 | API tests `services/api/tests/test_api_studio.py` — (a) create coach → `GET /personas` returns it (archetype="custom"), (b) delete coach → no longer in list, (c) delete non-existent → 404, (d) delete built-in persona → 403 (forbidden — `archetype != "custom"`), (e) create with missing required field → 422 | TODO | | `pytest services/api/tests/test_api_studio.py -v` → ≥5 passed |

---

## P2 — Frontend storage layer

*Checkpoint:* `customCoaches.ts` CRUD works correctly; tests pass.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | Install `@react-native-async-storage/async-storage` via `expo install` (Expo-compatible version); add to `app/package.json` | TODO | | `grep async-storage app/package.json` |
| P2.2 | `app/src/coaching/customCoaches.ts` — `CustomCoach` type, `RubricDimension` type, `saveCustomCoach`, `listCustomCoaches`, `deleteCustomCoach`, `customCoachToPersonaDetail` | TODO | | TypeScript compiles clean (`make poc-app-test` → tsc clean) |
| P2.3 | Jest mock for `@react-native-async-storage/async-storage` in `app/jest.config.js` (or in a `__mocks__` file) so tests run without native module | TODO | | `make poc-app-test` → no "module not found" for async-storage |
| P2.4 | Unit tests `app/src/coaching/customCoaches.test.ts` — (a) save + list → list contains saved coach, (b) save two + delete one → list has one remaining, (c) listCustomCoaches on empty storage → empty array, (d) listCustomCoaches with corrupted storage → empty array (no crash), (e) customCoachToPersonaDetail produces a PersonaDetail with correct `persona_id`, `name`, and `speech.lines` | TODO | | `make poc-app-test` → ≥5 new tests pass |

---

## P3 — Frontend creation form

*Checkpoint:* `/coach-studio` renders all form fields; save writes to AsyncStorage; dynamic
rubric list works.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | `app/src/app/coach-studio.tsx` — controlled form state (all fields); "Name" and "Script lines" fields are required (Save button disabled if either is empty); dynamic rubric list: state is `RubricDimension[]`, "Add dimension" appends a row, "Remove" splices it out | TODO | | `make poc-app-test` green; form renders without errors |
| P3.2 | Save flow: validate required fields → `saveCustomCoach(...)` → navigate back to `'/'` (home); optional: if API is reachable, also call `POST /studio/coaches` (fire-and-forget, never blocks save) | TODO | | Save button calls `saveCustomCoach`; navigates to home |
| P3.3 | Unit/component test `coach-studio.test.tsx` — (a) Save button disabled when name empty, (b) Save button disabled when script_lines empty, (c) enabled when both filled, (d) "Add dimension" increases rubric row count, (e) "Remove" decreases rubric row count | TODO | | `make poc-app-test` → ≥5 coach-studio tests pass |
| P3.4 | Register `/coach-studio` route in `app/src/app/_layout.tsx` (`Stack.Screen` title "Coach Studio") | TODO | | `make poc-app-test` green; route registered |

---

## P4 — Frontend integration: custom coaches on home

*Checkpoint:* created coaches appear on home screen; tapping one opens the persona detail/record
flow; delete works.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | `app/src/app/index.tsx` — on mount: `listCustomCoaches()` → if list non-empty, render a "My Custom Coaches" section below the built-in cards; each custom coach card shows name + archetype chip + delete button (×) | TODO | | Home screen shows "My Custom Coaches" section after saving one |
| P4.2 | Tapping a custom coach card → navigate to `/personas?coachId={id}` OR pass via params to an adapted persona detail panel; `customCoachToPersonaDetail` produces the `PersonaDetail` the detail panel already expects; "Speak as …" starts a `createSession` with `mode=persona` + `persona_id=coach.id` | TODO | | Tapping custom coach starts a persona session |
| P4.3 | Delete button on home → `deleteCustomCoach(id)` → refresh list (custom coach disappears); optional: also call `DELETE /studio/coaches/{id}` (fire-and-forget) | TODO | | Delete removes card from home without page reload |
| P4.4 | "Create Custom Coach" / "Coach Studio" card on home (appears above the "My Custom Coaches" section, always visible) → `/coach-studio` | TODO | | "Coach Studio" card visible; tapping navigates to form |
| P4.5 | Unit tests for home index changes — (a) "My Custom Coaches" section renders when `listCustomCoaches` returns 1 item, (b) section absent when list is empty, (c) delete button present per coach card | TODO | | `make poc-app-test` → new home tests pass |

---

## P5 — E2E verify

*Checkpoint:* create → appear on home → start practice → get feedback; delete works.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P5.1 | Start app; navigate to `/coach-studio`; fill out form (name "Direct Mentor", archetype "Direct", goal "Sound clear and direct", script lines: "State the problem clearly. Then give one solution. Don't add qualifiers."); press Save → home shows "Direct Mentor" in "My Custom Coaches" | TODO | | Custom coach card visible on home |
| P5.2 | Tap "Direct Mentor" → detail view shows name + script lines; press "Speak as Direct Mentor" → session starts (mode=persona) → record → processing → feedback renders (style_match shown for custom coach) | TODO | | Full flow completes; feedback screen renders |
| P5.3 | Press delete (×) on "Direct Mentor" card → card disappears from home | TODO | | Custom coach card removed |
| P5.4 | Confirm built-in personas, Mode A/B flows still work (regression check) | TODO | | Mode A session scores correctly; 20 legends still listed |
| P5.5 | `make poc-api-test` green (coverage ≥70%); `make poc-app-test` green | TODO | | Both test suites pass |
| P5.6 | Update `docs/plans/poc-implementation-progress.md` with POC 20 milestone row | TODO | | `grep poc-20 docs/plans/poc-implementation-progress.md` |

---

## Acceptance criteria

- User can create a custom coach with: name (required), archetype, goal line, description, script
  lines (required), rubric dimensions (dynamic list), feedback style
- Created coaches appear under "My Custom Coaches" on the home screen
- Tapping a custom coach flows through the existing persona record + feedback infrastructure
- User can delete a custom coach from the home screen
- Optional backend sync works if the API is running (fire-and-forget, never blocks offline use)
- Feature works fully offline (localStorage / AsyncStorage only)
- `make poc-api-test` + `make poc-app-test` green

---

## Decisions & notes

- `AsyncStorage` is the Expo-compatible cross-platform async key-value store. On web it wraps
  `localStorage`; on Android/iOS it uses the native async storage. This means the feature works
  on all three platforms without conditional code.
- The `customCoachToPersonaDetail` adapter maps `coach.script_lines` → `speech.lines` (strings)
  and uses default rubric values for any acoustic dimensions not explicitly set. This is the
  minimal bridge needed so the existing `_create_persona_session` pipeline accepts a custom
  coach without any backend changes.
- Rubric dimension weights: the user enters raw numbers (e.g. "Pace: 2, Clarity: 1"). The
  adapter normalizes them to sum to 1.0 before constructing the `PersonaDetail.rubric`. If all
  weights are zero (user entered zeros or left blank), equal weights are used.
- The "Coach Studio" creation card on home is always visible (even with no custom coaches) to
  make it discoverable. A "+" icon approach (floating button) is an alternative but a card is
  more consistent with the rest of the home screen design.
- Custom coaches persisted to the mock DB (via optional sync) appear in `GET /personas` with
  `archetype="custom"`. They will not be included in any persona golden test fixtures since
  golden fixtures are seeded deterministically at test time with no custom coaches.
- AsyncStorage mock in jest: the recommended jest mock for `@react-native-async-storage/async-storage`
  is the package's own `jest/async-storage-mock` or a manual `__mocks__` file that provides an
  in-memory implementation. Either approach is acceptable; the in-memory implementation is simpler
  and avoids an extra jest module mapper entry.
