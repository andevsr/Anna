from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel


def _default_path() -> Path:
    configured = os.getenv("ANNA_AUDIT_LOG")
    if configured:
        return Path(configured).expanduser()
    return Path("~/.anna/audit.jsonl").expanduser()


class AuditLog:
    def __init__(
        self, path: str | Path | None = None, enabled: bool | None = None
    ) -> None:
        self.path = Path(path).expanduser() if path else _default_path()
        if enabled is None:
            enabled = os.getenv("ANNA_AUDIT", "1").strip().lower() not in {
                "0",
                "false",
                "no",
                "off",
            }
        self.enabled = enabled
        self._warned = False

    def record(
        self,
        *,
        goal: str,
        step: int,
        action: BaseModel | dict | None,
        decision: str,
        reason: str = "",
        outcome: str = "",
        error: str | None = None,
    ) -> None:
        if not self.enabled:
            return

        if isinstance(action, BaseModel):
            action_data = action.model_dump()
        elif isinstance(action, dict):
            action_data = action
        else:
            action_data = None

        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "goal": goal,
            "step": step,
            "action": action_data,
            "decision": decision,
            "reason": reason,
            "outcome": outcome,
            "error": error,
        }

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, default=str) + "\n")
        except OSError as exc:
            if not self._warned:
                print(f"[warn] could not write audit log {self.path}: {exc}")
                self._warned = True
