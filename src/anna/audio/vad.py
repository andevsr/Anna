from __future__ import annotations

import sys
import types


def _ensure_pkg_resources() -> None:
    if "pkg_resources" in sys.modules:
        return
    stub = types.ModuleType("pkg_resources")

    class _Distribution:
        def __init__(self, version: str) -> None:
            self._version = version

        @property
        def version(self) -> str:
            return self._version

    stub.get_distribution = lambda name: _Distribution("2.0.10")
    sys.modules["pkg_resources"] = stub


_ensure_pkg_resources()

import webrtcvad  # noqa: E402


class VAD:
    def __init__(self, aggressiveness: int = 2, sample_rate: int = 16000) -> None:
        self._vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate

    def is_speech(self, pcm16: bytes) -> bool:
        return self._vad.is_speech(pcm16, self.sample_rate)
