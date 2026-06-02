#!/usr/bin/env node
/**
 * Automatic setup for Speech Lab analysis dependencies.
 * Runs on every `npm run dev` — fast no-op when deps are already installed.
 * Creates .venv, installs Python packages, writes .analysis-ready.json.
 */
import { execSync } from 'child_process';
import { execFile } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const execFileAsync = promisify(execFile);
const __dirname   = path.dirname(fileURLToPath(import.meta.url));
const ROOT        = path.join(__dirname, '..');
const VENV_DIR    = path.join(ROOT, '.venv');
const READY_FILE  = path.join(ROOT, '.analysis-ready.json');
const REQUIREMENTS = path.join(ROOT, 'python', 'requirements.txt');

const IS_WIN = process.platform === 'win32';
const VENV_PYTHON = IS_WIN
  ? path.join(VENV_DIR, 'Scripts', 'python.exe')
  : path.join(VENV_DIR, 'bin', 'python3');
const VENV_PIP = IS_WIN
  ? path.join(VENV_DIR, 'Scripts', 'pip.exe')
  : path.join(VENV_DIR, 'bin', 'pip');

const REQUIRED = ['numpy', 'scipy', 'librosa', 'soundfile', 'rapidfuzz'];

async function tryExec(cmd, args) {
  try { await execFileAsync(cmd, args); return true; } catch { return false; }
}

async function findPython() {
  for (const cmd of ['python3', 'python']) {
    if (await tryExec(cmd, ['--version'])) return cmd;
  }
  return null;
}

async function verifyPkg(pythonExec, pkg) {
  try {
    await execFileAsync(pythonExec, ['-c', `import ${pkg}; print(${pkg}.__version__ if hasattr(${pkg},'__version__') else 'ok')`]);
    return true;
  } catch { return false; }
}

function writeStatus(status) {
  fs.writeFileSync(READY_FILE, JSON.stringify(status, null, 2));
}

async function main() {
  // ── Fast path: already ready? ─────────────────────────────────────
  if (fs.existsSync(READY_FILE) && fs.existsSync(VENV_PYTHON)) {
    try {
      const cached = JSON.parse(fs.readFileSync(READY_FILE, 'utf8'));
      if (cached.prosodyReady) {
        // Quick sanity-check librosa still importable
        if (await verifyPkg(VENV_PYTHON, 'librosa')) {
          process.stdout.write('✅ Analysis deps ready (cached)\n');
          return;
        }
      }
    } catch { /* re-run setup */ }
  }

  console.log('\n🔧 Vaani · Speech Lab Setup\n');

  const status = {
    python: false, ffmpeg: false, ffprobe: false,
    numpy: false, scipy: false, librosa: false, soundfile: false, rapidfuzz: false,
    prosodyReady: false,
  };

  // ── ffmpeg ────────────────────────────────────────────────────────
  try {
    const { default: ffmpegPath } = await import('ffmpeg-static');
    status.ffmpeg = !!ffmpegPath && fs.existsSync(ffmpegPath);
  } catch { status.ffmpeg = await tryExec('ffmpeg', ['-version']); }
  console.log(`  ffmpeg:  ${status.ffmpeg ? '✅' : '❌ not found'}`);

  // ── ffprobe ────────────────────────────────────────────────────────
  status.ffprobe = await tryExec('ffprobe', ['-version']);
  console.log(`  ffprobe: ${status.ffprobe ? '✅' : '⚠️  not found (will use ffmpeg fallback)'}`);

  // ── Python ────────────────────────────────────────────────────────
  const systemPython = await findPython();
  if (!systemPython) {
    console.error('\n❌ Python 3 not found. Install Python 3.8+ to enable prosody analysis.');
    console.error('   brew install python3   (macOS)\n');
    writeStatus(status);
    // Non-fatal: server will start with prosodyReady=false
    console.log('\n⚠️  Server will start without prosody analysis.\n');
    return;
  }
  status.python = true;
  console.log(`  python:  ✅ (${systemPython})`);

  // ── Create venv ────────────────────────────────────────────────────
  if (!fs.existsSync(VENV_PYTHON)) {
    process.stdout.write('  Creating .venv…');
    try {
      execSync(`"${systemPython}" -m venv "${VENV_DIR}"`, { stdio: 'pipe', cwd: ROOT });
      process.stdout.write(' ✅\n');
    } catch (err) {
      process.stdout.write(' ❌\n');
      console.error('  Failed to create .venv:', err.message.slice(0, 200));
      writeStatus(status);
      console.log('\n⚠️  Server will start without prosody analysis.\n');
      return;
    }
  }

  // ── Install requirements ──────────────────────────────────────────
  console.log('  Installing analysis packages (first run ~60s)…');
  try {
    execSync(
      `"${VENV_PIP}" install -q --upgrade pip && "${VENV_PIP}" install -q -r "${REQUIREMENTS}"`,
      { stdio: 'pipe', cwd: ROOT, timeout: 300_000 }
    );
    console.log('  Packages installed ✅');
  } catch (err) {
    console.error('  pip install failed:', err.message.slice(0, 300));
    console.error('  Trying individual packages…');
    // Try installing one by one to see what works
    for (const pkg of REQUIRED) {
      try {
        execSync(`"${VENV_PIP}" install -q ${pkg}`, { stdio: 'pipe', cwd: ROOT, timeout: 120_000 });
        console.log(`    ${pkg} ✅`);
      } catch {
        console.log(`    ${pkg} ❌`);
      }
    }
  }

  // ── Verify imports ────────────────────────────────────────────────
  console.log('  Verifying imports…');
  for (const pkg of REQUIRED) {
    status[pkg] = await verifyPkg(VENV_PYTHON, pkg);
    console.log(`    ${pkg}: ${status[pkg] ? '✅' : '❌'}`);
  }

  status.prosodyReady = REQUIRED.every(p => status[p]);
  writeStatus(status);

  if (status.prosodyReady) {
    console.log('\n✅ Speech Lab analysis fully ready.\n');
  } else {
    const failed = REQUIRED.filter(p => !status[p]);
    console.warn(`\n⚠️  Some packages unavailable: ${failed.join(', ')}`);
    console.warn('   Prosody (pitch/expression) analysis will be disabled.');
    console.warn('   Other scoring (accuracy, pace, energy, pauses) will still work.\n');
  }
}

main().catch(err => {
  console.error('Setup warning:', err.message);
  // Non-fatal — server continues
});
