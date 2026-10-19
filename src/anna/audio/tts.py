from __future__ import annotations

import subprocess


def speak(text: str) -> None:
    if not text:
        return
    subprocess.run(["say", text])
