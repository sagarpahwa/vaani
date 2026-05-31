# Vaani POC — "20 Legends Speaking Coach" (Iteration 1)

> In-repo copy of the approved plan (canonical original lives at
> `~/.claude/plans/here-s-a-curated-top-idempotent-swan.md`). Progress is tracked in
> [`poc-personas-progress.md`](poc-personas-progress.md) — **read that first to resume.**

## Context

We're pivoting the POC from a generic, function-first coach into a **practical, demo-ready product** and shipping it in fast iterations. The product loop:

> Pick 1 of **20 real speakers** → "Today you practice like **X**" → one fixed **~1-minute speech** → record it line by line → **Vaani listens to your actual voice** → you get a style-matched score + **exact, audio-grounded corrections** → re-speak a flagged line → see the improvement.

This is the recommended **POC 1 + POC 3** ("20 people, 20 one-minute speeches, 20 rubrics, one recording flow, one feedback screen"). We build only this now; the YouTube library / role modes / style labs are later iterations.

**Hard requirement (emphatic user instruction):** judge the *real speech*, never a cleaned-up transcript. Whisper silently "fixes" mispronunciations, drops fillers, and smooths stumbles — scoring its text would flatter bad delivery. So **delivery is scored from acoustics** (pace, pauses, pitch/energy measured from the raw waveform), not from an LM transcript.

**Speed mandate:** lean iteration, maximal reuse, lightweight deps. The heavy per-word pronunciation engine (forced alignment, torch/torchaudio) is deliberately **deferred to Iteration 2** so it doesn't block this ship.

---

## What already exists — reuse, do not rebuild

The whole record→score→feedback→retry machinery is already there:

- **Per-line recording** (`app/src/audio/`, `Recorder`/`LineRecorder`) — each line is its own audio clip. Exactly what we need for per-line acoustic analysis and per-line corrections.
- **Processing + Feedback screens**, overall + per-capability score bars, strengths/improvements, **A/B "ideal voice" clips**, and **retry-flagged-lines** (= "speak this line again") with a per-capability **delta** (`app/src/app/feedback.tsx`, `processing.tsx`).
- **Pipeline shape**: `analyze_utterances → features → score → feedback/corrections` (`services/api/domain/pipeline.py`).
- **Provider seams** (mock default for CI, real opt-in via `PROVIDER_*`) and the **isolated mock DB** (port 27018).
- **Real audio decode** already pulled in via PyAV (faster-whisper dep) — reuse it for the acoustic extractor.

**Net-new in Iteration 1** is therefore small: (A) 20-persona content, (B) an acoustic analyzer + persona scoring + `/personas`, (C) a 20-tile grid screen + feedback additions.

---

## Design decision: acoustic-first; the transcript is not the judge

To honor "judge my voice, not the transcript", the **persona flow** (only) uses a new acoustic path:

- **Pace** ("fast/slow") — measured as **syllables/sec** via syllable-nuclei peak detection on the intensity envelope (De Jong & Wempe method). Transcript-free.
- **Pauses / breaks** — silence segmentation from RMS energy → count, durations, locations. Transcript-free.
- **Expressiveness / monotone** — pitch (F0) range + variation via `librosa.pyin`; energy dynamics for emphasis.
- **Content coverage** (did you skip/truncate a line) — per-line **detected-vs-expected syllable count** (transcript-free; the script is known). Catches a skipped line without grading words.
- **Hesitation/disfluency** — proxy from filled/long pauses + energy dips (precise "um" counting waits for the ASR/pronunciation iteration).
- **Style match** — distance of your acoustic profile from the persona's target bands (pace in band? pauses where expected? expressiveness matched?).

Whisper STT stays **off in the persona path** for v1 (kept available behind a flag). Existing **Mode A/B keep their current transcript-based path untouched** — zero regression, smallest blast radius, existing golden gate stays green.

---

## Part A — Content: the 20 personas (seed data)

**A0 — Research & data prep (this *is* the "fetch" for the 20 people):** for each person, confirm the **top reference video** (start from the provided YouTube links, verify with a quick `WebSearch`/`WebFetch`) and distill **how they speak** — pace tendency, signature devices, expressiveness, pause style — from documented talk analyses + reasoning (curated profiles, **no video transcription**). The output is the populated seed file below. One-time authoring step, not a live scraper, so it can't fail at demo time.

New seed file **`services/api/db/seed_data/personas.json`**. One record per person, shape (mirrors the guided-script `lines[]` so the recorder/scorer reuse it):

```jsonc
{
  "persona_id": "steve-jobs",
  "name": "Steve Jobs",
  "role": "Founder",                       // role column from the table
  "archetype": "Product storyteller",
  "reference": { "title": "iPhone 2007 keynote", "video_url": "https://..." },
  "goal_line": "Build suspense, then reveal with simple, confident contrast.",
  "signature_qualities": ["dramatic pause before the reveal","simple concrete words","old-vs-new contrast","measured pace"],
  "speech": {                              // ORIGINAL, written in their style, ~130–150 words ≈ 60s
    "estimated_duration_seconds": 60,
    "lines": [ { "line_index": 0, "text": "...", "coaching_focus": ["pace","suspense"] } ]
  },
  "rubric": {
    "capability_weights": { "clarity":1.2,"pace":1.3,"engagement":1.3,"confidence":1.1,"fluency":0.8,"conciseness":1.1 },
    "target_pace_sps": [2.8, 3.6],         // syllables/sec band for this speaker
    "expressiveness": "high-contrast",     // monotone | balanced | high-contrast
    "pause_style": "dramatic",             // steady | dramatic | brisk
    "feedback_notes": { "too_fast": "You rushed the reveal — Jobs lets silence do the work." }
  }
}
```

- **All 20** (exact list), grouped by role: Steve Jobs, Elon Musk (Founder) · Satya Nadella, Jensen Huang (CEO) · Warren Buffett, Indra Nooyi (Business Leader) · Marty Cagan, Shreyas Doshi (PM) · Chris Voss, Seth Godin (Sales/Marketing) · Nancy Duarte, Matthew Dicks (Storyteller) · Adam Grant, Jordan Peterson (Psychologist) · Sal Khan, Walter Lewin (Teacher) · Sir Ken Robinson, Brené Brown (TED) · Guy Kawasaki, Kevin Kelly (Tech Evangelist).
- **Speeches are original-in-style** (zero copyright, each tuned to exercise that person's standout skill). `reference.video_url` seeds from the provided YouTube links; **curated profiles** come from documented speaking analyses + reasoning, not video transcription.
- Distinct target bands make the demo land: Buffett slow/steady (~2.4–3.0 sps), Huang fast/high-energy (~4.2–5.0), Jobs measured/dramatic, Khan even/explanatory, Voss calm/low/deliberate, Brown warm/variable.

---

## Part B — Backend (acoustic engine + persona scoring)

Follow the CLAUDE.md "New collection for the POC" + provider rules. Co-locate tests; keep `make poc-api-lint` + `make poc-api-test` green.

1. **`personas` collection** — `services/api/db/schemas/personas.json` (NOT shared `schemas/`); register in `COLLECTION_SPECS` in `services/api/db/init_mock_db.py`; seed in `services/api/db/seed_mock.py`; add a case to `services/api/tests/test_schemas_poc.py`; add the row to the POC Data Model table in CLAUDE.md.
2. **Audio decode util** — `services/api/providers/audio_decode.py`: `bytes (webm/opus | m4a) → mono 16 kHz float32 PCM` via PyAV.
3. **Acoustic analyzer provider**:
   - `services/api/providers/base.py`: add `AcousticAnalyzer` ABC: `analyze(pcm, sample_rate, expected_text) -> AcousticFeatures`.
   - `services/api/providers/acoustic.py`: **real** impl (`librosa`/numpy) → `speech_rate_sps`, `articulation_rate_sps`, `pause_count`, `pause_total_s`, `longest_pause_s`, `pause_positions`, `pitch_range_semitones`, `pitch_variation`, `energy_variation`, `est_syllables`, `coverage_ratio`. **mock** impl: deterministic from `expected_text` + seed (keeps CI offline + golden stable).
   - `services/api/providers/registry.py` + `config.py`: build from `PROVIDER_ACOUSTIC` (`mock` default, `librosa` real).
4. **Types** — `services/api/domain/types.py`: add `AcousticFeatures` dataclass; carry on `UtteranceAnalysis`; aggregate onto a persona feature view. Add `style_match` to the score result.
5. **Pipeline** — `services/api/domain/pipeline.py`: when the session is a **persona** session, decode each line's audio → run `AcousticAnalyzer` per line → aggregate; skip Whisper. Mode A/B branch unchanged.
6. **Persona scorer + style match** — extend `RubricScorer` in `services/api/providers/analysis.py` (or sibling `persona_scorer`): `pace` from `speech_rate_sps` vs persona `target_pace_sps` band; `fluency` from acoustic pauses/hesitations; `engagement` from `pitch_variation`/energy; `clarity`/`confidence` from coverage + steadiness; apply persona `capability_weights`. Compute a separate **0–1 `style_match`** from band/pause/expressiveness distance.
7. **Feedback** — persona-flavored, **acoustic-grounded, per-line** corrections using `rubric.feedback_notes`. Reuse the A/B "ideal clip" (`PROVIDER_TTS=macos`) and `CorrectionDraft`.
8. **Session create** — extend `CreateSessionRequest` (`services/api/models.py`) + sessions route with `persona_id`: load persona `speech.lines` as `expected_units`, attach rubric.
9. **Versions/golden** — add persona-scoring version constants in `services/api/domain/versions.py` and **new** persona golden fixtures under `services/api/tests/golden/`. Existing Mode A/B golden untouched.
10. **Deps** — `services/api/requirements-local.txt`: add `librosa` (+ numpy/scipy/soundfile). CI/golden stay on the mock acoustic provider.

---

## Part C — Frontend (grid + feedback)

Talk to the backend only through `app/src/api/client.ts`; read config/flags from `src/config.ts`/`featureFlags.ts`; co-locate tests; keep `make poc-app-test` green.

1. **`app/src/app/personas.tsx`** (new) — grid of **20 monogram tiles** (initials + name + role chip; colored tiles, zero image licensing), modeled on the `mode-a` list/detail pattern. Tap → detail: `goal_line`, the speech `lines`, `signature_qualities`, reference link, **Start**. Start → `createSession({ persona_id })` → push `/record`. Register the route in `app/src/app/_layout.tsx`.
2. **`app/src/api/client.ts` + `types.ts`** — add `listPersonas()` / `getPersona(id)`; extend `createSession` with `persona_id`; add `PersonaSummary` / `PersonaDetail`; extend `SessionDetail` with `style_match` + acoustic metrics.
3. **`app/src/app/index.tsx`** — add a primary **"Practice with a great speaker"** card → `/personas` (headline). Keep Mode A/B as secondary cards.
4. **`app/src/app/feedback.tsx`** — show the persona name, the **style-match score** alongside Overall, and a small acoustic readout (your pace vs target band, pause count). Corrections + retry/delta render as-is.
5. **Reuse `record.tsx` + `processing.tsx` unchanged** (per-line recording + submit/retry already work).
6. **Runs on web *and* Android** from the single Expo codebase (iOS best-effort): `make poc-app-web` / `make poc-app-android`. Monogram grid uses no image assets; Android already points at `10.0.2.2:8090` via `src/config.ts`.

---

## Part D — Tests / CI / docs

- **Unit tests** (mock acoustic → offline, deterministic): syllable-nuclei rate on a synthetic tone-burst signal; pause detection on synthetic silence gaps; persona scorer + `style_match`; persona schema/seed; `/personas` routes. New persona **golden** fixtures.
- **CLAUDE.md**: add `personas` to the POC Data Model table; add `AcousticAnalyzer` to the providers description + `PROVIDER_ACOUSTIC`; note the persona version constants + golden; note `librosa` in `requirements-local.txt`.
- **Progress doc**: add this as the next milestone in `docs/plans/poc-implementation-progress.md`.

---

## Verification (end-to-end, real voice)

```bash
make poc-db-up && make poc-db-setup            # seeds the 20 personas
PROVIDER_ACOUSTIC=librosa PROVIDER_TTS=macos make poc-api-run   # http://localhost:8090/docs
make poc-app-web                                # open the web app
```

In the browser: open **Personas** → pick **Steve Jobs** → record the 1-min speech, then confirm:
- Record **fast**, then **slow** → `pace` + `style_match` change; a correction names the actual rate vs the Jobs band.
- Record **monotone** vs **expressive** → `engagement`/pitch reflects it.
- **Skip a line** → coverage flags it (no transcript).
- A correction cites a **real acoustic event** (a 2 s+ pause, a rushed line), the **A/B ideal clip** plays, and **re-speaking** a flagged line shows a positive **delta**.
- Pick **Warren Buffett** (slow band) → the same fast read that suited Huang is now flagged too fast → proves per-persona scoring.

On **Android**: `make poc-app-android` → same end-to-end flow, recording with the device mic, score returns over `10.0.2.2:8090`.

Backend acceptance: `make poc-api-test` green (incl. new persona golden); `make poc-app-test` green.

---

## End-to-end acceptance — what "done" means for Iteration 1

- ✅ **Data of all 20 people** populated: real top-video reference + authored 1-min speech + per-person rubric.
- ✅ **Coaching system ready**: backend listens to your **actual recorded audio** and returns an overall score, a **style-match** score, acoustic metrics, and **specific per-line corrections** — transcript never grades delivery.
- ✅ **Usable as an end user**: open the **web app (and Android)**, see the 20-tile grid, pick a coach, read the speech, record, submit, get coached, **re-speak a line, see the improvement delta**.
- ✅ **Full testing**: `make poc-api-test` + `make poc-app-test` green (incl. new persona golden); CI stays offline on the mock provider.

---

## Roadmap (the fast iterations after this)

1. **It 2 — Pronunciation:** forced-alignment of audio vs the known script (torch/torchaudio) → per-word "garbled / skipped", precise from audio (still not an LM transcript). Heaviest dep; lands once the loop above is proven.
2. **It 3 — POC 2:** internal YouTube-first curated library (50–100 hand-tagged exemplars) → defensibility.
3. **It 4 — POC 4:** role-based modes (Founder / Sales / PM / Interview / Leadership) → monetization.
4. **It 5 — POC 5:** theater / cinema / debate / podcast "style labs" (written rubrics, no copyrighted clips).
