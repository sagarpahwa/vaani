/**
 * Extracts per-unit acoustic features from a WAV/MP3 file using ffmpeg.
 * Given an alignment (from transcriptAligner) and the original whisper words,
 * extracts timing, loudness, pause, and basic prosody features for each unit.
 */

import { execFile } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs';
import ffmpegPath from 'ffmpeg-static';

const execFileAsync = promisify(execFile);

/**
 * Clip audio from audioPath between start..end seconds.
 * Returns the output clip path (WAV, 16kHz mono).
 */
export async function clipAudio(audioPath, start, end, outputPath) {
  const duration = end - start;
  if (duration <= 0.05) throw new Error(`Clip too short: ${duration}s`);

  await execFileAsync(ffmpegPath, [
    '-y',
    '-i', audioPath,
    '-ss', String(start),
    '-t', String(duration),
    '-ar', '16000',
    '-ac', '1',
    '-f', 'wav',
    outputPath,
  ]);
  return outputPath;
}

/**
 * Run ffmpeg volumedetect on a WAV clip.
 * Returns { meanVolumeDb, maxVolumeDb, dynamicRangeDb }.
 */
async function volumeDetect(wavPath) {
  const { stderr } = await execFileAsync(ffmpegPath, [
    '-i', wavPath,
    '-af', 'volumedetect',
    '-vn', '-sn', '-dn',
    '-f', 'null', '-',
  ]).catch(e => ({ stderr: e.stderr ?? '' }));

  const mean = parseFloat(stderr.match(/mean_volume:\s*([-\d.]+)/)?.[1] ?? '0');
  const max  = parseFloat(stderr.match(/max_volume:\s*([-\d.]+)/)?.[1] ?? '0');
  return {
    meanVolumeDb:   mean,
    maxVolumeDb:    max,
    dynamicRangeDb: Math.abs(max - mean),
  };
}

/**
 * Run ffmpeg silencedetect on a WAV clip.
 * Returns array of { silenceStart, silenceEnd, silenceDuration }.
 */
async function silenceDetect(wavPath, noiseDb = -40, minDuration = 0.1) {
  const filter = `silencedetect=noise=${noiseDb}dB:duration=${minDuration}`;
  const { stderr } = await execFileAsync(ffmpegPath, [
    '-i', wavPath,
    '-af', filter,
    '-vn', '-sn', '-dn',
    '-f', 'null', '-',
  ]).catch(e => ({ stderr: e.stderr ?? '' }));

  const silences = [];
  const startRe  = /silence_start:\s*([\d.]+)/g;
  const endRe    = /silence_end:\s*([\d.]+)\s*\|\s*silence_duration:\s*([\d.]+)/g;

  let sm, em;
  const starts = [];
  while ((sm = startRe.exec(stderr)) !== null) starts.push(parseFloat(sm[1]));
  let idx = 0;
  while ((em = endRe.exec(stderr)) !== null) {
    silences.push({
      silenceStart:    starts[idx] ?? 0,
      silenceEnd:      parseFloat(em[1]),
      silenceDuration: parseFloat(em[2]),
    });
    idx++;
  }
  return silences;
}

/**
 * Get audio duration via ffprobe.
 */
async function getAudioDuration(audioPath) {
  const { stdout } = await execFileAsync(ffmpegPath.replace('ffmpeg', 'ffprobe'), [
    '-v', 'error',
    '-show_entries', 'format=duration',
    '-of', 'default=noprint_wrappers=1:nokey=1',
    audioPath,
  ]).catch(() => ({ stdout: '0' }));
  return parseFloat(stdout.trim()) || 0;
}

/**
 * Extract features for a single time window from the audio file.
 * Does NOT require librosa — pure ffmpeg.
 */
async function extractWindowFeatures(audioPath, start, end, sessionDir, unitIndex) {
  const clipPath = path.join(sessionDir, `user_clip_${unitIndex}.wav`);

  let clipped = false;
  try {
    await clipAudio(audioPath, start, end, clipPath);
    clipped = true;
  } catch {
    return { unitIndex, tooShort: true, start, end };
  }

  const [volume, silences] = await Promise.all([
    volumeDetect(clipPath),
    silenceDetect(clipPath),
  ]);

  const duration = end - start;
  const totalSilence = silences.reduce((acc, s) => acc + s.silenceDuration, 0);
  const speechDuration = Math.max(0, duration - totalSilence);
  const speechRatio = duration > 0 ? speechDuration / duration : 0;

  // Pace estimate: words spoken in segment / speech time (words/min)
  // We don't have per-word count here — caller fills this in from alignment
  const pauseCount = silences.filter(s => s.silenceDuration >= 0.3).length;

  return {
    unitIndex,
    start:          round(start),
    end:            round(end),
    durationSec:    round(duration),
    meanVolumeDb:   round(volume.meanVolumeDb),
    maxVolumeDb:    round(volume.maxVolumeDb),
    dynamicRangeDb: round(volume.dynamicRangeDb),
    speechRatio:    round(speechRatio),
    silences,
    pauseCount,
    clipPath,
    tooShort:       false,
  };
}

function round(n, decimals = 3) {
  return Math.round(n * 10 ** decimals) / 10 ** decimals;
}

/**
 * Main export: extracts per-unit features from user audio.
 *
 * @param {string} userAudioPath  - path to user's uploaded audio (wav/webm/mp4)
 * @param {Array}  unitWindows    - [{index, start, end}] time windows from getUnitTimeWindow
 * @param {Array}  alignmentOps   - full operations array from alignTranscripts (for word counts)
 * @param {string} sessionDir     - temp dir for clip files
 * @returns {Array} per-unit feature objects
 */
export async function extractUserFeatures(userAudioPath, unitWindows, alignmentOps, sessionDir) {
  // Convert to 16kHz mono WAV for analysis if needed
  const workPath = path.join(sessionDir, 'user_work.wav');
  await execFileAsync(ffmpegPath, [
    '-y',
    '-i', userAudioPath,
    '-ar', '16000',
    '-ac', '1',
    '-f', 'wav',
    workPath,
  ]);

  // Build a word-count lookup per unit from alignment ops
  // alignment ops have ei (expected word index) — group by unit
  // We'll attach word counts after feature extraction

  const results = await Promise.all(
    unitWindows.map(async (win) => {
      if (win.start == null || win.end == null) {
        return { unitIndex: win.index, noTimestamp: true };
      }
      const features = await extractWindowFeatures(
        workPath, win.start, win.end, sessionDir, win.index
      );
      return features;
    })
  );

  return results;
}

/**
 * Compute pace (words/min) for a unit given word count and duration.
 */
export function computePace(wordCount, speechDurationSec) {
  if (speechDurationSec <= 0 || wordCount <= 0) return 0;
  return Math.round((wordCount / speechDurationSec) * 60);
}

/**
 * Find leading and trailing silence in a clip (entry/exit pause).
 */
export function getLeadTrailSilence(silences, totalDuration) {
  const lead  = silences.find(s => s.silenceStart < 0.05)?.silenceDuration ?? 0;
  const trail = [...silences].reverse().find(s => s.silenceEnd >= totalDuration - 0.1)?.silenceDuration ?? 0;
  return { leadSilenceSec: round(lead), trailSilenceSec: round(trail) };
}
