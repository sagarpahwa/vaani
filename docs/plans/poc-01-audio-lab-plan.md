# POC 01 — Audio Metrics Lab — Implementation Plan

> **This file is the approved design and resumable tracker for POC 01.**
> It is authoritative across sessions — not in-session memory, not the TaskList.

---

## ▶ HOW TO RESUME (agent: read this block FIRST, every run)

You were told: *"implement this plan"* (pointing at this file). Do exactly this:

1. **Branch:** `feat/poc-01-audio-lab` (off `feat/poc-coaching-app`). Run:
   ```bash
   git checkout feat/poc-coaching-app && git checkout -b feat/poc-01-audio-lab
   ```
2. **Read this whole file** — find the **first sub-task whose status is not `DONE`** in the
   tables below. That is where you resume.
3. **Re-verify the last `DONE` row actually landed** before continuing (run its *Verify* command /
   confirm the file exists). A session can die between writing code and committing, so the last row
   marked `DONE` might not be on disk. If it didn't land, redo **only** that one step. **Never redo
   work already `DONE` and verified.**
4. Work **one atomic sub-task at a time**: do it → run its *Verify* → set status `DONE` + record
   the commit SHA → **`git commit` the code and this tracker together** (branch
   `feat/poc-01-audio-lab`, conventional commit) → next row. Never batch multiple sub-tasks into one
   commit. A crash then costs at most one in-flight step.
5. Mirror progress into TaskCreate/TaskUpdate for in-session visibility, but **this committed file
   is authoritative** — reconcile against it, not against memory.

**Status legend:** `TODO` (not started) · `DOING` (in flight, not committed) · `DONE` (committed;
SHA recorded) · `DEFERRED` (committed decision to skip; blocker recorded).

---

## Key constraints (do not violate — full detail in CLAUDE.md)

- **No new coaching rubric.** This endpoint returns raw metrics only — no capability scores (0–1),
  no GoalSignature weighting, no FeedbackResult. It is a diagnostic tool, not a coach.
- **Reuse existing analysis.** `providers/analysis.py` already computes `DeliveryFeatures` (wpm,
  filler_count, pause_count, speech_ratio, etc.). The new endpoint extracts these and adds
  interpretations — it does **not** duplicate the extraction logic.
- **Audio is optional.** Both `audio_file` and `transcript_text` are optional. With audio but no
  transcript: audio-derived metrics only. With transcript but no audio: text-derived metrics only.
  With both: full metrics set. With neither: return 422 with a clear message.
- **No STT in this endpoint.** The metrics lab does **not** run Whisper. Audio durations and
  speech/silence ratios come from signal-level analysis (the mock's sine-wave heuristics or a real
  VAD probe), not transcription. WPM requires a transcript — if none is given, `wpm` and
  `word_count` are `null`.
- **Isolated POC DB not needed.** This endpoint is stateless — it takes audio+text, returns JSON,
  persists nothing. No new collection. No DB call.
- **Hard DB isolation preserved.** The new route is mounted in the existing `create_app()` factory
  (`services/api/app.py`). Never touch port 27017 or the real DB.
- **Mock is CI default.** Audio signal analysis uses the existing `MockAcousticAnalyzer` when
  `PROVIDER_ACOUSTIC=mock` (default). The real librosa path is opt-in via `PROVIDER_ACOUSTIC=librosa`
  (requires `requirements-local.txt`).
- **Python env:** `.venv-poc` only. Never `.venv` / `.venv311`.
- **Keep green:** `make poc-api-lint && make poc-api-test` (coverage ≥70%) and `make poc-app-test`
  must stay green at every commit.
- **Git identity:** branch `feat/poc-01-audio-lab`; conventional commits; never `git add -A`,
  never force-push / `reset --hard` without explicit ask.

---

## Purpose

The coaching flow transforms raw audio metrics into capability scores (0–1) — the raw numbers are
invisible to the learner. This lab exposes them directly: duration, WPM, filler rate, pause count,
speech ratio, volume variation. Users see their baseline in concrete terms (e.g. "85 WPM → 112 WPM
after a week of practice"). It also validates the full audio→metrics pipeline independently of the
coaching rubric, making it the simplest possible end-to-end integration test.

---

## API contract

```
POST /api/metrics-lab/analyze
Content-Type: multipart/form-data
Fields:
  audio_file:      (optional) audio blob (webm/opus, m4a, wav)
  transcript_text: (optional) plain-text transcript

Response 200:
{
  "duration_sec":      47.3,       -- null if no audio
  "word_count":        112,        -- null if no transcript
  "wpm":               142,        -- null if no transcript or duration
  "filler_count":      4,          -- null if no transcript
  "filler_per_min":    5.1,        -- null if no transcript or duration
  "pause_count":       7,          -- null if no audio
  "long_pause_count":  1,          -- null if no audio
  "speech_ratio":      0.78,       -- null if no audio
  "volume_variation":  0.31,       -- null if no audio
  "clarity_proxy":     0.81,       -- null if no transcript
  "interpretation": {
    "wpm":          "slightly fast — aim 110–150",
    "fillers":      "high — aim <2/min",
    "pauses":       "good",
    "speech_ratio": "good — 76–80% is natural"
  }
}

Response 422: { "detail": "Provide at least one of audio_file or transcript_text." }
```

**Interpretation thresholds (baked into `routes/metrics_lab.py`):**

| Metric | Low | Good | High |
|---|---|---|---|
| wpm | <90 → "slow — aim 110–150" | 90–150 → "good" | >150 → "slightly fast — aim 110–150" |
| filler_per_min | — | <2 → "good — aim <2/min" | 2–5 → "moderate — aim <2/min"; >5 → "high — aim <2/min" |
| pauses | <2 → "few pauses — pauses help comprehension" | 2–8 → "good" | >8 → "many pauses — check for stalling" |
| speech_ratio | <0.55 → "low — many pauses/silences" | 0.55–0.85 → "good — 76–80% is natural" | >0.85 → "high — consider breathing room" |

---

## Frontend screen: `/metrics-lab`

- **Recording UI:** same `<Recorder>` component used in `record.tsx` (reused, not copied). Record
  one continuous clip (no per-line splitting). Show duration counter while recording.
- **Optional transcript:** a `<TextInput>` below the recorder labelled "Paste your script or
  transcript (optional)".
- **Submit:** "Analyze" button — disabled until at least one input exists.
- **Results grid:** 8+ metric cards, each showing: metric name, value, unit, interpretation label
  (color-coded: green = good, amber = moderate, red = needs work).
- **No coaching rubric:** no ScoreBars, no GoalSignature form, no capability names.
- **Home link:** index.tsx gets a new card "Diagnose your delivery" → `/metrics-lab`.

---

## P0 — Docs + branch setup

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P0.1 | This plan file at `docs/plans/poc-01-audio-lab-plan.md` | TODO | | `test -f docs/plans/poc-01-audio-lab-plan.md` |
| P0.2 | Link this milestone in `docs/plans/poc-implementation-progress.md` (add a new row in the Milestone Status table for POC 01) | TODO | | `grep "poc-01-audio-lab" docs/plans/poc-implementation-progress.md` |

---

## P1 — Backend: `routes/metrics_lab.py` + core logic

*Checkpoint:* `POST /api/metrics-lab/analyze` returns the metrics JSON; unit tests green.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P1.1 | Add `interpret_metrics(metrics: dict) -> dict` pure function to `services/api/domain/text.py` — returns the `interpretation` sub-dict based on threshold table above; no external deps | TODO | | `pytest services/api/tests/test_text.py` green; grep `interpret_metrics` in text.py |
| P1.2 | Add `MetricsLabResponse` Pydantic model to `services/api/models.py` — all fields Optional[float/int], plus `interpretation: dict[str, str]` | TODO | | `python3 -c "from services.api.models import MetricsLabResponse; print('ok')"` from `.venv-poc` |
| P1.3 | Create `services/api/routes/metrics_lab.py` — `POST /analyze` multipart handler; extracts `DeliveryFeatures` from text via existing `DeliveryFeatureExtractor`; calls `AcousticAnalyzer` for signal-level metrics when audio bytes present; assembles `MetricsLabResponse`; returns 422 when both inputs absent | TODO | | `grep "APIRouter" services/api/routes/metrics_lab.py` |
| P1.4 | Mount the new router in `services/api/app.py` under prefix `/api/metrics-lab`; confirm `/api/metrics-lab/analyze` appears in `/openapi.json` | TODO | | `grep "metrics_lab" services/api/app.py` |
| P1.5 | Unit test `services/api/tests/test_api_metrics_lab.py`: (a) text-only → wpm+fillers set, audio fields null; (b) 422 on empty request; (c) valid multipart with mock audio bytes → all fields populated; (d) `interpret_metrics` thresholds: slow wpm, high fillers, good speech_ratio | TODO | | `pytest services/api/tests/test_api_metrics_lab.py` green |
| P1.6 | Run `make poc-api-lint` (ruff + black) — clean | TODO | | `make poc-api-lint` exits 0 |
| P1.7 | Run `make poc-api-test` — coverage ≥70%; all prior tests still pass (no regression) | TODO | | `make poc-api-test` green, coverage ≥70% |

---

## P2 — Frontend: `metrics-lab.tsx` screen + home card

*Checkpoint:* `/metrics-lab` route loads in web browser; metrics grid renders.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P2.1 | Add `MetricsLabResponse` type and `analyzeMetrics(formData: FormData)` client function to `app/src/api/types.ts` and `app/src/api/client.ts` | TODO | | `grep "analyzeMetrics" app/src/api/client.ts` |
| P2.2 | Create `app/src/app/metrics-lab.tsx` — screen with: (a) `<Recorder>` component (reused, single-clip mode), (b) optional transcript `TextInput`, (c) "Analyze" button (disabled until input present), (d) loading state, (e) `MetricsGrid` inline component rendering the 8 metric cards with value + unit + interpretation chip; colors: good=green, moderate=amber, high/low=red | TODO | | `test -f app/src/app/metrics-lab.tsx` |
| P2.3 | Register `/metrics-lab` route in `app/src/app/_layout.tsx` (`Stack.Screen` title "Delivery Diagnostics") | TODO | | `grep "metrics-lab" app/src/app/_layout.tsx` |
| P2.4 | Add "Diagnose your delivery" card to `app/src/app/index.tsx` — links to `/metrics-lab`; place below the "Practice with a great speaker" card | TODO | | `grep "metrics-lab" app/src/app/index.tsx` |
| P2.5 | Run `make poc-app-test` (lint + typecheck + jest) — green | TODO | | `make poc-app-test` exits 0 |

---

## P3 — Tests: component tests

*Checkpoint:* all new frontend logic is covered by jest tests.

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P3.1 | `app/src/api/__tests__/metrics_lab.test.ts` — unit test `analyzeMetrics`: (a) calls correct endpoint, (b) returns `MetricsLabResponse` shape, (c) throws `ApiError` on 422 | TODO | | `make poc-app-test` green; grep test file exists |
| P3.2 | `app/src/app/__tests__/metrics-lab.test.tsx` (or co-located) — render MetricsGrid with mock data: assert 8 metric cards render; assert null fields render as "—"; assert interpretation chip text appears | TODO | | `make poc-app-test` green; jest output shows metrics-lab tests |
| P3.3 | Confirm no regression: `make poc-api-test && make poc-app-test` both green | TODO | | both exit 0 |

---

## P4 — E2E verify (web browser walkthrough)

*Checkpoint:* full click-through in the browser (home → metrics-lab → record → analyze → grid).

| # | Sub-task | Status | Commit | Verify |
|---|---|---|---|---|
| P4.1 | Start backend and frontend (`make poc-db-up && make poc-db-setup && make poc-api-run` in one terminal; `make poc-app-web` in another). Verify both healthy: `curl http://localhost:8090/health` → 200; web app loads at :8081 | TODO | | curl exits 0; browser shows home screen |
| P4.2 | Navigate to `/metrics-lab` from home card. Confirm: "Diagnose your delivery" card visible on home; route loads with Recorder + optional transcript input + disabled Analyze button | TODO | | screenshot or preview shows metrics-lab screen |
| P4.3 | Submit with text only (paste a short sentence into the transcript field, leave audio empty). Confirm: Analyze button enables; submission returns metrics grid with WPM, filler_count, clarity_proxy set; audio-only fields (pause_count, speech_ratio, duration_sec) shown as "—" | TODO | | metrics grid renders with expected null-field handling |
| P4.4 | Confirm no console errors and no regression on the home screen (all existing cards still present) | TODO | | browser console clean; existing routes load |
| P4.5 | Confirm `make poc-api-test && make poc-app-test` green on final committed state | TODO | | both exit 0 |

---

## Acceptance criteria

- [ ] `POST /api/metrics-lab/analyze` exists, returns `MetricsLabResponse` JSON.
- [ ] Returns 422 when both `audio_file` and `transcript_text` are absent.
- [ ] Returns at least 8 metrics with interpretation labels.
- [ ] `wpm`, `word_count`, `filler_count`, `clarity_proxy` are `null` when no transcript provided.
- [ ] `duration_sec`, `pause_count`, `speech_ratio` are `null` when no audio provided.
- [ ] No capability scores, no GoalSignature, no coaching rubric in the response.
- [ ] `/metrics-lab` route loads in web browser from the home "Diagnose your delivery" card.
- [ ] Metrics grid shows all non-null metrics with color-coded interpretation chips.
- [ ] `make poc-api-test` green (coverage ≥70%).
- [ ] `make poc-app-test` green (lint + typecheck + jest).
- [ ] No regression on existing Mode A / Mode B / Persona sessions.

---

## Decisions & open notes

- **Stateless by design.** No session, no DB write, no user_id — the metrics lab is a pure
  signal-in / metrics-out utility. This keeps it lightweight and avoids polluting the coaching
  session history with diagnostic runs.
- **Reuse `DeliveryFeatureExtractor`.** It already computes wpm, filler_count, pause_count,
  speech_ratio from a `Transcript` + `DeliveryFeatures`. The new endpoint builds a minimal stub
  transcript from `transcript_text` (tokenize via `domain/text.py`) and passes it through. No new
  extraction logic.
- **WPM requires duration.** If only a transcript is given (no audio), duration is unknown →
  `wpm` = `null`. The UI shows "—" with label "Provide audio for WPM".
- **`clarity_proxy`** is derived from the alignment score (ratio of exact-match tokens) when both
  audio and transcript are given; from vocabulary richness (unique words / total) when transcript
  only; `null` when no transcript.
- **Mock acoustic in CI.** `PROVIDER_ACOUSTIC=mock` (default) produces deterministic signal-level
  estimates so tests never need a real audio file with real signal processing. A minimal WAV fixture
  (the existing mock TTS output, a sine wave) is sufficient for P1.5(c).
- **No new golden fixture.** The metrics lab is not a scoring path — it produces human-readable
  numbers, not versioned model outputs. No golden regression needed.
- **`interpret_metrics` is pure** and lives in `domain/text.py` (already the home for pure text/
  delivery helpers). Thresholds are constants in that function — easy to tune without touching
  routes or models.
- **Android:** the screen uses the same cross-platform `<Recorder>` already validated in Mode A/B.
  No new Android-specific code needed. Android emulator verify is deferred (same constraint as P4.9
  in the personas plan — no SDK in this env).
