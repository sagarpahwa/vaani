"""Ensure the repo root is importable so `services.api.*` resolves regardless of CWD."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
