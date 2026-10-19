from __future__ import annotations

import subprocess


def open_app(name: str) -> str:
    result = subprocess.run(
        ["open", "-a", name], capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return result.stderr.strip() or f"Failed to open {name}"
    return result.stdout.strip() or f"Opened {name}"


def run_shell(command: str, timeout: int = 60) -> str:
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=timeout
    )
    out = (result.stdout or "") + (result.stderr or "")
    return out.strip()
