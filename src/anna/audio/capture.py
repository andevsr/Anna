from __future__ import annotations

import queue

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000


class Microphone:
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        block_ms: int = 30,
        device=None,
    ) -> None:
        self.sample_rate = sample_rate
        self.block = int(sample_rate * block_ms / 1000)
        self.device = device
        self._q: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: sd.InputStream | None = None

    def _callback(self, indata, frames, time_info, status) -> None:
        self._q.put(indata.copy())

    def start(self) -> None:
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.block,
                device=self.device,
                callback=self._callback,
            )
        except sd.PortAudioError as e:
            raise RuntimeError(
                "Could not open the microphone. Grant Microphone access in "
                "System Settings → Privacy & Security → Microphone, then retry."
            ) from e
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def read(self, timeout: float | None = None) -> np.ndarray:
        return self._q.get(timeout=timeout)

    def drain(self) -> None:
        while True:
            try:
                self._q.get_nowait()
            except queue.Empty:
                break

    def __enter__(self) -> Microphone:
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
