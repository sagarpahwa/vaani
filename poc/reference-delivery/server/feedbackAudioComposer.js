/**
 * Creates comparison audio clips for feedback:
 * - User's spoken clip for a unit
 * - Reference TTS clip for that unit (from the stored reference take)
 * - Corrected TTS clip generated on-demand with adjusted instructions
 *
 * Returns paths to audio files that get served as static assets.
 */

import { execFile } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs';
import OpenAI from 'openai';
import dotenv from 'dotenv';
import ffmpegPath from 'ffmpeg-static';
import { clipAudio } from './audioFeatureExtractor.js';
dotenv.config();

const execFileAsync = promisify(execFile);

const TTS_MODEL = process.env.OPENAI_TTS_MODEL  || 'gpt-4o-mini-tts';
const TTS_VOICE = process.env.OPENAI_PRIMARY_VOICE || 'marin';

function getClient() {
  return new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
}

/**
 * Convert any audio to a browser-safe MP3 for playback.
 */
async function toMp3(inputPath, outputPath) {
  await execFileAsync(ffmpegPath, [
    '-y', '-i', inputPath,
    '-ar', '44100', '-ac', '1',
    '-b:a', '96k',
    outputPath,
  ]);
}

/**
 * Extract user's clip for a unit and save as MP3.
 */
export async function extractUserClip(userAudioPath, start, end, outputDir, unitIndex) {
  if (start == null || end == null) return null;

  const wavPath = path.join(outputDir, `feedback_user_${unitIndex}.wav`);
  const mp3Path = path.join(outputDir, `feedback_user_${unitIndex}.mp3`);

  try {
    await clipAudio(userAudioPath, start, end, wavPath);
    await toMp3(wavPath, mp3Path);
    fs.unlinkSync(wavPath); // clean up raw wav
    return mp3Path;
  } catch (err) {
    console.warn(`[feedbackAudio] User clip ${unitIndex} failed:`, err.message);
    return null;
  }
}

/**
 * Copy reference unit audio from the stored reference take (already an MP3/WAV from TTS).
 * The reference wav is stored during generation in the session dir.
 */
export async function extractReferenceClip(refWavPath, outputDir, unitIndex) {
  if (!refWavPath || !fs.existsSync(refWavPath)) return null;
  const mp3Path = path.join(outputDir, `feedback_ref_${unitIndex}.mp3`);
  try {
    await toMp3(refWavPath, mp3Path);
    return mp3Path;
  } catch (err) {
    console.warn(`[feedbackAudio] Ref clip ${unitIndex} failed:`, err.message);
    return null;
  }
}

/**
 * Generate a corrected TTS clip with coaching-adjusted instructions.
 * Used to demonstrate what the unit should sound like given the user's weak dimension.
 */
export async function generateCorrectedClip(unit, comparison, outputDir, unitIndex) {
  if (!unit?.text) return null;

  const dim = comparison?.dimensions ?? {};
  const ref = comparison?.reference ?? {};

  // Build a corrective instruction based on the worst dimension
  const worst = Object.entries(dim)
    .filter(([, v]) => v != null)
    .sort(([, a], [, b]) => a - b)[0]?.[0];

  let correctionHint = '';
  if (worst === 'pace') {
    const idealWpm = ref.idealWpm ?? 130;
    correctionHint = `Speak at approximately ${idealWpm} words per minute. ${ref.paceContour?.includes('slow') ? 'Slow down deliberately.' : 'Keep a steady, purposeful pace.'}`;
  } else if (worst === 'energy') {
    const energyMid = ((ref.energyStart ?? 0.5) + (ref.energyEnd ?? 0.5)) / 2;
    correctionHint = energyMid > 0.65
      ? 'Project with full confidence — speak as if addressing a large room.'
      : 'Speak with quiet authority — measured, intimate, deliberate.';
  } else if (worst === 'expression') {
    correctionHint = 'Vary your pitch dramatically — rise on key words, drop at the end of statements. Never stay flat.';
  } else if (worst === 'pauses') {
    const ms = ref.pauseAfterMs ?? 500;
    correctionHint = ms > 1000
      ? `After this line, hold a ${(ms / 1000).toFixed(1)}-second silence to let it land.`
      : 'Use a brief pause after this line before continuing.';
  } else {
    correctionHint = 'Deliver with clarity and intention.';
  }

  const instruction = [
    unit.ttsInstruction ?? '',
    correctionHint,
    'This is the corrected model delivery for coaching purposes.',
  ].filter(Boolean).join(' ');

  const outputPath = path.join(outputDir, `feedback_corrected_${unitIndex}.mp3`);

  try {
    const openai = getClient();
    const response = await openai.audio.speech.create({
      model:        TTS_MODEL,
      voice:        TTS_VOICE,
      input:        unit.text,
      instructions: instruction.slice(0, 500),
      response_format: 'mp3',
    });

    const buffer = Buffer.from(await response.arrayBuffer());
    fs.writeFileSync(outputPath, buffer);
    return outputPath;
  } catch (err) {
    console.warn(`[feedbackAudio] Corrected TTS ${unitIndex} failed:`, err.message);
    return null;
  }
}

/**
 * Main export: build all feedback audio clips for a session.
 * Only generates clips for the worst N units (by overall score) to save API calls.
 *
 * @param {string} userAudioPath    - user's uploaded audio
 * @param {Array}  unitComparisons  - from referenceComparator
 * @param {Array}  unitWindows      - [{index, start, end}] aligned time windows
 * @param {object} refWavByUnit     - Map of unitIndex → reference wav path (from TTS generation)
 * @param {Array}  performanceUnits - beat map units
 * @param {string} outputDir        - where to write clips
 * @param {number} topN             - how many units to generate clips for (default 5)
 * @returns {Map<number, {user, reference, corrected}>} unitIndex → clip paths
 */
export async function buildFeedbackAudio(
  userAudioPath, unitComparisons, unitWindows, refWavByUnit,
  performanceUnits, outputDir, topN = 5
) {
  fs.mkdirSync(outputDir, { recursive: true });

  // Pick worst N units (scored, not skipped)
  const scored = unitComparisons
    .filter(u => !u.skipped && u.overall != null)
    .sort((a, b) => (a.overall ?? 100) - (b.overall ?? 100))
    .slice(0, topN);

  const winByIndex  = new Map(unitWindows.map(w => [w.index, w]));
  const unitByIndex = new Map(performanceUnits.map(u => [u.index, u]));

  const clips = new Map();

  await Promise.all(scored.map(async (comp) => {
    const idx  = comp.unitIndex;
    const win  = winByIndex.get(idx);
    const unit = unitByIndex.get(idx);

    const [userClip, refClip, correctedClip] = await Promise.all([
      win ? extractUserClip(userAudioPath, win.start, win.end, outputDir, idx) : Promise.resolve(null),
      refWavByUnit?.get(idx) ? extractReferenceClip(refWavByUnit.get(idx), outputDir, idx) : Promise.resolve(null),
      unit ? generateCorrectedClip(unit, comp, outputDir, idx) : Promise.resolve(null),
    ]);

    clips.set(idx, {
      user:      userClip,
      reference: refClip,
      corrected: correctedClip,
    });
  }));

  return clips;
}

/**
 * Convert Map to a plain object keyed by unitIndex for JSON serialization.
 * Replaces absolute paths with relative URL paths.
 */
export function serializeClips(clips, baseDir, urlPrefix) {
  const out = {};
  for (const [idx, paths] of clips.entries()) {
    const rel = (p) => {
      if (!p) return null;
      const rel = path.relative(baseDir, p);
      return `${urlPrefix}/${rel}`;
    };
    out[idx] = {
      user:      rel(paths.user),
      reference: rel(paths.reference),
      corrected: rel(paths.corrected),
    };
  }
  return out;
}
