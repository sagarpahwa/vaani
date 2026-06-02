import { execFile } from 'child_process';
import { promisify } from 'util';
import ffmpegPath from 'ffmpeg-static';

const execFileAsync = promisify(execFile);

async function ffmpegRun(args) {
  // ffmpeg always writes info to stderr
  const result = await execFileAsync(ffmpegPath, ['-y', ...args]).catch(e => e);
  return result.stderr || result.stdout || '';
}

function parseDuration(output) {
  const m = output.match(/Duration:\s*(\d+):(\d+):([\d.]+)/);
  if (!m) return 0;
  return parseInt(m[1]) * 3600 + parseInt(m[2]) * 60 + parseFloat(m[3]);
}

function parseVolumeDetect(output) {
  const meanM = output.match(/mean_volume:\s*([-\d.]+)\s*dB/);
  const maxM  = output.match(/max_volume:\s*([-\d.]+)\s*dB/);
  return {
    mean: meanM ? parseFloat(meanM[1]) : -30,
    max:  maxM  ? parseFloat(maxM[1])  : -20,
  };
}

function parseSilences(output, totalDuration) {
  const starts  = [...output.matchAll(/silence_start:\s*([\d.]+)/g)].map(m => parseFloat(m[1]));
  const ends    = [...output.matchAll(/silence_end:\s*([\d.]+)/g)].map(m => parseFloat(m[1]));
  let totalSilence = 0;
  const longPauses = [];

  starts.forEach((start, i) => {
    const end = ends[i] ?? totalDuration;
    const dur = end - start;
    totalSilence += dur;
    if (dur > 1.0) longPauses.push(Math.round(dur * 1000));
  });

  return { totalSilence, longPauses };
}

// Analyze a single segment WAV and return quality metrics for candidate selection
export async function analyzeSegment(wavPath) {
  const output = await ffmpegRun(['-i', wavPath, '-af', 'volumedetect', '-f', 'null', '-']);
  const duration = parseDuration(output);
  const { mean, max } = parseVolumeDetect(output);
  const dynamicRange = max - mean;

  return {
    durationSec: Math.round(duration * 100) / 100,
    meanVolumeDb: Math.round(mean * 10) / 10,
    maxVolumeDb: Math.round(max * 10) / 10,
    dynamicRangeDb: Math.round(dynamicRange * 10) / 10,
    isFlat: dynamicRange < 2.5,
    isClipping: max > -0.5,
    overallScore: Math.min(100, Math.max(0, Math.round(
      dynamicRange * 5.5 - (max > -0.5 ? 25 : 0)
    ))),
  };
}

// Analyze a complete take MP3 for the diagnostics panel
export async function analyzeFullTake(mp3Path, targetDurationSec = 85) {
  const volOutput = await ffmpegRun(['-i', mp3Path, '-af', 'volumedetect', '-f', 'null', '-']);
  const silOutput = await ffmpegRun([
    '-i', mp3Path,
    '-af', 'silencedetect=noise=-35dB:duration=0.15',
    '-f', 'null', '-',
  ]);

  const duration   = parseDuration(volOutput);
  const { mean, max } = parseVolumeDetect(volOutput);
  const dynamicRange  = max - mean;
  const { totalSilence, longPauses } = parseSilences(silOutput, duration);
  const speechRatio = duration > 0 ? (duration - totalSilence) / duration : 0;

  // Scoring
  const durationScore    = Math.max(0, 100 - Math.abs(duration - targetDurationSec) * 1.8);
  const longPauseScore   = Math.max(0, 100 - Math.max(0, longPauses.length - 8) * 7);
  const speechRatioScore = speechRatio >= 0.65 && speechRatio <= 0.80
    ? 100
    : speechRatio < 0.65
      ? (speechRatio / 0.65) * 100
      : Math.max(0, 100 - (speechRatio - 0.80) * 300);
  const dynamicScore = Math.min(100, dynamicRange * 5);

  const performanceScore = Math.round(
    durationScore * 0.25 + longPauseScore * 0.25 + speechRatioScore * 0.30 + dynamicScore * 0.20,
  );

  const warnings = [];
  if (duration > 100) warnings.push(`Duration ${Math.round(duration)}s is too long (target ≤ 95s)`);
  if (speechRatio < 0.60) warnings.push(`Speech ratio ${Math.round(speechRatio * 100)}% is too low (target 65–78%)`);
  if (longPauses.length > 12) warnings.push(`${longPauses.length} pauses over 1 s — reduce for naturalness (target 6–12)`);
  if (dynamicRange < 5) warnings.push(`Phrase-level dynamics are low (${dynamicRange.toFixed(1)} dB) — speech may sound flat`);

  return {
    durationSec: Math.round(duration),
    targetDurationSec,
    speechRatio: Math.round(speechRatio * 100),
    longPauseCount: longPauses.length,
    dynamicRangeDb: Math.round(dynamicRange * 10) / 10,
    performanceScore,
    warnings,
    breakdown: {
      durationScore:    Math.round(durationScore),
      longPauseScore:   Math.round(longPauseScore),
      speechRatioScore: Math.round(speechRatioScore),
      dynamicScore:     Math.round(dynamicScore),
    },
  };
}
