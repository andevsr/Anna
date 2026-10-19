from __future__ import annotations

from abc import ABC, abstractmethod


class ModelProvider(ABC):
    name: str = "base"

    @abstractmethod
    def next_action(self, goal: str, history: list[dict], screenshot_b64: str) -> dict:
        """Return the next raw action dict for the given goal and current screen."""
        raise NotImplementedError
