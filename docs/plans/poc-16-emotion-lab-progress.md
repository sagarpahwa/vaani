# POC 16 — Theater/Cinema Emotion Lab — Implementation Progress Tracker

> **This file is the committed, resumable source of truth for POC 16.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at
[`poc-16-emotion-lab-plan.md`](poc-16-emotion-lab-plan.md)). Do exactly this:

1. **Read the plan:** [`docs/plans/poc-16-emotion-lab-plan.md`](poc-16-emotion-lab-plan.md) — the
   full approved design. This tracker is its checklist.
2. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify*
   command / confirm the file exists). A session can die between writing code and committing,
   so the last row marked `DONE` might not be on disk. If it didn't land, redo **only** that
   one step. **Never redo work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` +
   record the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-16-emotion-lab`, conventional commit) → next row. Never batch multiple sub-tasks
   into one commit.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed; SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in the plan & CLAUDE.md)

- **Base branch:** `feat/poc-15-podcast-coach` → new branch `feat/poc-16-emotion-lab`
- **Acoustic-first for emotion scoring.** Persona acoustic path reused entirely. No STT in the
  emotion path. Mock acoustic is the CI default.
- **Additive, zero regression.** Existing Mode A/B + persona golden fixtures stay byte-identical.
  Emotion personas are additive rows in `personas.json` — no existing row is modified.
- **Hard DB isolation.** Mock DB only: port **27018**, database
  `public_speaking_intelligence_mock`. Never touch port 27017.
- **Python env:** `.venv-poc` only. **Keep green:** `make poc-api-lint && make poc-api-test`
  (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** personal SSH host `github.com-personal` / username `sagarpahwa`.

---

## P0 — Docs / resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of this plan → `docs/plans/poc-16-emotion-lab-plan.md` | TODO | | `test -f docs/plans/poc-16-emotion-lab-plan.md` |
| P0.2 | This resumable tracker → `poc-16-emotion-lab-progress.md` | TODO | | `test -f docs/plans/poc-16-emotion-lab-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-16-emotion-lab docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend data: emotion persona seed records

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | Author 5 emotion persona entries in `services/api/db/seed_data/personas.json` (archetype="emotion", 8–10 line original scripts, rubric bands per archetype) | TODO | | `python3 -c "import json;d=json.load(open('services/api/db/seed_data/personas.json'));assert len(d)==25"` |
| P1.2 | Verify all 5 emotion personas pass existing `$jsonSchema` validator | TODO | | `make poc-api-test` → test_schemas_poc.py persona schema test passes |
| P1.3 | Confirm existing `seed_mock.py` seeds all 25 personas idempotently | TODO | | Run seed twice → `personas.count_documents({}) == 25` both runs |
| P1.4 | Unit test: load personas.json, assert 5 records with `archetype=="emotion"`, each has `speech.lines` len ≥ 8 and `rubric.pace_band` | TODO | | `pytest services/api/tests/test_emotion_personas.py -v` |
| P1.5 | Unit test: `GET /personas` returns 25 records | TODO | | `pytest services/api/tests/test_api_personas.py::test_list_returns_25` |
| P1.6 | Unit test: `POST /sessions` with each of the 5 emotion persona_ids → session created (smoke tests) | TODO | | `pytest services/api/tests/test_emotion_e2e.py` (5 cases pass) |

---

## P2 — Frontend: Emotion Lab section

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `app/src/api/types.ts` — extend `PersonaSummary`/`PersonaDetail` with optional `archetype` field | TODO | | `make poc-app-test` → typecheck clean |
| P2.2 | `app/src/app/personas.tsx` — add "Emotion Lab" section below the Legends grid; render emotion personas with "EMOTION" badge | TODO | | `make poc-app-test` green; browser shows two sections |
| P2.3 | Emotion persona detail view — archetype-specific copy ("Deliver this script to match the {Name} style") | TODO | | `make poc-app-test` green |
| P2.4 | Confirm `record.tsx` and `processing.tsx` handle emotion persona sessions unchanged; add confirming comment | TODO | | `make poc-app-test` green |
| P2.5 | `PersonaReadout.test.tsx` — add case for emotion persona label ("SOUNDED LIKE CALM AUTHORITY") | TODO | | `make poc-app-test` green; new test passes |
| P2.6 | Home `index.tsx` — add secondary "Emotion Lab: 5 archetypes" card → `/personas` | TODO | | Card visible on home; `make poc-app-test` green |

---

## P3 — E2E verify

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Navigate to `/personas` → Emotion Lab section shows 5 archetypes | TODO | | Browser shows "Emotion Lab" section with 5 cards |
| P3.2 | Pick "Calm Authority" → detail shows 8–10 line script + rubric summary | TODO | | Detail screen renders correctly |
| P3.3 | Start session → skip-all → feedback shows style_match for Calm Authority | TODO | | `PersonaReadout` renders style_match % for emotion archetype |
| P3.4 | Mode A/B flows still work (regression check) | TODO | | No errors; Mode A session scores correctly |

---

## P4 — Polish + tests

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | `make poc-api-test` green (coverage ≥70%) | TODO | | `make poc-api-test` → green |
| P4.2 | `make poc-app-test` green (lint + typecheck + jest) | TODO | | `make poc-app-test` → all pass |
| P4.3 | `docs/plans/poc-implementation-progress.md` — add POC 16 milestone row | TODO | | `grep poc-16 docs/plans/poc-implementation-progress.md` |
| P4.4 | CLAUDE.md — note `archetype: "emotion"` pattern in personas section | TODO | | `grep emotion CLAUDE.md` |

---

## Decisions & open notes

- Emotion personas are first-class rows in `personas.json` (not a separate file) for simplicity.
- The `archetype` field differentiates them; all other persona path code is unchanged.
- Original scripts are copyright-free, authored to reward the target acoustic delivery style.
- If the `archetype` field is not in the `$jsonSchema` required list, it can be optional.
