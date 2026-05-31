"""Tests for object-store backends: round-trip, isolation, traversal safety."""

import pytest

from services.api.providers.object_store import InMemoryObjectStore, LocalFSObjectStore


def test_localfs_round_trip(tmp_path):
    store = LocalFSObjectStore(tmp_path)
    store.put("sessions/s1/utterances/0.wav", b"audio-bytes")
    assert store.exists("sessions/s1/utterances/0.wav")
    assert store.get("sessions/s1/utterances/0.wav") == b"audio-bytes"


def test_localfs_missing_key_raises(tmp_path):
    store = LocalFSObjectStore(tmp_path)
    assert store.exists("nope") is False
    with pytest.raises(KeyError):
        store.get("nope")


def test_localfs_rejects_path_traversal(tmp_path):
    store = LocalFSObjectStore(tmp_path)
    with pytest.raises(ValueError):
        store.put("../escape.wav", b"x")
    with pytest.raises(ValueError):
        store.put("/abs/path.wav", b"x")
    # exists() swallows the traversal error and returns False.
    assert store.exists("../escape.wav") is False


def test_inmemory_round_trip():
    store = InMemoryObjectStore()
    store.put("k", b"v")
    assert store.exists("k")
    assert store.get("k") == b"v"


def test_inmemory_rejects_empty_key_and_missing_get():
    store = InMemoryObjectStore()
    with pytest.raises(ValueError):
        store.put("", b"v")
    with pytest.raises(KeyError):
        store.get("absent")
