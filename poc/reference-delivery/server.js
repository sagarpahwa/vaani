import express from 'express';
import { v4 as uuidv4 } from 'uuid';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs/promises';
import fsSync from 'fs';
import multer from 'multer';

// ── Reference generation pipeline ────────────────────────────────────
import { generateBeatMap, TAKE_CONFIGS } from './server/performanceDirector.js';
import { generatePerformanceUnit } from './server/ttsGenerator.js';
import { composeAudio } from './server/audioComposer.js';
import { masterAudio } from './server/audioMastering.js';
import { analyzeFullTake } from './server/acousticEvaluator.js';

// ── Speech Lab analysis pipeline ──────────────────────────────────────
import { prepareAudioForAnalysis } from './server/audioConverter.js';
import { transcribeAudio } from './server/transcriptionService.js';
import {
  alignTranscripts, getUnitTimeWindow, mapUnitsToExpectedWordRanges, getUnitOps,
} from './server/transcriptAligner.js';
import { extractUserFeatures, computePace, getLeadTrailSilence } from './server/audioFeatureExtractor.js';
import { analyzeProsody, mergeProsodyIntoFeatures, isProsodyReady } from './server/prosodyAnalyzer.js';
import { computeValidity, scoreUnit, buildSessionSummary } from './server/scoringEngine.js';
import { generateAllFeedback, buildOverviewMessage } from './server/coachingFeedback.js';
import { buildFeedbackAudio } from './server/feedbackAudioComposer.js';

dotenv.config();

const __dirname     = path.dirname(fileURLToPath(import.meta.url));
const app           = express();
const PORT          = process.env.PORT || 8081;
const GENERATED_DIR = path.join(__dirname, 'generated');
const UPLOADS_DIR   = path.join(__dirname, 'uploads');
const READY_FILE    = path.join(__dirname, '.analysis-ready.json');

await fs.mkdir(GENERATED_DIR, { recursive: true });
await fs.mkdir(UPLOADS_DIR,   { recursive: true });

app.use(express.json({ limit: '2mb' }));
app.use(express.static(path.join(__dirname, 'public')));
app.use('/generated', express.static(GENERATED_DIR));

// Multer — accept any audio, up to 50 MB
const upload = multer({
  dest: UPLOADS_DIR,
  limits: { fileSize: 50 * 1024 * 1024 },
  fileFilter: (_req, _file, cb) => cb(null, true),
});

// In-memory store: sessionId → frozen expected script
const sessionScripts = new Map();

const TAKE_ORDER = ['restrained', 'emotional', 'launch'];

function withConcurrency(items, fn, limit = 2) {
  const results = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const i = next++;
      results[i] = await fn(items[i], i);
    }
  }
  return Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker))
    .then(() => results);
}

// ── Core reference generation pipeline ───────────────────────────────

async function generateOneTake({ text, voice, style, emphasisBoost = false, sessionDir, push, takeIndex, takeTotal }) {
  const takeName = TAKE_CONFIGS[style].name;

  push('progress', { step: `Directing performance · beat map for ${takeName}…`, phase: 'beat_map', takeIndex, takeTotal });
  const beatMap = await generateBeatMap(text, style, emphasisBoost);
  const units   = beatMap.performanceUnits ?? [];
  push('beat_map_done', { takeIndex, takeName, unitCount: units.length, overallArc: beatMap.overallDirection?.emotionArc });

  const totalUnits = units.length;
  push('progress', { step: `Generating ${totalUnits} performance units for ${takeName}…`, phase: 'tts', takeIndex, takeTotal, segmentTotal: totalUnits });

  let completed = 0;
  const unitsWithAudio = await withConcurrency(units, async (unit) => {
    const result = await generatePerformanceUnit(unit, voice, sessionDir, unit.index);
    completed++;
    push('segment_done', { takeIndex, completed, total: totalUnits, variant: result.selectedVariant });
    return { ...unit, ...result };
  }, 2);

  push('progress', { step: `Composing audio for ${takeName}…`, phase: 'compose', takeIndex, takeTotal });
  const combinedWav = await composeAudio(sessionDir, unitsWithAudio, style);

  push('progress', { step: `Mastering final audio for ${takeName}…`, phase: 'master', takeIndex, takeTotal });
  const mp3File = `take_${style}.mp3`;
  const mp3Path = path.join(sessionDir, mp3File);
  await masterAudio(combinedWav, mp3Path);

  const diagnostics = await analyzeFullTake(mp3Path, beatMap.targetDurationSec ?? 85);

  // Save manifest (beat map + unit wavs) for analysis lookups
  try {
    const manifest = {
      text, style, beatMap,
      unitWavPaths: Object.fromEntries(unitsWithAudio.map(u => [u.index, u.wavPath])),
    };
    await fs.writeFile(path.join(sessionDir, `manifest_${style}.json`), JSON.stringify(manifest, null, 2));
  } catch { /* non-fatal */ }

  return {
    style, name: takeName, beatMap,
    audioUrl:   `/generated/${path.basename(sessionDir)}/${mp3File}`,
    unitCount:  totalUnits,
    diagnostics,
    candidateStats: unitsWithAudio.map(u => u.candidateScores),
  };
}

// ── GET /api/health/audio ─────────────────────────────────────────────

app.get('/api/health/audio', (_req, res) => {
  let status = {
    ffmpeg: true, ffprobe: true,
    python: false, numpy: false, scipy: false, librosa: false, soundfile: false, rapidfuzz: false,
    prosodyReady: false,
  };
  try {
    if (fsSync.existsSync(READY_FILE)) {
      const raw = JSON.parse(fsSync.readFileSync(READY_FILE, 'utf8'));
      status = { ...status, ...raw };
    }
  } catch { /* return defaults */ }
  res.json(status);
});

// ── POST /api/generate ────────────────────────────────────────────────

app.post('/api/generate', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.flushHeaders();

  const push = (event, data) => res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  const { text, voice = 'marin', mode = 'emotional', takeCount = 1 } = req.body ?? {};

  if (!text?.trim())               { push('error', { message: 'Text is required.' }); return res.end(); }
  if (text.length > 2500)          { push('error', { message: `Text must be ≤ 2500 chars.` }); return res.end(); }
  if (!process.env.OPENAI_API_KEY) { push('error', { message: 'OPENAI_API_KEY not set.' }); return res.end(); }

  const styles     = takeCount >= 3 ? TAKE_ORDER : [mode];
  const sessionId  = uuidv4();
  const sessionDir = path.join(GENERATED_DIR, sessionId);
  await fs.mkdir(sessionDir, { recursive: true });

  // Freeze the expected script for this session
  sessionScripts.set(sessionId, text.trim());

  const takes = [];
  try {
    for (let ti = 0; ti < styles.length; ti++) {
      const take = await generateOneTake({
        text, voice, style: styles[ti], emphasisBoost: false,
        sessionDir, push, takeIndex: ti, takeTotal: styles.length,
      });
      takes.push(take);
      push('take_done', { takeIndex: ti, style: take.style, takeName: take.name, audioUrl: take.audioUrl, diagnostics: take.diagnostics });
    }
    push('complete', {
      sessionId, takes, voice,
      model:          process.env.OPENAI_TTS_MODEL  || 'gpt-4o-mini-tts',
      textModel:      process.env.OPENAI_TEXT_MODEL || 'gpt-4.1-mini',
      generatedFiles: takes.map(t => t.audioUrl),
    });
  } catch (err) {
    console.error('[generate error]', err?.message ?? err);
    await fs.rm(sessionDir, { recursive: true, force: true }).catch(() => {});
    push('error', { message: err.message || 'Generation failed.' });
  } finally {
    res.end();
  }
});

// ── POST /api/regenerate ──────────────────────────────────────────────

app.post('/api/regenerate', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.flushHeaders();

  const push = (event, data) => res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  const { text, voice = 'marin', style = 'emotional' } = req.body ?? {};

  if (!text?.trim())               { push('error', { message: 'Text is required.' }); return res.end(); }
  if (!process.env.OPENAI_API_KEY) { push('error', { message: 'OPENAI_API_KEY not set.' }); return res.end(); }

  const sessionId  = uuidv4();
  const sessionDir = path.join(GENERATED_DIR, sessionId);
  await fs.mkdir(sessionDir, { recursive: true });

  try {
    const take = await generateOneTake({
      text, voice, style, emphasisBoost: true,
      sessionDir, push, takeIndex: 0, takeTotal: 1,
    });
    push('take_done', { takeIndex: 0, style: take.style, takeName: take.name, audioUrl: take.audioUrl, diagnostics: take.diagnostics });
    push('complete', {
      sessionId, takes: [take], voice,
      model:          process.env.OPENAI_TTS_MODEL  || 'gpt-4o-mini-tts',
      textModel:      process.env.OPENAI_TEXT_MODEL || 'gpt-4.1-mini',
      generatedFiles: [take.audioUrl],
    });
  } catch (err) {
    console.error('[regenerate error]', err?.message ?? err);
    await fs.rm(sessionDir, { recursive: true, force: true }).catch(() => {});
    push('error', { message: err.message || 'Regeneration failed.' });
  } finally {
    res.end();
  }
});

// ── POST /api/analyze-user-speech ─────────────────────────────────────
// Accepts: multipart form: `audio` file + fields: `script`, `sessionId`, `style`
// Returns: SSE stream → complete event with full gated-scoring analysis

app.post('/api/analyze-user-speech', upload.single('audio'), async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.flushHeaders();

  const push = (event, data) => res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);

  const audioFile = req.file;
  const { script: rawScript, sessionId, style = 'emotional' } = req.body ?? {};

  if (!audioFile)               { push('error', { message: 'No audio file uploaded.' });   return res.end(); }
  if (!rawScript?.trim())       { push('error', { message: 'script field is required.' }); return res.end(); }
  if (!process.env.OPENAI_API_KEY) { push('error', { message: 'OPENAI_API_KEY not set.' }); return res.end(); }

  // Use frozen script if available (prevents analyzing against edited text)
  const script = (sessionId && sessionScripts.get(sessionId)) ?? rawScript.trim();

  // Block if prosody is not ready
  const prosodyOk = isProsodyReady();
  if (!prosodyOk) {
    // Non-blocking: proceed with reduced scoring (no expression dimension)
    console.warn('[analyze] Prosody not ready — proceeding without pitch analysis');
  }

  // Load beat map from manifest
  let beatMap      = null;
  let refWavByUnit = null;
  if (sessionId) {
    const manifestPath = path.join(GENERATED_DIR, sessionId, `manifest_${style}.json`);
    try {
      const mf  = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
      beatMap     = mf.beatMap;
      refWavByUnit = new Map(Object.entries(mf.unitWavPaths ?? {}).map(([k, v]) => [Number(k), v]));
    } catch { /* no manifest */ }
  }

  const performanceUnits = beatMap?.performanceUnits ?? [];
  const analysisId       = uuidv4();
  const analysisDir      = path.join(GENERATED_DIR, analysisId);
  await fs.mkdir(analysisDir, { recursive: true });

  // Rename multer file to have proper extension for Whisper
  const MIME_TO_EXT = {
    'audio/webm': '.webm', 'audio/ogg': '.ogg',
    'audio/mp4': '.mp4',   'audio/x-m4a': '.mp4', 'audio/m4a': '.mp4',
    'audio/mpeg': '.mp3',  'audio/mp3': '.mp3',
    'audio/wav': '.wav',   'audio/wave': '.wav',
    'audio/flac': '.flac',
  };
  const ext         = MIME_TO_EXT[audioFile.mimetype] ?? '.webm';
  const uploadedPath = audioFile.path + ext;
  await fs.rename(audioFile.path, uploadedPath);

  try {
    // ── 1. Validate + convert to clean WAV ─────────────────────────
    push('progress', { step: 'Validating and converting audio…', phase: 'convert', pct: 6 });
    const { wavPath, probe } = await prepareAudioForAnalysis(uploadedPath, analysisDir, 'user_audio');
    push('audio_ready', { duration: probe.duration, codec: probe.codec, sampleRate: probe.sampleRate });

    // ── 2. Transcribe (use clean WAV) ──────────────────────────────
    push('progress', { step: 'Transcribing your recording…', phase: 'transcribe', pct: 15 });
    const transcription = await transcribeAudio(wavPath);
    push('transcription_done', { text: transcription.text, wordCount: transcription.words.length, quality: transcription.quality });

    // ── 3. Align ───────────────────────────────────────────────────
    push('progress', { step: 'Aligning your words to the script…', phase: 'align', pct: 27 });
    const alignment = alignTranscripts(script, transcription.text, transcription.words);

    // ── 4. EARLY GATE: compute validity BEFORE expensive analysis ──
    const validityInfo = computeValidity(alignment.stats);
    push('validity_check', {
      validity:   validityInfo.validity,
      coverage:   Math.round(validityInfo.coverage * 100),
      maxOverall: validityInfo.maxOverall,
      capReason:  validityInfo.capReason,
    });

    // ── 5. Map units to time windows ────────────────────────────────
    let unitWindows = [];
    let unitRanges  = [];
    if (performanceUnits.length > 0) {
      unitRanges  = mapUnitsToExpectedWordRanges(performanceUnits);
      unitWindows = unitRanges.map(r => ({
        index:    r.index,
        expStart: r.expStart,
        expEnd:   r.expEnd,
        wordCount: r.expEnd - r.expStart + 1,
        ...getUnitTimeWindow(r.expStart, r.expEnd, alignment),
      }));
    } else {
      unitWindows = [{ index: 0, expStart: 0, expEnd: alignment.expectedWords.length - 1, wordCount: alignment.expectedWords.length, start: null, end: null }];
      unitRanges  = [{ index: 0, expStart: 0, expEnd: alignment.expectedWords.length - 1 }];
    }
    const rangeByIndex = new Map(unitRanges.map(r => [r.index, r]));
    const winByIndex   = new Map(unitWindows.map(w => [w.index, w]));

    // ── 6. Acoustic features (skip if catastrophic) ─────────────────
    push('progress', { step: 'Extracting acoustic features…', phase: 'features', pct: 40 });
    let enrichedFeatures = [];
    if (validityInfo.validity !== 'catastrophic_script_mismatch') {
      const rawFeatures = await extractUserFeatures(wavPath, unitWindows, alignment.operations, analysisDir);
      const features = rawFeatures.map(f => {
        if (f.tooShort || f.noTimestamp) return f;
        const win       = winByIndex.get(f.unitIndex);
        const speechDur = f.durationSec * (f.speechRatio ?? 1);
        const wpm       = computePace(win?.wordCount ?? 0, speechDur);
        const { trailSilenceSec } = getLeadTrailSilence(f.silences ?? [], f.durationSec);
        return { ...f, wpm, trailSilenceSec };
      });

      // ── 7. Prosody ───────────────────────────────────────────────
      push('progress', { step: 'Analyzing pitch and expression…', phase: 'prosody', pct: 55 });
      const validWindows = unitWindows.filter(w => w.start != null && w.end != null);
      const prosodyResult = prosodyOk
        ? await analyzeProsody(wavPath, validWindows)
        : { quality: 'no_librosa', units: [] };
      push('prosody_done', { quality: prosodyResult.quality });
      enrichedFeatures = mergeProsodyIntoFeatures(features, prosodyResult.units ?? []);
    } else {
      // Catastrophic: create minimal feature stubs (no acoustic analysis needed)
      enrichedFeatures = unitWindows.map(w => ({ unitIndex: w.index, noTimestamp: true }));
      push('prosody_done', { quality: 'skipped_catastrophic' });
    }

    // ── 8. Hard-gated scoring ───────────────────────────────────────
    push('progress', { step: 'Computing scores…', phase: 'score', pct: 65 });
    const featureByUnit = new Map(enrichedFeatures.map(f => [f.unitIndex, f]));
    const unitByIdx     = new Map(performanceUnits.map(u => [u.index, u]));

    const unitScores = unitWindows.map(win => {
      const unit    = unitByIdx.get(win.index) ?? { index: win.index, text: '', paceContour: 'medium', energyStart: 0.5, energyEnd: 0.5, pauseAfterMs: 0 };
      const feature = featureByUnit.get(win.index);
      const range   = rangeByIndex.get(win.index);
      const unitOps = range ? getUnitOps(alignment.operations, range.expStart, range.expEnd) : [];
      return scoreUnit(feature, unit, unitOps, validityInfo);
    });

    const summary = buildSessionSummary(unitScores, validityInfo, alignment.stats, prosodyOk);

    // ── 9. Coaching feedback ────────────────────────────────────────
    push('progress', { step: 'Generating coaching feedback…', phase: 'feedback', pct: 76 });
    const feedback = await generateAllFeedback(
      performanceUnits, unitScores, summary, alignment.operations, alignment.stats, validityInfo
    );

    // ── 10. Comparison audio clips (top 5 worst units) ──────────────
    push('progress', { step: 'Creating comparison audio clips…', phase: 'audio_clips', pct: 90 });
    const audioClips = {};
    if (validityInfo.validity !== 'catastrophic_script_mismatch') {
      try {
        // Map unitScores to unitComparisons-compatible format for feedbackAudioComposer
        const compatComparisons = unitScores.map(s => ({
          unitIndex: s.unitIndex, unitText: s.unitText, overall: s.overall,
          skipped: s.unitStatus === 'mostly_skipped',
          dimensions: s.dimensions ?? {},
        }));
        const clips = await buildFeedbackAudio(
          wavPath, compatComparisons, unitWindows, refWavByUnit, performanceUnits, analysisDir, 5
        );
        for (const [idx, c] of clips.entries()) {
          audioClips[idx] = {};
          for (const [k, v] of Object.entries(c)) {
            audioClips[idx][k] = v ? `/generated/${analysisId}/${path.basename(v)}` : null;
          }
        }
      } catch (clipErr) {
        console.warn('[analyze] Audio clips failed:', clipErr.message);
      }
    }

    // Clean up uploads
    await fs.unlink(uploadedPath).catch(() => {});

    push('complete', {
      analysisId,
      transcript: { text: transcription.text, quality: transcription.quality, warning: transcription.warning },
      alignment:  {
        accuracy: alignment.accuracy,
        stats:    alignment.stats,
        operations: alignment.operations,
        transcriptReliability: alignment.transcriptReliability,
      },
      validityInfo,
      summary,
      unitScores,
      feedback,
      audioClips,
      prosodyReady: prosodyOk,
    });

  } catch (err) {
    console.error('[analyze error]', err?.message ?? err);
    await fs.unlink(uploadedPath).catch(() => {});
    push('error', { message: err.message || 'Analysis failed.' });
  } finally {
    res.end();
  }
});

app.listen(PORT, () => {
  console.log(`\n  Vaani Reference Delivery POC`);
  console.log(`  → http://localhost:${PORT}\n`);
});
