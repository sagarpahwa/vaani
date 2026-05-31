#!/usr/bin/env python3
"""
Coverage ratchet: the quality bar only moves up, never down.

Reads coverage.json produced by pytest-cov (--cov-report=json).
Compares total coverage against the committed baseline in quality-baseline.json.
Fails CI if coverage dropped. Prints upgrade instructions when coverage improved.

Usage:
    pytest tests/unit/ --cov=scripts/python --cov-report=json
    python3 scripts/ci/ratchet_coverage.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
BASELINE_FILE = ROOT / "quality-baseline.json"
COVERAGE_FILE = ROOT / "coverage.json"


def main() -> None:
    if not COVERAGE_FILE.exists():
        print("ERROR: coverage.json not found.")
        print("Run: pytest tests/unit/ --cov=scripts/python --cov-report=json")
        sys.exit(1)

    coverage_data = json.loads(COVERAGE_FILE.read_text())
    current_pct = round(coverage_data["totals"]["percent_covered"], 1)

    if not BASELINE_FILE.exists():
        print(f"WARNING: quality-baseline.json not found. Current coverage: {current_pct:.1f}%")
        print("Create it with: python3 scripts/ci/update_baseline.py")
        sys.exit(0)

    baseline = json.loads(BASELINE_FILE.read_text())
    floor = baseline.get("coverage_floor", 0)

    if current_pct < floor:
        drop = floor - current_pct
        print(f"FAIL: Coverage dropped {drop:.1f}% (was {floor:.1f}%, now {current_pct:.1f}%)")
        print()
        print("Options:")
        print("  1. Add tests to cover the missing lines (recommended)")
        print("  2. If intentional, update the baseline: python3 scripts/ci/update_baseline.py")
        sys.exit(1)

    if current_pct > floor:
        gained = current_pct - floor
        print(f"Coverage improved +{gained:.1f}% (was {floor:.1f}%, now {current_pct:.1f}%)")
        print()
        print(f"Update the baseline: python3 scripts/ci/update_baseline.py")
    else:
        print(f"OK: Coverage {current_pct:.1f}% meets baseline {floor:.1f}%")


if __name__ == "__main__":
    main()
