#!/usr/bin/env python3
"""
Prosody analyzer — called from Node.js via stdin/stdout JSON.

Input  (stdin):
  {
    "wavPath": "...",
    "units": [{ "index": N, "start": 0.0, "end": 1.5 }, ...]
  }

Output (stdout):
  {
    "quality": "full" | "no_librosa" | "error",
    "units": [
      {
        "index":               0,
        "start":               0.0,
        "end":                 1.5,
        "pitchMedianHz":       180.0,
        "pitchRangeSemitones": 4.2,
        "pitchSlope":          0.003,
        "rmsDbMean":           -8.2,
        "rmsDbRange":          12.4,
        "energySlope":         -0.8,
        "monotoneScore":       33.6,
        "voicedFraction":      0.72,
        "speechChunkCount":    3,
        "pauseLabel":          "short breath"
      },
      ...
    ]
  }

Pause label thresholds (derived from unit duration gaps that the caller may
supply via unit["gapAfterMs"]; falls back to None if no gap info):
  0–99 ms   → "tiny beat"
  100–499ms → "short breath"
  500–999ms → "let it land"
  1000–1999ms → "long pause"
  2000ms+   → "dead air"
"""
import sys
import json
import math


def pause_label(gap_ms):
    """Human-readable label for a pause duration in milliseconds."""
    if gap_ms is None:
        return None
    gap_ms = float(gap_ms)
    if gap_ms < 100:
        return "tiny beat"
    if gap_ms < 500:
        return "short breath"
    if gap_ms < 1000:
        return "let it land"
    if gap_ms < 2000:
        return "long pause"
    return "dead air"


def count_speech_chunks(seg, sr, threshold_ratio=0.08, min_gap_frames=5):
    """
    Count distinct speech bursts in a segment using amplitude envelope.
    Returns the number of connected regions above the threshold.
    """
    try:
        import numpy as np
        # Compute short-time energy (frames of ~30ms)
        hop = max(1, int(sr * 0.03))
        frames = [seg[i:i+hop] for i in range(0, len(seg), hop) if len(seg[i:i+hop]) == hop]
        if not frames:
            return 0
        energy = np.array([np.sqrt(np.mean(f**2)) for f in frames])
        threshold = np.max(energy) * threshold_ratio
        active = energy > threshold

        # Count connected runs of True with minimum length 2
        chunks = 0
        in_chunk = False
        silence_count = 0
        for a in active:
            if a:
                if not in_chunk:
                    chunks += 1
                    in_chunk = True
                silence_count = 0
            else:
                silence_count += 1
                if in_chunk and silence_count >= min_gap_frames:
                    in_chunk = False
        return chunks
    except Exception:
        return 0


def analyze_unit(u, y, sr, duration):
    """Analyze one time window. Returns a result dict."""
    import numpy as np

    start = float(u.get('start', 0))
    end   = float(u.get('end', duration))
    end   = min(end, duration)
    gap_ms = u.get('gapAfterMs', None)

    s = int(start * sr)
    e = int(end   * sr)
    seg = y[s:e]

    if len(seg) < sr * 0.05:  # < 50 ms — too short
        return {
            'index':     u['index'],
            'start':     round(start, 3),
            'end':       round(end,   3),
            'tooShort':  True,
            'pauseLabel': pause_label(gap_ms),
        }

    hop = 256

    # ── RMS energy ───────────────────────────────────────────────────
    try:
        import librosa
        rms = librosa.feature.rms(y=seg, frame_length=1024, hop_length=hop)[0]
    except Exception:
        rms = np.array([np.sqrt(np.mean(seg**2))])
    rms_safe = rms + 1e-10
    rms_ref  = np.max(rms_safe)
    rms_db   = 20 * np.log10(rms_safe / rms_ref) if rms_ref > 0 else rms_safe * 0

    rms_db_mean  = float(np.mean(rms_db))
    rms_db_range = float(np.max(rms_db) - np.min(rms_db))

    # ── Pitch via pyin ───────────────────────────────────────────────
    pitch_median = 0.0
    pitch_range  = 0.0
    pitch_slope  = 0.0
    voiced_fraction = 0.0
    try:
        import librosa
        f0, voiced, _ = librosa.pyin(
            seg, fmin=60, fmax=500, sr=sr,
            frame_length=1024, hop_length=hop,
        )
        n_voiced = int(np.sum(voiced))
        voiced_fraction = round(float(n_voiced / max(len(voiced), 1)), 3)
        voiced_f0 = f0[voiced & (f0 > 0)] if f0 is not None else np.array([])
        if len(voiced_f0) >= 4:
            pitch_median = float(np.median(voiced_f0))
            semi = 12 * np.log2(voiced_f0 / (pitch_median + 1e-8))
            pitch_range  = float(np.percentile(semi, 90) - np.percentile(semi, 10))
            x = np.linspace(0, 1, len(voiced_f0))
            pitch_slope  = float(np.polyfit(x, voiced_f0, 1)[0])
    except Exception:
        pass

    # ── Energy slope ─────────────────────────────────────────────────
    energy_slope = 0.0
    if len(rms_db) >= 4:
        x = np.linspace(0, 1, len(rms_db))
        energy_slope = float(np.polyfit(x, rms_db, 1)[0])

    # ── Monotone score ───────────────────────────────────────────────
    # Higher pitch range → less monotone.  0 = fully monotone.
    monotone_score = round(max(0.0, min(100.0, pitch_range * 8)), 1)

    # ── Speech chunks ────────────────────────────────────────────────
    speech_chunk_count = count_speech_chunks(seg, sr)

    return {
        'index':               u['index'],
        'start':               round(start, 3),
        'end':                 round(end,   3),
        'pitchMedianHz':       round(pitch_median, 1),
        'pitchRangeSemitones': round(pitch_range,  2),
        'pitchSlope':          round(pitch_slope,  3),
        'rmsDbMean':           round(rms_db_mean,  2),
        'rmsDbRange':          round(rms_db_range, 2),
        'energySlope':         round(energy_slope, 3),
        'monotoneScore':       monotone_score,
        'voicedFraction':      voiced_fraction,
        'speechChunkCount':    speech_chunk_count,
        'pauseLabel':          pause_label(gap_ms),
    }


def main():
    data     = json.loads(sys.stdin.read())
    wav_path = data['wavPath']
    units    = data.get('units', [])

    try:
        import numpy as np
        import librosa

        y, sr    = librosa.load(wav_path, sr=None, mono=True)
        duration = len(y) / sr

        results = []
        for u in units:
            try:
                results.append(analyze_unit(u, y, sr, duration))
            except Exception as exc:
                results.append({
                    'index':    u.get('index', -1),
                    'error':    str(exc),
                    'tooShort': False,
                })

        print(json.dumps({'quality': 'full', 'units': results}))

    except ImportError as e:
        print(json.dumps({'quality': 'no_librosa', 'error': str(e), 'units': []}))
    except Exception as e:
        print(json.dumps({'quality': 'error', 'error': str(e), 'units': []}))


if __name__ == '__main__':
    main()
