"""Object-store implementations: local filesystem (default) and in-memory.

Audio blobs are stored here, not in Mongo. Keys look like
`sessions/<id>/utterances/<n>.wav`; the local backend maps them to files under
a single root, with a guard against path traversal escaping that root.
"""

from pathlib import Path

from .base import ObjectStore


class LocalFSObjectStore(ObjectStore):
    """Stores blobs as files under a single root directory.

    The default backend for local POC runs — survives restarts and is directly
    inspectable on disk. Keys are treated as relative paths under `root`.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, key: str) -> Path:
        """Resolve a key to a path, refusing anything that escapes the root."""
        if not key or key.startswith("/"):
            raise ValueError(f"invalid object key: {key!r}")
        candidate = (self.root / key).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError(f"object key escapes storage root: {key!r}")
        return candidate

    def put(self, key: str, data: bytes) -> str:
        path = self._safe_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        path = self._safe_path(key)
        if not path.exists():
            raise KeyError(key)
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        try:
            return self._safe_path(key).exists()
        except ValueError:
            return False


class InMemoryObjectStore(ObjectStore):
    """Dict-backed store for unit tests — no disk, no cleanup."""

    def __init__(self):
        self._blobs: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> str:
        if not key:
            raise ValueError("object key must be non-empty")
        self._blobs[key] = data
        return key

    def get(self, key: str) -> bytes:
        if key not in self._blobs:
            raise KeyError(key)
        return self._blobs[key]

    def exists(self, key: str) -> bool:
        return key in self._blobs
