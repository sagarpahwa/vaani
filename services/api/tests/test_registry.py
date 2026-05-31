"""Tests for provider wiring: mock stack builds, bad config fails loudly."""

import pytest

from services.api.providers.object_store import InMemoryObjectStore, LocalFSObjectStore
from services.api.providers.registry import ProviderBundle, build_providers


class _Settings:
    provider_stt = "mock"
    provider_tts = "mock"
    provider_llm = "mock"
    object_store = "memory"
    poc_storage_dir = "./.poc-storage"


def test_build_mock_bundle():
    bundle = build_providers(_Settings(), store=InMemoryObjectStore())
    assert isinstance(bundle, ProviderBundle)
    assert isinstance(bundle.store, InMemoryObjectStore)


def test_build_localfs_store(tmp_path):
    s = _Settings()
    s.object_store = "localfs"
    s.poc_storage_dir = str(tmp_path)
    bundle = build_providers(s)
    assert isinstance(bundle.store, LocalFSObjectStore)


def test_unknown_stt_provider_raises():
    s = _Settings()
    s.provider_stt = "deepgram"  # not 'mock' or 'whisper'
    with pytest.raises(ValueError, match="not supported"):
        build_providers(s, store=InMemoryObjectStore())


def test_unknown_tts_provider_raises():
    s = _Settings()
    s.provider_tts = "elevenlabs"  # not 'mock' or 'macos'
    with pytest.raises(ValueError, match="not supported"):
        build_providers(s, store=InMemoryObjectStore())


def test_non_mock_llm_raises():
    s = _Settings()
    s.provider_llm = "openai"  # only deterministic 'mock' feedback in the POC
    with pytest.raises(ValueError, match="only 'mock'"):
        build_providers(s, store=InMemoryObjectStore())


def test_minio_store_not_implemented():
    s = _Settings()
    s.object_store = "minio"
    with pytest.raises(NotImplementedError):
        build_providers(s)


def test_unknown_store_raises():
    s = _Settings()
    s.object_store = "ftp"
    with pytest.raises(ValueError, match="unknown OBJECT_STORE"):
        build_providers(s)
