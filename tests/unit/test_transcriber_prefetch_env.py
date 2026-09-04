"""EXTRACT_PREFETCH_* env overrides.

The prefetch pool is sized for a GPU host, where ffmpeg extraction overlaps
GPU inference. On a CPU-only box the workers contend with the inference they
feed, so the pool size has to be tunable without an image rebuild.
"""
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


def _reload_with(monkeypatch, **env):
    import transcriber
    for key in ('EXTRACT_PREFETCH_WORKERS', 'EXTRACT_PREFETCH_AHEAD'):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(transcriber)


@pytest.fixture(autouse=True)
def _restore_module():
    yield
    import transcriber
    for key in ('EXTRACT_PREFETCH_WORKERS', 'EXTRACT_PREFETCH_AHEAD'):
        os.environ.pop(key, None)
    importlib.reload(transcriber)


class TestPrefetchEnvOverrides:
    def test_defaults_match_upstream_when_unset(self, monkeypatch):
        mod = _reload_with(monkeypatch)
        assert mod.EXTRACT_PREFETCH_WORKERS == 2
        assert mod.EXTRACT_PREFETCH_AHEAD == 2

    def test_single_worker_for_cpu_only_hosts(self, monkeypatch):
        mod = _reload_with(monkeypatch, EXTRACT_PREFETCH_WORKERS='1')
        assert mod.EXTRACT_PREFETCH_WORKERS == 1

    def test_ahead_is_independently_tunable(self, monkeypatch):
        mod = _reload_with(monkeypatch, EXTRACT_PREFETCH_AHEAD='4')
        assert mod.EXTRACT_PREFETCH_AHEAD == 4
        assert mod.EXTRACT_PREFETCH_WORKERS == 2

    @pytest.mark.parametrize('bad', ['0', '-3'])
    def test_below_one_clamps_to_one(self, monkeypatch, bad):
        # A zero-worker pool would stall extraction entirely.
        mod = _reload_with(monkeypatch, EXTRACT_PREFETCH_WORKERS=bad)
        assert mod.EXTRACT_PREFETCH_WORKERS == 1

    @pytest.mark.parametrize('bad', ['', 'two', '1.5'])
    def test_unparseable_falls_back_to_default(self, monkeypatch, bad):
        mod = _reload_with(monkeypatch, EXTRACT_PREFETCH_WORKERS=bad)
        assert mod.EXTRACT_PREFETCH_WORKERS == 2
