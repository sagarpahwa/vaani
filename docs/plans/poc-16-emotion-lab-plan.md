# POC 16 — Theater/Cinema Emotion Lab — Implementation Plan

> **This file is the committed, resumable source of truth for POC 16.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file or at the progress tracker).
Do exactly this:

1. **Read the companion progress tracker** `poc-16-emotion-lab-progress.md` — find the
   **first sub-task whose status is not `DONE`** in the tables there. That is where you resume.
2. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify* command /
   confirm the file exists). A session can die between writing code and committing, so the last row
   marked `DONE` might not be on disk. If it didn't land, redo **only** that one step.
3. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` + record
   the commit SHA → **`git commit` the code and the progress tracker together** → next row.
4. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but the **committed
   progress tracker is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` · `DOING` · `DONE` (SHA recorded) · `DEFERRED` (blocker recorded)

---

## KEY CONSTRAINTS (never violate — full rules in CLAUDE.md)

- **Base branch:** `feat/poc-15-podcast-coach` → new branch `feat/poc-16-emotion-lab`
- **Acoustic-first for emotion scoring.** The emotion persona path scores the real waveform via
  the existing `AcousticAnalyzer` interface (mock default, librosa opt-in). No STT in the
  emotion path — judge the delivery, not the transcript.
- **Additive, zero regression.** Mode A/B + existing persona golden fixtures stay byte-identical.
  Emotion personas are additional rows in `personas.json` distinguished by `archetype: "emotion"`.
- **Mock is the CI default.** `PROVIDER_ACOUSTIC=mock` (deterministic, offline). The mock returns
  deterministic values that are sufficient to exercise the whole flow end-to-end in CI.
- **Hard DB isolation.** Mock DB only: port **27018**, database
  `public_speaking_intelligence_mock`. Never touch port 27017.
- **POC schemas isolated.** `services/api/db/schemas/` only — NOT the shared `schemas/`.
- **Audio never in Mongo.** ObjectStore abstraction only (LocalFS default).
- **Python env:** `.venv-poc` only (`make poc-api-install`). Never `.venv` / `.venv311`.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test`.
- **Git identity:** personal SSH host `github.com-personal` / username `sagarpahwa`.

---

## Purpose

User picks one of five emotion archetypes (calm authority, controlled intensity, vulnerable truth,
inspiring rally, mysterious reveal). The app provides an original 30-second script designed for
that archetype. The user records a delivery. The backend scores the delivery against the
archetype's acoustic rubric (pace band, energy level, pitch variation, pause style) using the
existing persona acoustic path. The feedback screen shows a style_match percentage ("You sounded
72% like Calm Authority") plus per-dimension acoustic readout.

**Why this is nearly free to build:** the persona acoustic scoring path (`domain/persona.py`,
`providers/acoustic.py`, `providers/acoustic_librosa.py`, `routes/personas.py`) already handles
everything. Emotion personas are simply five new persona records in `personas.json` with
emotion-appropriate rubrics and shorter original scripts. No new backend infrastructure is needed.

---

## Architecture notes

- Emotion personas live in `services/api/db/seed_data/personas.json` alongside the 20 speaker
  legends. They are distinguished by `archetype: "emotion"` and a top-level `"emotion_id"` field
  (or equivalently `persona_id` prefixed `emotion-*`).
- The existing `GET /personas` endpoint returns them all. The frontend filters by archetype to
  render the "Emotion Lab" section in the personas grid.
- `CreateSessionRequest` with `mode="persona"` + `persona_id` pointing to an emotion persona
  flows through the same `_create_persona_session` / `run_persona` / `score_persona` pipeline.
- Rubric bands per archetype (these are the `rubric` fields in each persona record):
  1. **calm_authority** — pace 2.5–3.5 sps, energy variation: low/steady, pitch variation: low,
     pause style: few long deliberate pauses
  2. **controlled_intensity** — pace 3.5–4.5 sps, medium-high energy, high pitch range, pointed pauses
  3. **vulnerable_truth** — pace 2.0–3.0 sps, low overall energy but variable, medium pitch
     variation, frequent short pauses
  4. **inspiring_rally** — pace 3.5–5.0 sps, high energy, high pitch variation, dramatic pauses
     before key lines
  5. **mysterious_reveal** — pace 2.0–3.2 sps, low baseline energy with sharp peaks, wide pitch
     range, long pauses before reveals

---

## P0 — Docs / resumability scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | In-repo copy of this plan → `docs/plans/poc-16-emotion-lab-plan.md` | TODO | | `test -f docs/plans/poc-16-emotion-lab-plan.md` |
| P0.2 | Resumable progress tracker → `docs/plans/poc-16-emotion-lab-progress.md` | TODO | | `test -f docs/plans/poc-16-emotion-lab-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-16-emotion-lab docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend data: emotion persona seed records

*Checkpoint:* `GET /personas` returns 25 (20 legends + 5 emotion); each emotion persona has a
valid rubric and an 8–10 line original script.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | Author 5 emotion persona entries in `services/api/db/seed_data/personas.json` — each with: `persona_id` (`emotion-calm-authority` etc.), `name` (display label), `role` ("Emotion Archetype"), `archetype` ("emotion"), `description`, `goal_line`, `signature_qualities` (3–4 descriptors), `speech.lines` (8–10 lines, ~30s original script), `rubric` (pace band, energy_level, pitch_variation, pause_style, capability_weights) | TODO | | `python3 -c "import json;d=json.load(open('services/api/db/seed_data/personas.json'));assert len(d)==25"` |
| P1.2 | Verify all 5 emotion personas pass the existing personas `$jsonSchema` validator (required fields: persona_id, name, speech, rubric) | TODO | | `make poc-api-test` → test_schemas_poc.py persona schema test passes |
| P1.3 | Confirm existing `seed_mock.py` seeds all 25 personas (no code change needed; verify idempotency) | TODO | | Run seed twice → `personas.count_documents({}) == 25` both runs |
| P1.4 | Unit test: load personas.json, assert 5 records with `archetype=="emotion"`, each has `speech.lines` list of len ≥ 8, `rubric.pace_band` present | TODO | | `pytest services/api/tests/test_emotion_personas.py -v` |
| P1.5 | Unit test: verify `GET /personas` returns 25 records via TestClient | TODO | | `pytest services/api/tests/test_api_personas.py::test_list_returns_25` |
| P1.6 | Unit test: `POST /sessions` with `mode=persona` + each of the 5 emotion persona_ids → session created (smoke test for acoustic scoring path with emotion rubrics) | TODO | | `pytest services/api/tests/test_emotion_e2e.py` (5 session-create cases pass) |

---

## P2 — Frontend: Emotion Lab section in personas grid

*Checkpoint:* "Emotion Lab" section visible on `/personas`; user can navigate from grid →
detail → record → processing → feedback with style_match shown.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | `app/src/api/types.ts` — extend `PersonaSummary` and `PersonaDetail` to carry optional `archetype` field; add `'emotion'` to an `ArchetypeKind` union | TODO | | `make poc-app-test` → typecheck clean |
| P2.2 | `app/src/app/personas.tsx` — add an "Emotion Lab" section below the Legends grid: filter personas where `archetype === 'emotion'`; render with a distinct visual treatment (e.g. colored accent badge "EMOTION" instead of monogram initials; use the existing `Card` component) | TODO | | `make poc-app-test` green; browser shows two sections |
| P2.3 | Emotion persona detail view — reuse the existing persona detail panel in `personas.tsx`; add archetype-specific copy ("Deliver this script to match the {Name} style — {goal_line}") | TODO | | `make poc-app-test` green |
| P2.4 | Ensure `record.tsx` and `processing.tsx` handle emotion persona sessions — no code change expected (they already work for any `mode=persona` session); write a comment confirming this | TODO | | `make poc-app-test` green |
| P2.5 | `PersonaReadout` in `feedback.tsx` already renders style_match for any persona — confirm it renders correctly for an emotion persona label (e.g. "SOUNDED LIKE CALM AUTHORITY 72%"); add a test case to `PersonaReadout.test.tsx` | TODO | | `make poc-app-test` green; new test passes |
| P2.6 | Home screen `index.tsx` — add a secondary card "Emotion Lab: 5 archetypes" → `/personas` (or `/personas#emotion-lab`) | TODO | | `make poc-app-test` green; card visible on home |

---

## P3 — E2E verify

*Checkpoint:* full click-through on web: home → personas → emotion persona detail → record →
processing → feedback showing style_match for the emotion archetype.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Start API + app (`make poc-db-up && make poc-db-setup && make poc-api-run` and `make poc-app-web`); navigate to `/personas` → confirm Emotion Lab section with 5 archetypes | TODO | | Browser shows "Emotion Lab" section with 5 cards |
| P3.2 | Pick "Calm Authority" → verify detail shows 8–10 line script + rubric summary ("2.5–3.5 syll/s · low energy · deliberate pauses") | TODO | | Detail screen renders correctly |
| P3.3 | Start session → skip-all (no mic needed) → Get feedback → feedback screen shows style_match for Calm Authority persona | TODO | | `PersonaReadout` renders "SOUNDED LIKE CALM AUTHORITY" with style_match % |
| P3.4 | Verify no console errors; Mode A/B flows still work (regression check) | TODO | | No errors; Mode A session still scores and shows feedback |

---

## P4 — Polish + tests

*Checkpoint:* `make poc-api-test` + `make poc-app-test` green; coverage ≥70%.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Backend: ensure coverage gate still ≥70% after new test files; run `make poc-api-test` | TODO | | `make poc-api-test` → green, coverage ≥70% |
| P4.2 | Frontend: ensure `make poc-app-test` green (lint + typecheck + jest) | TODO | | `make poc-app-test` → all pass |
| P4.3 | Update `docs/plans/poc-implementation-progress.md` with POC 16 milestone row | TODO | | `grep poc-16 docs/plans/poc-implementation-progress.md` |
| P4.4 | CLAUDE.md: note the `archetype: "emotion"` pattern in the personas seed data section (one line) | TODO | | `grep emotion CLAUDE.md` |

---

## Acceptance criteria

- 5 emotion archetypes available in the personas grid under an "Emotion Lab" section
- Each has an 8–10 line original 30-second script
- User can record a delivery (or skip-all for demo)
- Feedback shows `style_match` score ("You sounded 72% like Calm Authority") plus pace, energy,
  pitch variation, pause readout via the existing `PersonaReadout` component
- No new backend infrastructure introduced (reuses the persona acoustic path end-to-end)
- Mode A/B golden fixtures unchanged
- `make poc-api-test` + `make poc-app-test` green

---

## Decisions & notes

- Emotion personas are first-class rows in `personas.json` (not a separate file) so the single
  `GET /personas` endpoint and the single seeder handle them automatically.
- The `archetype: "emotion"` field is the only distinguishing marker. All other persona path code
  is unchanged.
- Original scripts are copyright-free (authored for this POC). Each script is purposely designed
  to reward the target acoustic delivery style — e.g. the Calm Authority script uses short
  declarative sentences that reward low pace and deliberate pauses.
- If the `archetype` field does not yet exist on the personas `$jsonSchema` `required` list, it
  can be an optional field — the schema only requires the fields that were defined in P1 of the
  personas POC (persona_id, name, speech, rubric).
