#!/usr/bin/env python3
"""
Update quality-baseline.json with current coverage results.
Only run this when intentionally raising the quality bar.

Usage:
    pytest tests/unit/ --cov=scripts/python --cov-report=json
    python3 scripts/ci/update_baseline.py
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parents[2]
BASELINE_FILE = ROOT / "quality-baseline.json"
COVERAGE_FILE = ROOT / "coverage.json"


def main() -> None:
    if not COVERAGE_FILE.exists():
        print("ERROR: coverage.json not found. Run pytest with --cov-report=json first.")
        raise SystemExit(1)

    coverage_data = json.loads(COVERAGE_FILE.read_text())
    total = coverage_data["totals"]["percent_covered"]

    existing = json.loads(BASELINE_FILE.read_text()) if BASELINE_FILE.exists() else {}
    old_floor = existing.get("coverage_floor", 0)

    if total < old_floor:
        print(f"ERROR: Current coverage {total:.1f}% is below existing baseline {old_floor:.1f}%.")
        print("Fix the coverage drop before updating the baseline.")
        raise SystemExit(1)

    by_module = {
        path: data["summary"]["percent_covered"]
        for path, data in coverage_data.get("files", {}).items()
    }

    baseline = {
        "coverage_floor": round(total, 1),
        "last_updated": date.today().isoformat(),
        "coverage_by_module": {k: round(v, 1) for k, v in sorted(by_module.items())},
    }

    BASELINE_FILE.write_text(json.dumps(baseline, indent=2) + "\n")
    print(f"Updated quality-baseline.json: coverage_floor = {total:.1f}% (was {old_floor:.1f}%)")
    print("Commit this file: git add quality-baseline.json")


if __name__ == "__main__":
    main()
