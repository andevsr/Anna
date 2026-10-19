from __future__ import annotations

from anna.actions import AskUser, Shell


class Policy:
    def needs_confirmation(self, action) -> str | None:
        if isinstance(action, Shell):
            return f"run shell command: {action.command}"
        if isinstance(action, AskUser):
            return None
        return None
