from __future__ import annotations

import io
import wave

import numpy as np


class Transcriber:
    def __init__(
        self,
        engine: str = "mlx",
        model: str = "mlx-community/whisper-base.en-mlx",
        api_key: str | None = None,
    ) -> None:
        self.engine = engine
        self.model = model
        self.api_key = api_key

    def transcribe(self, audio: np.ndarray) -> str:
        if audio is None or audio.size == 0:
            return ""
        if self.engine == "openai":
            return self._transcribe_openai(audio)
        return self._transcribe_mlx(audio)

    def warmup(self) -> None:
        if self.engine == "mlx":
            from mlx_whisper.load_models import load_model

            load_model(self.model)

    def _transcribe_mlx(self, audio: np.ndarray) -> str:
        import mlx_whisper

        result = mlx_whisper.transcribe(audio, path_or_hf_repo=self.model)
        return (result.get("text") or "").strip()

    def _transcribe_openai(self, audio: np.ndarray) -> str:
        from openai import OpenAI

        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY required for OpenAI STT.")
        client = OpenAI(api_key=self.api_key)

        pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(pcm.tobytes())
        buf.seek(0)

        resp = client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.wav", buf, "audio/wav"),
        )
        return (resp.text or "").strip()
