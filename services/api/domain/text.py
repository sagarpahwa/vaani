"""Pure text utilities: tokenization, normalization, deterministic seeding.

No randomness that varies across runs — `stable_seed` hashes its inputs so the
mock AI produces identical output for identical input on every machine.
"""

import hashlib
import re

_WORD_RE = re.compile(r"[a-z0-9']+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def tokenize(text: str) -> list[str]:
    """Split text into lowercase word tokens, stripping punctuation."""
    return _WORD_RE.findall((text or "").lower())


def normalize(word: str) -> str:
    """Normalize a single token for comparison (lowercase, strip apostrophes)."""
    return (word or "").lower().strip("'")


def stable_seed(*parts: object) -> int:
    """Deterministic 32-bit seed derived from the string form of all parts.

    Uses md5 (not Python's salted `hash()`) so the value is identical across
    processes and machines — essential for reproducible mock transcripts.
    """
    joined = "\x1f".join(str(p) for p in parts)
    digest = hashlib.md5(joined.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def split_script_text(text: str) -> list[str]:
    """Split a free-form user script (Mode B) into non-empty trimmed lines.

    Honors explicit newlines first; if the user pasted one long paragraph,
    falls back to sentence segmentation so each unit is independently coachable.
    """
    if not text or not text.strip():
        return []
    raw_lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in raw_lines if ln]
    if len(lines) > 1:
        return lines
    # Single block: split into sentences.
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(lines[0])]
    return [s for s in sentences if s]
