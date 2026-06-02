/**
 * Central audio conversion utility.
 * Converts any browser-recorded audio (WebM/Opus, MP4/AAC, OGG, WAV)
 * to a clean 16kHz mono PCM WAV suitable for Whisper and librosa.
 */
import { execFile } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import ffmpegPath from 'ffmpeg-static';

const execFileAsync = promisify(execFile);

// Use system ffprobe (available via homebrew/apt on dev machines)
// If system ffprobe missing, ffmpeg itself can do duration detection as fallback
const FFPROBE = 'ffprobe';

/**
 * Probe an audio file with ffprobe.
 * Returns { duration, codec, sampleRate, channels, format }.
 * Throws a descriptive error if ffprobe fails.
 */
export async function probeAudio(filePath) {
  let stdout;
  try {
    ({ stdout } = await execFileAsync(FFPROBE, [
      '-v', 'quiet',
      '-print_format', 'json',
      '-show_format',
      '-show_streams',
      filePath,
    ]));
  } catch (err) {
    // Fallback: use ffmpeg to get duration via stderr
    try {
      const { stderr } = await execFileAsync(ffmpegPath, [
        '-i', filePath, '-f', 'null', '-',
      ]).catch(e => ({ stderr: e.stderr ?? '' }));
      const dur = parseFloat(stderr.match(/Duration:\s*(\d+):(\d+):([\d.]+)/)?.[3] ?? '0');
      return { duration: dur, codec: 'unknown', sampleRate: 0, channels: 1, format: 'unknown', bitRate: 0 };
    } catch {
      throw new Error(`Cannot read audio file. Ensure it is a valid browser recording.`);
    }
  }

  const info   = JSON.parse(stdout);
  const audio  = info.streams?.find(s => s.codec_type === 'audio');
  if (!audio) throw new Error('No audio stream found in uploaded file.');

  // Chrome MediaRecorder WebM files report duration as "N/A" in the container.
  // parseFloat("N/A") = NaN; filter those out so the fallback chain works.
  const parseDur = v => { const n = parseFloat(v); return isFinite(n) && n > 0 ? n : null; };

  return {
    duration:   parseDur(info.format?.duration) ?? parseDur(audio.duration) ?? 0,
    codec:      audio.codec_name ?? 'unknown',
    sampleRate: parseInt(audio.sample_rate ?? '0', 10),
    channels:   audio.channels ?? 1,
    format:     info.format?.format_name ?? 'unknown',
    bitRate:    parseInt(info.format?.bit_rate ?? '0', 10),
  };
}

/**
 * Convert any audio to clean 16kHz mono PCM WAV.
 * This is the canonical format for all analysis (Whisper + librosa).
 */
export async function convertToWav(inputPath, outputPath) {
  await execFileAsync(ffmpegPath, [
    '-y',
    '-i',  inputPath,
    '-ar', '16000',
    '-ac', '1',
    '-c:a', 'pcm_s16le',
    '-vn',
    outputPath,
  ]);
  return outputPath;
}

/**
 * Validate audio probe result. Throws user-friendly errors.
 */
export function validateAudio(probe, minSec = 5) {
  if (probe.duration < minSec) {
    throw new Error(
      `Recording is too short (${probe.duration.toFixed(1)}s). ` +
      `Please record at least ${minSec} seconds.`
    );
  }
  if (probe.duration > 600) {
    throw new Error('Recording exceeds 10 minutes. Please record a shorter segment.');
  }
}

/**
 * Detect if a WAV has meaningful speech (not all silence).
 * Returns true if speech is present.
 */
export async function hasSpeech(wavPath) {
  try {
    const { stderr } = await execFileAsync(ffmpegPath, [
      '-i', wavPath,
      '-af', 'silencedetect=noise=-40dB:duration=0.5',
      '-vn', '-sn', '-dn', '-f', 'null', '-',
    ]).catch(e => ({ stderr: e.stderr ?? '' }));

    // If we find at least one non-silence section, speech is present
    // Count silence segments vs total
    const silenceStarts = [...stderr.matchAll(/silence_start:\s*([\d.]+)/g)];
    const durMatch = stderr.match(/Duration:\s*(\d+):(\d+):([\d.]+)/);
    if (!durMatch) return true; // can't tell — assume ok

    const totalSec = +durMatch[1] * 3600 + +durMatch[2] * 60 + +durMatch[3];
    const silenceEnds = [...stderr.matchAll(/silence_duration:\s*([\d.]+)/g)]
      .map(m => parseFloat(m[1]));
    const totalSilence = silenceEnds.reduce((a, b) => a + b, 0);

    // If > 90% of file is silence, reject
    return totalSec <= 0 || (totalSilence / totalSec) < 0.90;
  } catch {
    return true; // assume speech if check fails
  }
}

/**
 * Full pipeline: probe → convert → validate → speech check.
 *
 * NOTE: validation happens AFTER conversion to WAV.
 * Chrome MediaRecorder WebM files have no duration in the container header,
 * so ffprobe returns 0 for the raw upload. The converted PCM WAV always has
 * an accurate duration (samples / sample_rate), so we re-probe the WAV when
 * the original probe returned 0 or NaN.
 *
 * Returns { wavPath, probe } or throws with a user-friendly message.
 */
export async function prepareAudioForAnalysis(uploadedPath, outputDir, baseName = 'user_audio') {
  // Probe original file for codec/format info
  let probe = await probeAudio(uploadedPath);

  // Convert to clean 16kHz mono WAV first — always succeeds even without duration
  const wavPath = `${outputDir}/${baseName}.wav`;
  await convertToWav(uploadedPath, wavPath);

  // If duration was missing/0 from the original container (Chrome WebM), get it from the WAV
  if (!probe.duration || !isFinite(probe.duration)) {
    const wavProbe = await probeAudio(wavPath);
    probe = { ...probe, duration: wavProbe.duration };
  }

  // Validate duration now that we have a reliable number
  validateAudio(probe);

  // Check for meaningful speech content
  const speechFound = await hasSpeech(wavPath);
  if (!speechFound) {
    throw new Error('No speech detected. Check your microphone and try again.');
  }

  return { wavPath, probe };
}
