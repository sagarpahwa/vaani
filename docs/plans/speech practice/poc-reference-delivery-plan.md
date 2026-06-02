# POC — Reference Delivery + Speech Lab — Complete Build Record

> **Location:** `poc/reference-delivery/`
> **Status:** ✅ Feature-complete (core pipeline fully operational)
> **Stack:** Node.js 18+ ES modules · Express · OpenAI API (Whisper + gpt-4o-mini-tts + gpt-4.1-mini) · Python 3 + librosa · ffmpeg
> **Purpose:** Generate world-class keynote reference audio from any speech text, then let the user record themselves, score their attempt with hard-gated validity, and receive structured human-language coaching.

---

## What This POC Proves

1. A full **reference-generation pipeline** can produce professional-quality TTS keynote performance from plain text — beat map → per-unit TTS → compose + master → MP3.
2. A **speech analysis pipeline** can compare a user's recording to a reference script with real Whisper transcription, Levenshtein DP alignment, acoustic feature extraction, pitch/prosody analysis, and hard-gated scoring.
3. **Scoring integrity**: a terrible attempt (< 50% script coverage) must score 3–5/100, never 33/100. The validity gate enforces this before any delivery dimension is computed.
4. **Human-language coaching** — no raw numbers (no dB, no ms, no %), just structured feedback: what happened → why it hurts → what to do → the effect.
5. The full stack (reference generation + user analysis) is driven by a **single-file Node.js server** with SSE streaming, no database, no auth, no cloud object storage.

---

## Hard Constraints — Never Violate

| Constraint | Detail |
|---|---|
| No ElevenLabs | Not mentioned anywhere in code, comments, or UI |
| No "voice clone" / "impersonation" language | Always say "Steve Jobs-inspired product keynote performance" |
| No database | All state is in-memory (`sessionScripts` Map) or local file system |
| No auth | Pure local POC |
| No rebuilding from scratch | Incremental additions only |
| OPENAI_API_KEY | Only from `.env` file via dotenv |
| No unrelated UI | Only Reference Generator + Speech Lab tabs |

---

## Repository Location & Stack

```
poc/reference-delivery/
├── server.js                  # Express app — 3 endpoints, SSE streaming
├── package.json               # npm scripts: dev, start, setup:analysis, test:speech-lab
├── .env                       # OPENAI_API_KEY (not committed)
├── .gitignore                 # generated/, uploads/, .venv/, .analysis-ready.json
├── server/                    # 15 backend modules
├── scripts/                   # setup-analysis.js (Python venv bootstrap)
├── python/                    # analyze_prosody.py + requirements.txt
├── public/index.html          # Full React SPA (no bundler, Babel standalone)
├── test/test-speech-lab.js    # Regression test (bad fixture → score ≤ 5)
├── fixtures/                  # bad_user_audio.webm (not committed)
├── generated/                 # session dirs with MP3s, WAVs, manifests
└── uploads/                   # multer temp storage (auto-cleaned)
```

**Total source code:** ~4 700 lines across 20+ files.

---

## Server Modules — What Each Does

### Reference Generation Pipeline

| File | Lines | Purpose |
|---|---|---|
| `server/performanceDirector.js` | 164 | Calls GPT-4.1-mini to generate a beat map: per-sentence emotion, pace contour (slow/medium/fast), energy level (1–10), pause duration + reason, TTS instruction, 3 delivery variants. Supports 3 take styles: `restrained`, `emotional`, `launch`. |
| `server/ttsGenerator.js` | 93 | Calls `gpt-4o-mini-tts` per unit with the director's instruction. Generates 3 candidate variants and picks the best. Saves individual unit WAVs to session directory. |
| `server/audioComposer.js` | 99 | Concatenates unit WAVs with silence gaps (from `pauseAfterMs`) into a single combined WAV using ffmpeg. |
| `server/audioMastering.js` | 23 | Converts combined WAV to final MP3 at 192kbps via ffmpeg. |
| `server/acousticEvaluator.js` | 114 | Analyzes the final MP3: duration, speech ratio, long-pause count, dynamic range (dB), overall performance score. Uses ffmpeg silencedetect. |

### Speech Lab Analysis Pipeline

| File | Lines | Purpose |
|---|---|---|
| `server/audioConverter.js` | 160 | **Central conversion hub.** Probes audio with ffprobe (handles Chrome MediaRecorder WebM "N/A duration" bug by re-probing the converted WAV). Converts any browser format (WebM/Opus, MP4, OGG, WAV) to 16kHz mono PCM WAV. Validates duration (5s–600s). Detects silence (hasSpeech). |
| `server/transcriptionService.js` | 72 | Calls Whisper-1 with `language: 'en'` and vocabulary hint prompt (TinyTrail brand terms). Falls back to gpt-4o-transcribe, then whisper-1 plain. Returns `{text, words[], duration, quality}` with word-level timestamps. |
| `server/transcriptAligner.js` | 189 | **Levenshtein DP alignment** of expected script words vs spoken words. Classifies each op as `correct`, `missing`, `extra`, `substitution`, or `possible_asr_confusion` (for known product-name mishearings). Computes `coverage = (correct + confusion*0.5) / total`. Exports `alignTranscripts()`, `getUnitTimeWindow()`, `mapUnitsToExpectedWordRanges()`, `getUnitOps()`. |
| `server/audioFeatureExtractor.js` | 206 | Extracts per-unit acoustic features from the WAV: duration, RMS volume (dB), speech ratio, silence segments, pace (WPM), lead/trail silence. Uses ffmpeg silencedetect + manual WAV header parsing for sample counts. |
| `server/prosodyAnalyzer.js` | 104 | Spawns `python/analyze_prosody.py` via stdin/stdout JSON. Checks `.analysis-ready.json` before running. Returns pitch median, pitch range (semitones), pitch slope, RMS dB stats, energy slope, monotone score, voiced fraction, speech chunk count, pause label. Falls back gracefully if librosa unavailable. |
| `server/scoringEngine.js` | 293 | **Hard-gated scoring.** See Scoring System section below. |
| `server/coachingFeedback.js` | 254 | GPT-4.1-mini feedback generation. For catastrophic/major: 5 fixed script-completion coaching points. For partial/valid: AI-generated Top 5 fixes (no percentages, no dB/Hz/ms numbers, structure: what → why → what to do → effect) + per-unit feedback + overall summary. |
| `server/feedbackAudioComposer.js` | 209 | Extracts user audio clips for worst 5 units (ffmpeg), copies reference TTS clips, generates corrected TTS clips with adjusted delivery instructions. Returns `Map<unitIndex, {user, reference, corrected}>`. |
| `server/feedbackGenerator.js` | 224 | *(Legacy — superseded by coachingFeedback.js but kept for reference)* |
| `server/referenceComparator.js` | 223 | *(Legacy — superseded by scoringEngine.js but kept for reference)* |

---

## The Scoring System (Core Algorithm)

### Step 1 — Validity Gate (runs before any delivery scoring)

```
scriptCoverage = (correct + possibleAsrConfusion × 0.5) / expectedWords

coverage < 0.50 → catastrophic_script_mismatch  → maxOverall =  5
coverage < 0.70 → major_script_mismatch          → maxOverall = 25
coverage < 0.85 → partial_attempt                → maxOverall = 55
coverage ≥ 0.85 → valid_attempt                  → maxOverall = 100

Additional hard caps (applied after tier):
  missingWords > 40% of expected → cap at  5
  (extra + substitution) > 25%   → cap at 20
```

For **catastrophic** attempts: `overallScore = max(1, min(5, floor(coverage × 10)))`. A recording of the TinyTrail script covering 46% of words → score = 4. Acoustic/prosody analysis is **skipped entirely** to save compute.

### Step 2 — Per-Unit Status

```
unitCoverage = (unitCorrect + unitConfusion×0.5) / unitExpectedWords

< 30% → mostly_skipped   → score 0–5, no delivery bars
< 60% → partial          → score capped at 25
≥ 60% → complete         → full delivery scoring
```

### Step 3 — Delivery Dimensions (complete units only)

| Dimension | Weight | Measurement |
|---|---|---|
| Accuracy | 3 | `unitCoverage × 100` |
| Pace | 2 | Deviation from ideal WPM (from beat map pace contour); ±10% → 100, ±60% → 0 |
| Energy | 2 | RMS mean vs beat-map energy target; ±10% → 100 |
| Pauses | 1 | Trail silence vs `pauseAfterMs` target; ±30% → 100 |
| Expression | 2 | Pitch range semitones vs energy-level threshold (requires librosa); if unavailable → null |

Weighted average → apply partial cap → apply session cap (`maxOverall`).

### Step 4 — Session Summary

- `catastrophic`: `overallScore = max(1, min(5, floor(coverage×10)))`
- `major`: `overallScore = max(6, min(25, 6 + (coverage−0.5)/0.20 × 19))`
- `partial`/`valid`: average of scored units, capped at `maxOverall`

---

## The Transcript Aligner (Levenshtein DP)

Classic edit-distance DP over tokenized word arrays. Back-traces to produce a list of ops:

- `correct` — word matches (case/punct-normalized)
- `missing` — expected word not spoken
- `extra` — spoken word not in script
- `substitution` — different word in place of expected
- `possible_asr_confusion` — known ASR mishearing of a product name (e.g. "tinytrail" → "tiny", "trail", "train", "trial") — gets 0.5 credit in coverage

ASR confusion map is in `transcriptAligner.js` and is extensible. Whisper timestamps are attached to each op via `spoToExp` index mapping.

---

## Reference Generation — Beat Map + TTS Flow

1. User pastes speech text (default: TinyTrail ~145-word keynote)
2. GPT-4.1-mini generates a beat map: sentences split into performance units, each with emotion, pace contour, energy 1–10, pause after (ms + reason), 3 delivery variants, director's TTS instruction
3. Each unit is synthesized via `gpt-4o-mini-tts` with the instruction as `instructions` field; 3 candidates, best selected by acoustic score
4. Units composed: WAVs concatenated with silence gaps via ffmpeg
5. Master: WAV → MP3 at 192kbps
6. Manifest saved: `generated/{sessionId}/manifest_{style}.json` — preserves beat map + unit WAV paths for later analysis comparison
7. `sessionScripts.set(sessionId, text)` — **script frozen at generation time**
8. Supports 3 take styles simultaneously: Restrained · Emotional · Product Launch

---

## Speech Lab Analysis — 10-Step Pipeline (SSE streamed)

```
1. Validate + Convert   → probeAudio → convertToWav (16kHz mono PCM)
                          re-probe WAV if source had no duration metadata (Chrome WebM)
2. Transcribe           → Whisper-1 with vocabulary hint, word timestamps
3. Align                → Levenshtein DP, ASR confusion detection
4. Validity Gate        → computeValidity() → SSE: validity_check event
5. Map time windows     → mapUnitsToExpectedWordRanges + getUnitTimeWindow
6. Acoustic features    → SKIPPED for catastrophic_script_mismatch
7. Prosody (Python)     → SKIPPED if isProsodyReady()=false or catastrophic
8. Score units          → scoreUnit() per unit, hard-capped
9. Build summary        → buildSessionSummary()
10. Generate feedback   → generateAllFeedback() → OpenAI batch
    + Audio clips       → extractUserClip + extractReferenceClip + generateCorrectedClip
```

SSE events emitted: `progress`, `audio_ready`, `transcription_done`, `validity_check`, `prosody_done`, `complete`, `error`.

---

## Frontend — React SPA (no bundler)

Single HTML file (`public/index.html`, 1 297 lines). React 18 via CDN, Babel standalone transform.

### Two Top-Level Tabs

**Reference Generator:**
- Textarea (default: TinyTrail script, 145 words)
- Voice selector (marin/cedar/onyx/nova/alloy/shimmer), mode selector, 3-takes checkbox
- Streaming progress: take pills, phase-aware progress bar (beat_map → tts → compose → master)
- Per-take: playback audio, ⬇ MP3 download, ↺ Stronger regeneration
- Expandable Beat Map table + performance script view
- "→ Go to Speech Lab" button after generation

**Speech Lab:**
- Setup warning banner if `prosodyReady = false` (checks `/api/health/audio` on mount)
- Script drift warning if textarea edited after reference was generated (frozenScript mechanism)
- Script read-along (locked to generation-time version)
- MediaRecorder: WebM/Opus preferred, MP4 fallback
- Analyze button → SSE progress with inline validity banner (shows coverage % and cap early)
- **5 Sub-tabs after analysis:**

| Sub-tab | Content |
|---|---|
| Overview | Big score + validity badge (color-coded) + capReason box + overall feedback + dimension bars (hidden for catastrophic) + alignment stat chips + transcript reliability |
| Transcript | Diff view: correct (green), missing (red strikethrough), extra (gray parens), substitution (old→new), ASR confusion (purple ~word~) + "You said:" raw text |
| Per Unit | Per-sentence cards with status badge (Skipped/Partial/Complete/Too Short) + delivery dimension bars (suppressed for skipped) + AI coaching text |
| Top 5 Fixes | Numbered list, structured coaching language, no technical units |
| Audio Compare | "You" / "Target" / "Try This" clips; "Try This" only shown if score < 70 |

### Script Freeze Mechanism

When reference generation completes, `frozenScript = text.trim()` is set. `effectiveScript = frozenScript ?? text` is passed to Speech Lab. If the user edits the textarea afterward, a yellow warning banner appears. The server independently freezes via `sessionScripts.set(sessionId, text)` and uses the frozen version regardless of what the client submits.

---

## Python Prosody Analysis (`python/analyze_prosody.py`)

Called via Node.js `spawn()` with JSON on stdin, JSON on stdout. Requires `.venv` with librosa.

**Per-unit outputs:**
- `pitchMedianHz` — median F0 of voiced frames (pyin algorithm, fmin=60, fmax=500)
- `pitchRangeSemitones` — 90th–10th percentile of pitch in semitones
- `pitchSlope` — linear trend of F0 across the unit
- `rmsDbMean` / `rmsDbRange` — RMS energy in dB (relative to segment peak)
- `energySlope` — linear trend of energy
- `monotoneScore` — `pitch_range × 8`, capped 0–100 (higher = more expressive)
- `voicedFraction` — proportion of frames with detected pitch
- `speechChunkCount` — distinct speech bursts (amplitude envelope threshold)
- `pauseLabel` — human label for post-unit pause: "tiny beat" / "short breath" / "let it land" / "long pause" / "dead air"

Falls back to `{ quality: 'no_librosa' }` with an empty units array if import fails.

---

## Auto-Setup (`scripts/setup-analysis.js`)

Runs automatically as part of `npm run dev`. Fast path: skips if `.analysis-ready.json` exists and `.venv/bin/python3` exists and librosa is importable. Otherwise:

1. Creates `.venv` with `python3 -m venv`
2. Installs `numpy`, `scipy`, `librosa`, `soundfile`, `rapidfuzz` from `python/requirements.txt`
3. Verifies each package with `python3 -c "import X"`
4. Writes `.analysis-ready.json` with per-package booleans + `prosodyReady: true/false`

Non-fatal: server starts even if librosa fails. Expression scoring is simply skipped (`null` dimension).

---

## `/api/health/audio` Endpoint

`GET /api/health/audio` — reads `.analysis-ready.json` and returns:

```json
{
  "ffmpeg": true, "ffprobe": true,
  "python": true, "numpy": true, "scipy": true,
  "librosa": true, "soundfile": true, "rapidfuzz": true,
  "prosodyReady": true
}
```

The frontend checks this on mount and shows a setup warning if `prosodyReady` is false.

---

## Known Bugs Fixed

| Bug | Root Cause | Fix |
|---|---|---|
| Whisper 400 "Unrecognized file format" | Multer saves uploads without extension; Whisper uses filename to detect format | Added `MIME_TO_EXT` mapping + `fs.rename()` before calling Whisper |
| "Recording too short (0.0s)" on valid 29s Chrome recording | Chrome MediaRecorder WebM has no duration metadata in container header → ffprobe returns `"N/A"` → `parseFloat("N/A")` = NaN, which `?? '0'` doesn't catch | (a) Added `parseDur()` to filter non-finite values in `probeAudio()`; (b) Reordered `prepareAudioForAnalysis()` to convert→WAV first, then re-probe WAV if original duration was 0/NaN |
| `prosodyAnalyzer.js` stdin deadlock | Initial version used `execFile` with `input` option, which doesn't send stdin | Rewrote to use `spawn()` with `proc.stdin.write()` + `proc.stdin.end()` |
| Score 33/100 for a terrible attempt | Old `referenceComparator.js` averaged dimension scores with no coverage gate | Replaced entirely with `scoringEngine.js` — validity gate runs before any delivery scoring |

---

## npm Scripts

| Script | Command | Purpose |
|---|---|---|
| `npm run dev` | `node scripts/setup-analysis.js && node --watch server.js` | Dev server with auto-install + hot reload |
| `npm start` | `node server.js` | Production server |
| `npm run setup:analysis` | `node scripts/setup-analysis.js` | Bootstrap Python venv manually |
| `npm run test:speech-lab` | `node test/test-speech-lab.js` | Regression test: bad fixture → score ≤ 5 |
| `npm run doctor` | `node scripts/doctor.js` | Dependency health check |

---

## Regression Test (`test/test-speech-lab.js`)

Requires server running + `fixtures/bad_user_audio.webm` present (not committed). Submits the fixture against the TinyTrail script and asserts:

- `summary.overallScore ≤ 5`
- `summary.validity === 'catastrophic_script_mismatch'`
- `validityInfo.maxOverall ≤ 5`
- `feedback.top5Fixes[0]` mentions script completion
- At least 3 top fixes generated
- `alignment.stats.coverage < 0.50`

Skips gracefully if fixture is absent. Fails with a clear message if server is not running.

---

## Default Script — TinyTrail (~145 words)

The default textarea content that the whole pipeline is built and tuned around:

> *Today, we are excited to introduce TinyTrail, a new toy created for children who love to explore, imagine, and learn through play. TinyTrail is not just a toy you hand to a child. It is a little adventure box. Every piece is designed to help kids build stories, solve small challenges, and create their own world using their hands and imagination. In a time when children spend more and more time on screens, TinyTrail brings them back to real play. It helps develop creativity, focus, motor skills, and confidence—without making learning feel like learning. Parents get a toy they can trust. Children get a world they can control. TinyTrail is safe, colorful, durable, and made for endless play. Today, we are not just launching a toy. We are launching curiosity. TinyTrail. Small pieces. Big adventures.*

Whisper vocabulary hint includes all brand terms to reduce ASR confusion on "TinyTrail".

---

## What This POC Does NOT Include

- **No database** — sessions exist only in memory; restart clears all state
- **No auth** — single-user local tool
- **No mobile** — web only (localhost:8081)
- **No real-time feedback** — analysis runs after full recording, not while speaking
- **No multi-session persistence** — `sessionScripts` Map is in-process only
- **No CI** — standalone POC, not wired into the main vaani CI pipeline
- **No unit tests** — only the integration-style regression test (test-speech-lab.js)
- **No Android/iOS** — out of scope for this POC

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | required | All OpenAI calls (Whisper, TTS, GPT) |
| `OPENAI_TTS_MODEL` | `gpt-4o-mini-tts` | TTS model for reference generation |
| `OPENAI_TEXT_MODEL` | `gpt-4.1-mini` | Beat map + feedback generation |
| `PORT` | `8081` | Express server port |

---

## Future Work / Open Items

| Item | Priority | Notes |
|---|---|---|
| Real-time waveform display during recording | Medium | Canvas WebAudio API in RecordingPanel |
| Per-word highlighting in transcript (word timestamps) | High | Whisper returns word timestamps; could animate playback sync |
| Multi-session persistence (SQLite or Redis) | Low | In-memory is fine for POC |
| Mobile browser testing | Medium | Chrome mobile should work but untested |
| Doctor script (`scripts/doctor.js`) | Low | Referenced in package.json but not yet written |
| Android e2e | Low | Not a goal for this POC |
| Coverage baseline / CI integration | Low | Standalone POC intentionally excluded from main CI |
| Scoring calibration against real human recordings | High | The 145-word TinyTrail script needs a golden set of rated recordings |
| Expression scoring without librosa | Medium | Could use Whisper confidence scores as a proxy |
