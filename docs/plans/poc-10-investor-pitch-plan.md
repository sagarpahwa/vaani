# POC 10 — Investor Pitch Drill — Implementation Plan

> **This file is the committed, resumable source of truth for POC 10.**
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
   `feat/poc-10-investor-pitch`, conventional commit) → next row. Never batch multiple
   sub-tasks into one commit.
4. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed
   file is authoritative**.

**Base branch:** `feat/poc-09-manager-feedback`
**Working branch:** `feat/poc-10-investor-pitch`

**Status legend:** `TODO` · `DOING` · `DONE` (SHA recorded) · `DEFERRED` (blocker recorded)

---

## KEY CONSTRAINTS

- **Hard DB isolation:** POC only — container `vaani_poc_mongo`, port **27018**, DB
  `public_speaking_intelligence_mock`. Never touch the real DB / port 27017.
- **Python env:** `.venv-poc` only. Never `.venv` / `.venv311`.
- **New dedicated endpoint, not a session.** `POST /pitch-drill/analyze` is a single-call
  analyze endpoint. It accepts either a `transcript` text field (text path) or
  `audio_base64` (audio path → mock STT decodes → same text analysis). The existing
  `POST /sessions` coaching pipeline is not involved.
- **No LLM required.** All 7 pitch component detectors are keyword/phrase-pattern based.
  The investor-readiness score is derived purely from the component count and weighted
  component scores.
- **60-second timer is the same frontend component** (`CountdownTimer`) introduced in
  POC 08. No new timer logic needed.
- **Additive, zero regression.** Existing Mode A/B/persona pipelines, golden fixtures,
  and the feedback_coach routes are completely untouched.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and
  `make poc-app-test` after every sub-task commit.
- **POC schemas isolated:** any new schema in `services/api/db/schemas/` only.
- **Git identity:** conventional commits; never `git add -A`.

---

## What to build

The user records a 60-second startup pitch (or pastes a transcript). The app checks which of
the 7 canonical pitch components are present and produces an **investor-readiness score**:

1. **Problem** — what painful problem is being solved?
2. **Customer** — who is the target customer?
3. **Pain intensity** — how acute/costly is the problem?
4. **Solution** — what does the product do?
5. **Traction** — evidence of progress (revenue, users, growth rate)?
6. **Market** — how big is the opportunity?
7. **Ask** — what are you asking for (funding amount, partnerships)?

The result shows: 7 component check cards (present ✓ / absent ✗), overall investor-readiness
score (0–100), list of missing components, and a "tighter pitch rewrite" built from a template
combining the detected fragments.

### Architecture

- `services/api/domain/pitch.py` — pure domain module: 7 component detector functions
  (keyword/phrase matching), `PitchScores` dataclass, `score_pitch(text) -> PitchScores`.
- `services/api/routes/pitch_drill.py` — `POST /pitch-drill/analyze` (accepts
  `{ transcript?: str, audio_base64?: str }`, returns `PitchScores`).
- Frontend: `app/src/app/investor-pitch.tsx` — intro + 60 s timer recording OR paste
  transcript → submit → 7-component result.

---

## P0 — Docs + branch scaffold

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | This plan file → `docs/plans/poc-10-investor-pitch-plan.md` | TODO | | `test -f docs/plans/poc-10-investor-pitch-plan.md` |
| P0.2 | Progress tracker → `docs/plans/poc-10-investor-pitch-progress.md` (all TODO) | TODO | | `test -f docs/plans/poc-10-investor-pitch-progress.md` |
| P0.3 | Link milestone from `docs/plans/poc-implementation-progress.md` | TODO | | `grep poc-10 docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend domain: 7 pitch component detectors + scorer

*Checkpoint:* `score_pitch(text)` returns correct component booleans and an
`investor_readiness_score` for a sample pitch; 10+ unit tests pass.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | Create `services/api/domain/pitch.py` — define `PitchScores` dataclass (fields: `problem_present`, `customer_present`, `pain_present`, `solution_present`, `traction_present`, `market_present`, `ask_present`, `component_count: int`, `investor_readiness_score: float`, `missing_components: list[str]`, `tighter_rewrite: str`) | TODO | | `python3 -c "from services.api.domain.pitch import PitchScores"` |
| P1.2 | Implement detector marker lists in `pitch.py`: `PROBLEM_MARKERS` (`"problem"`, `"challenge"`, `"pain"`, `"struggle"`, `"broken"`, `"friction"`), `CUSTOMER_MARKERS` (`"for"`, `"target"`, `"customer"`, `"user"`, `"enterprise"`, `"consumer"`, `"smb"`), `PAIN_MARKERS` (`"costs"`, `"hours"`, `"lose"`, `"waste"`, `"expensive"`, `"billion"`, `"million"` + currency/number patterns), `SOLUTION_MARKERS` (`"we built"`, `"our product"`, `"our platform"`, `"our app"`, `"we solve"`, `"solution"`), `TRACTION_MARKERS` (`"revenue"`, `"users"`, `"customers"`, `"growth"`, `"mom"`, `"yoy"`, `"arr"`, `"mrr"`, `"paying"`), `MARKET_MARKERS` (`"market"`, `"industry"`, `"billion dollar"`, `"tam"`, `"opportunity"`), `ASK_MARKERS` (`"raising"`, `"seeking"`, `"looking for"`, `"ask"`, `"investment"`, `"round"`) | TODO | | `grep PROBLEM_MARKERS services/api/domain/pitch.py` |
| P1.3 | Implement `score_pitch(text: str) -> PitchScores` — lowercase text; for each component run substring match against its marker list; `component_count = sum of present components`; `investor_readiness_score = round(component_count / 7 * 100, 1)`; `missing_components` = list of human-readable names for absent components; `tighter_rewrite` = template string assembling detected fragments (or placeholder lines for missing ones) | TODO | | `python3 -c "from services.api.domain.pitch import score_pitch; r=score_pitch('we solve'); print(r.solution_present)"` |
| P1.4 | Unit tests `services/api/tests/test_pitch.py` — 10+ cases: (a) full 7-component pitch → `component_count==7`, score 100; (b) problem present, customer absent; (c) traction markers ("$50k MRR", "200 users") → `traction_present`; (d) market markers ("$2B TAM") → `market_present`; (e) ask markers ("raising $500k") → `ask_present`; (f) empty text → 0 components; (g) `missing_components` list is correct for a 4-of-7 pitch; (h) `investor_readiness_score` is a float in [0, 100]; (i) `tighter_rewrite` is a non-empty string; (j) case-insensitive detection | TODO | | `pytest services/api/tests/test_pitch.py` → ≥10 passed |
| P1.5 | `make poc-api-lint && make poc-api-test` green | TODO | | `make poc-api-lint && make poc-api-test` |

---

## P2 — Backend API: pitch-drill route

*Checkpoint:* `POST /pitch-drill/analyze` returns 200 with all `PitchScores` fields
for both the `transcript` text path and an `audio_base64` path (mock STT decodes to text).

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | Create `services/api/routes/pitch_drill.py` — `POST /pitch-drill/analyze` accepts `PitchAnalyzeRequest(transcript: Optional[str], audio_base64: Optional[str])`; if `audio_base64` provided: decode → `MockSTT.transcribe` → use transcript text; if `transcript` provided directly, use as-is; call `score_pitch(text)` → return `PitchScores` as dict; return 422 if both fields absent | TODO | | `grep "pitch-drill" services/api/routes/pitch_drill.py` |
| P2.2 | Register `pitch_drill` router in `services/api/app.py` with prefix `/pitch-drill` | TODO | | `grep pitch_drill services/api/app.py` |
| P2.3 | API tests `services/api/tests/test_api_pitch_drill.py` — (a) POST with `transcript` containing all 7 markers → `component_count==7`; (b) POST with transcript missing traction → `traction_present==false`; (c) POST with `audio_base64` (mock WAV bytes base64) → 200 response (mock STT runs); (d) POST with neither field → 422; (e) `investor_readiness_score` present in response and is numeric | TODO | | `pytest services/api/tests/test_api_pitch_drill.py` → ≥5 passed |
| P2.4 | `make poc-api-lint && make poc-api-test` green (coverage ≥70%) | TODO | | `make poc-api-lint && make poc-api-test` |

---

## P3 — Frontend: investor-pitch screen + route + home card

*Checkpoint:* Home → "Investor Pitch Drill" → screen with 60 s timer + optional transcript
paste → submit → 7 component check cards + score displayed.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | Add `PitchScores`, `PitchAnalyzeRequest`, `analyzePitch` to `app/src/api/types.ts` and `app/src/api/client.ts` | TODO | | `make poc-app-test` green (typecheck) |
| P3.2 | Create `app/src/app/investor-pitch.tsx` — screen layout: instructions ("60 seconds — cover: Problem · Customer · Pain · Solution · Traction · Market · Ask"), two-tab UI (Record tab: 60 s `CountdownTimer` + record button using existing `useRecorder` hook, auto-submits at timer expire; Paste tab: multiline `TextInput` for transcript); "Analyze" button | TODO | | `make poc-app-test` green (typecheck + lint) |
| P3.3 | Results section in `investor-pitch.tsx`: investor-readiness score displayed as a large number (e.g. "71 / 100"); 7 `Card` components showing component name + ✓ or ✗; "Missing Components" section listing `missing_components`; collapsible "Tighter Rewrite" card | TODO | | `make poc-app-test` green |
| P3.4 | Register `/investor-pitch` route in `app/src/app/_layout.tsx` with title "Investor Pitch Drill" | TODO | | `grep investor-pitch app/src/app/_layout.tsx` |
| P3.5 | Add "Investor Pitch Drill" card to `app/src/app/index.tsx` home — badge "60 SECONDS · 7 COMPONENTS", links to `/investor-pitch` | TODO | | `make poc-app-test` green |
| P3.6 | `make poc-app-test` fully green (lint + typecheck + all jest) | TODO | | `make poc-app-test` |

---

## P4 — E2E verify

*Checkpoint:* end-to-end flow works; both test suites green.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Backend smoke: `POST /pitch-drill/analyze` with a full 7-component pitch transcript → `component_count==7`, `investor_readiness_score==100.0` | TODO | | curl or `pytest -k pitch_drill -m integration` |
| P4.2 | Backend smoke: partial pitch (3 components) → `component_count==3`, `investor_readiness_score≈42.9`, `missing_components` has 4 items | TODO | | curl or pytest |
| P4.3 | `make poc-api-test` fully green (no regressions) | TODO | | `make poc-api-test` |
| P4.4 | `make poc-app-test` fully green | TODO | | `make poc-app-test` |
| P4.5 | Manual / Claude Preview: Home → "Investor Pitch Drill" → paste a sample pitch with 5 of 7 components → Analyze → score shown, 5 ✓ / 2 ✗, tighter rewrite visible | TODO | | visual confirmation |

---

## Decisions & notes

- **No `practice_sessions` involvement.** The pitch drill is a stateless analyze-on-demand
  call. There is no per-line breakdown, no retry, no Goal Signature weighting.
- **Audio path uses MockSTT in POC.** When `audio_base64` is provided, the route decodes
  it and calls `MockSTT.transcribe` (which returns a deterministic transcript from the raw
  bytes). Real Whisper STT is available for the audio path when `PROVIDER_STT=whisper`,
  but is out of scope for the automated tests (no real audio in CI).
- **Investor-readiness score = (components present / 7) × 100.** This is deliberately
  simple for a POC. Post-POC: weight components (traction > problem for certain stage
  investors) and add confidence scores per component.
- **Tighter rewrite is a template.** The route handler assembles the rewrite by substituting
  a sentence for each component: present components contribute their detected sentence
  fragment; absent ones contribute a placeholder ("what problem you solve", etc.). Post-POC:
  generate a coherent paragraph with an LLM.
- **60-second timer reuses `CountdownTimer` from POC 08.** If POC 08 is not yet merged,
  this component must be re-implemented here (same spec) and deduplicated when branches merge.
- **Two input modes: Record and Paste.** The POC treats both as paths to the same text
  analysis. Audio recording auto-submits at timer expire for a seamless demo experience.
- **No new MongoDB collection.** Results are transient (returned in response, not stored).
  Post-POC: persist `pitch_drill_results` for progress tracking.
