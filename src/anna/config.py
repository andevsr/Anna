from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    provider: str = "openai"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    max_steps: int = 25
    stt_engine: str = "mlx"
    stt_model: str = "mlx-community/whisper-base.en-mlx"
    wake_word: str = "hey anna"
    tts: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            provider=os.getenv("ANNA_PROVIDER", "openai"),
            model=os.getenv("ANNA_MODEL") or None,
            base_url=os.getenv("ANNA_BASE_URL") or None,
            api_key=os.getenv("ANNA_API_KEY") or None,
            max_steps=int(os.getenv("ANNA_MAX_STEPS", "25")),
            stt_engine=os.getenv("ANNA_STT_ENGINE", "mlx"),
            stt_model=os.getenv("ANNA_STT_MODEL", "mlx-community/whisper-base.en-mlx"),
            wake_word=os.getenv("ANNA_WAKE_WORD", "hey anna"),
            tts=os.getenv("ANNA_TTS", "1") not in ("0", "false", "False"),
        )
