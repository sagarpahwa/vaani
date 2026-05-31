#!/usr/bin/env python3
"""
CI gate: CLAUDE.md must be updated whenever new source files are introduced.

This prevents documentation drift — the most common failure mode in AI-driven
development where code evolves faster than the contract that guides it.

Exits 1 if new source files were added in a PR but CLAUDE.md was not touched.
Exits 0 otherwise (including pushes directly to a branch without a base).
"""
import subprocess
import sys

SOURCE_DIRS = [
    "scripts/",
    "schemas/",
    "services/",
    "api/",
    "app/",
]


def get_changed_files(base_ref: str = "origin/main") -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Can't determine diff (e.g. fresh branch with no common ancestor) — pass
        print(f"WARNING: Could not compute diff against {base_ref}. Skipping check.")
        return []
    return [f for f in result.stdout.strip().split("\n") if f]


def main() -> None:
    files = get_changed_files()
    if not files:
        print("OK: No changed files detected.")
        sys.exit(0)

    new_source_files = [f for f in files if any(f.startswith(d) for d in SOURCE_DIRS)]
    claude_md_changed = "CLAUDE.md" in files

    if new_source_files and not claude_md_changed:
        print("ERROR: New source files added but CLAUDE.md was not updated.")
        print("Files added:")
        for f in new_source_files:
            print(f"  + {f}")
        print()
        print("Update CLAUDE.md to document the new pattern before merging.")
        print("See: 'How to Add New Code' section in CLAUDE.md")
        sys.exit(1)

    if new_source_files and claude_md_changed:
        print(f"OK: {len(new_source_files)} new source file(s) introduced, CLAUDE.md updated.")
    else:
        print("OK: No new source patterns introduced.")


if __name__ == "__main__":
    main()
