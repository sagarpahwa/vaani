/**
 * Calls python/analyze_prosody.py via stdin/stdout JSON.
 * Prefers the .venv Python created by setup-analysis.js.
 * Falls back gracefully if Python or librosa is unavailable.
 */
import { spawn, execFile } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const execFileAsync = promisify(execFile);
const __dirname    = path.dirname(fileURLToPath(import.meta.url));
const ROOT         = path.join(__dirname, '..');
const SCRIPT       = path.join(ROOT, 'python', 'analyze_prosody.py');
const READY_FILE   = path.join(ROOT, '.analysis-ready.json');

// Prefer venv Python, fall back to system
const IS_WIN = process.platform === 'win32';
const VENV_PYTHON = IS_WIN
  ? path.join(ROOT, '.venv', 'Scripts', 'python.exe')
  : path.join(ROOT, '.venv', 'bin', 'python3');

async function findPython() {
  if (fs.existsSync(VENV_PYTHON)) return VENV_PYTHON;
  for (const cmd of ['python3', 'python']) {
    try { await execFileAsync(cmd, ['--version']); return cmd; } catch {}
  }
  return null;
}

function runScript(python, inputStr) {
  return new Promise((resolve, reject) => {
    const proc = spawn(python, [SCRIPT], { timeout: 90_000 });
    let out = '', err = '';
    proc.stdout.on('data', c => { out += c; });
    proc.stderr.on('data', c => { err += c; });
    proc.on('close', code => {
      if (code !== 0 && !out.trim()) reject(new Error(`Python exited ${code}: ${err.slice(0, 300)}`));
      else resolve({ stdout: out, stderr: err });
    });
    proc.on('error', reject);
    proc.stdin.write(inputStr, 'utf8');
    proc.stdin.end();
  });
}

/**
 * Check if prosody analysis is ready (venv + librosa installed).
 */
export function isProsodyReady() {
  try {
    if (!fs.existsSync(READY_FILE)) return false;
    const status = JSON.parse(fs.readFileSync(READY_FILE, 'utf8'));
    return status.prosodyReady === true && fs.existsSync(VENV_PYTHON);
  } catch { return false; }
}

/**
 * Run prosody analysis on a WAV file for given time windows.
 *
 * @param {string} wavPath  - 16kHz mono WAV
 * @param {Array}  units    - [{index, start, end}]
 * @returns {{ quality, units }}
 */
export async function analyzeProsody(wavPath, units) {
  const python = await findPython();
  if (!python) {
    return { quality: 'no_python', units: [] };
  }
  if (!isProsodyReady() && python === VENV_PYTHON) {
    return { quality: 'no_librosa', units: [] };
  }

  const input = JSON.stringify({ wavPath, units });
  try {
    const { stdout, stderr } = await runScript(python, input);
    if (stderr?.trim()) console.warn('[prosody] py stderr:', stderr.trim().slice(0, 300));
    return JSON.parse(stdout.trim());
  } catch (err) {
    console.warn('[prosody] failed:', err.message?.slice(0, 200));
    return { quality: 'error', error: err.message, units: [] };
  }
}

export function mergeProsodyIntoFeatures(features, prosodyUnits) {
  const byIndex = new Map((prosodyUnits ?? []).map(u => [u.index, u]));
  return features.map(f => {
    const p = byIndex.get(f.unitIndex);
    if (!p || p.tooShort) return { ...f, prosody: null };
    return {
      ...f,
      prosody: {
        pitchMedianHz:       p.pitchMedianHz,
        pitchRangeSemitones: p.pitchRangeSemitones,
        pitchSlope:          p.pitchSlope,
        rmsDbMean:           p.rmsDbMean,
        rmsDbRange:          p.rmsDbRange,
        energySlope:         p.energySlope,
        monotoneScore:       p.monotoneScore,
      },
    };
  });
}
