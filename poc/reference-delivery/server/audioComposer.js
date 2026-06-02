import { execFile } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs/promises';
import ffmpegPath from 'ffmpeg-static';

const execFileAsync = promisify(execFile);
const SAMPLE_RATE = 24000;

async function runFfmpeg(args) {
  await execFileAsync(ffmpegPath, ['-y', ...args]).catch(err => {
    throw new Error(`ffmpeg error: ${err.stderr || err.message}`);
  });
}

// Cache silence WAVs by duration within a session (avoids regenerating the same silence)
const silenceCache = new Map();

async function getSilenceWav(sessionDir, durationMs) {
  if (!durationMs || durationMs <= 0) return null;

  const key = `${sessionDir}|${durationMs}`;
  if (silenceCache.has(key)) return silenceCache.get(key);

  const silPath = path.join(sessionDir, `sil_${durationMs}ms.wav`);
  await runFfmpeg([
    '-f', 'lavfi',
    '-i', `anullsrc=channel_layout=mono:sample_rate=${SAMPLE_RATE}`,
    '-t', String(durationMs / 1000),
    '-acodec', 'pcm_s16le',
    '-ar', String(SAMPLE_RATE),
    '-ac', '1',
    silPath,
  ]);
  silenceCache.set(key, silPath);
  return silPath;
}

// Enforce pause budget: no more than maxLongPauses units with pauseAfterMs > 1000ms
export function enforcePauseRules(units, maxLongPauses = 8) {
  const processed = units.map(u => ({ ...u }));

  // Cap absolute maximum
  for (const u of processed) {
    if ((u.pauseAfterMs || 0) > 2200) u.pauseAfterMs = 2200;
    if ((u.pauseAfterMs || 0) > 0 && (u.pauseAfterMs || 0) < 200) u.pauseAfterMs = 200;
  }

  // Count long pauses and reduce excess
  const longOnes = processed
    .filter(u => (u.pauseAfterMs || 0) > 1000)
    .sort((a, b) => (b.pauseAfterMs || 0) - (a.pauseAfterMs || 0));

  if (longOnes.length > maxLongPauses) {
    const toReduce = longOnes.slice(maxLongPauses);
    for (const u of toReduce) {
      u.pauseAfterMs = Math.max(600, Math.round((u.pauseAfterMs || 1000) * 0.55));
    }
  }

  // Prevent two identical consecutive pauses
  for (let i = 1; i < processed.length; i++) {
    if (processed[i].pauseAfterMs === processed[i - 1].pauseAfterMs && processed[i].pauseAfterMs > 400) {
      processed[i].pauseAfterMs = Math.round(processed[i].pauseAfterMs * 0.85);
    }
  }

  return processed;
}

export async function composeAudio(sessionDir, units, style) {
  const safeUnits = enforcePauseRules(units);
  const fileList = [];

  for (const unit of safeUnits) {
    fileList.push(unit.wavPath);
    if (unit.pauseAfterMs > 0) {
      const sil = await getSilenceWav(sessionDir, unit.pauseAfterMs);
      if (sil) fileList.push(sil);
    }
  }

  const listContent = fileList.map(f => `file '${f}'`).join('\n');
  const listPath = path.join(sessionDir, `concat_${style}.txt`);
  await fs.writeFile(listPath, listContent, 'utf8');

  const outputPath = path.join(sessionDir, `combined_${style}.wav`);
  await runFfmpeg([
    '-f', 'concat',
    '-safe', '0',
    '-i', listPath,
    '-acodec', 'pcm_s16le',
    '-ar', String(SAMPLE_RATE),
    '-ac', '1',
    outputPath,
  ]);

  return outputPath;
}
