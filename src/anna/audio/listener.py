from __future__ import annotations

import queue
import time

import numpy as np

from anna.audio.capture import Microphone, SAMPLE_RATE
from anna.audio.vad import VAD

FRAME_MS = 30
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)


def _to_float32(frames: list[np.ndarray]) -> np.ndarray:
    if not frames:
        return np.zeros(0, dtype=np.float32)
    pcm = np.concatenate(frames)
    return pcm.astype(np.float32) / 32768.0


class SpeechListener:
    def __init__(
        self,
        mic: Microphone,
        vad: VAD,
        min_ms: int = 300,
        end_silence_ms: int = 800,
        max_ms: int = 15000,
        start_frames: int = 3,
    ) -> None:
        self.mic = mic
        self.vad = vad
        self.min_ms = min_ms
        self.end_silence_ms = end_silence_ms
        self.max_ms = max_ms
        self.start_frames = start_frames
        self._buf: list[np.ndarray] = []
        self._in_utterance = False
        self._speech_run = 0
        self._silence_frames = 0

    def listen(self, timeout_s: float | None = None) -> np.ndarray | None:
        end_frames = max(1, self.end_silence_ms // FRAME_MS)
        deadline = time.monotonic() + timeout_s if timeout_s else None

        while True:
            try:
                block = self.mic.read(timeout=0.1)
            except queue.Empty:
                if deadline is not None and time.monotonic() >= deadline:
                    return None
                continue

            for start in range(0, len(block), FRAME_SAMPLES):
                frame = block[start : start + FRAME_SAMPLES]
                if len(frame) < FRAME_SAMPLES:
                    break

                is_speech = self.vad.is_speech(frame.tobytes())
                if is_speech:
                    self._silence_frames = 0
                    self._speech_run += 1
                    self._buf.append(frame)
                    if self._speech_run >= self.start_frames:
                        self._in_utterance = True
                elif not self._in_utterance:
                    self._speech_run = 0
                    self._buf = []
                else:
                    self._silence_frames += 1
                    self._buf.append(frame)
                    if self._silence_frames >= end_frames:
                        utt = self._finalize()
                        if utt is not None:
                            return utt

                if self._in_utterance and len(self._buf) * FRAME_MS >= self.max_ms:
                    utt = self._finalize()
                    if utt is not None:
                        return utt

    def _finalize(self) -> np.ndarray | None:
        frames = self._buf
        self._buf = []
        self._in_utterance = False
        self._speech_run = 0
        self._silence_frames = 0
        if len(frames) * FRAME_MS < self.min_ms:
            return None
        return _to_float32(frames)
