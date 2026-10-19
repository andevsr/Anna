from __future__ import annotations

import httpx

from anna.brain import prompts
from anna.brain.providers.base import ModelProvider
from anna.brain.providers.jsonutil import extract_json


class OllamaProvider(ModelProvider):
    """Local models served by Ollama (native /api/chat endpoint)."""

    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5vl:7b",
        timeout: float = 180.0,
        system_prompt: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.system_prompt = system_prompt or prompts.SYSTEM_PROMPT
        self._client = httpx.Client(timeout=timeout)

    def list_models(self) -> list[str]:
        try:
            r = self._client.get(f"{self.base_url}/api/tags")
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return []

    def next_action(self, goal: str, history: list[dict], screenshot_b64: str) -> dict:
        messages: list[dict] = [{"role": "system", "content": self.system_prompt}]
        for entry in history[-12:]:
            messages.append({"role": "assistant", "content": entry.get("note", "")})
        messages.append(
            {"role": "user", "content": f"Goal: {goal}", "images": [screenshot_b64]}
        )

        payload = {
            "model": self.model,
            "messages": messages,
            "format": "json",
            "stream": False,
            "options": {"num_predict": 1000, "temperature": 0.2},
        }

        try:
            r = self._client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Could not reach Ollama at {self.base_url}. Start it with `ollama serve`."
            ) from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                available = ", ".join(self.list_models()) or "none"
                raise RuntimeError(
                    f"Model '{self.model}' not found in Ollama. Pull it with: "
                    f"`ollama pull {self.model}`. Available models: {available}"
                ) from e
            raise

        content = (r.json().get("message", {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("Ollama returned empty content.")
        return extract_json(content)
