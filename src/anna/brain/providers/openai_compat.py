from __future__ import annotations

import json

from openai import OpenAI

from anna.brain import prompts
from anna.brain.providers.base import ModelProvider
from anna.brain.providers.jsonutil import extract_json


class OpenAICompatProvider(ModelProvider):
    """Provider for any OpenAI-compatible chat-completions endpoint (OpenAI, OpenRouter, DeepSeek, etc.)."""

    name = "openai-compat"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str = "gpt-4o",
        system_prompt: str | None = None,
        max_tokens: int = 1000,
    ) -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.system_prompt = system_prompt or prompts.SYSTEM_PROMPT
        self.max_tokens = max_tokens

    def next_action(self, goal: str, history: list[dict], screenshot_b64: str) -> dict:
        messages: list[dict] = [{"role": "system", "content": self.system_prompt}]

        for entry in history[-12:]:
            messages.append({"role": "assistant", "content": entry.get("note", "")})

        user_content = [
            {"type": "text", "text": f"Goal: {goal}"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"},
            },
        ]
        messages.append({"role": "user", "content": user_content})

        last_error: Exception | None = None
        for attempt in range(3):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=self.max_tokens,
            )
            content = (response.choices[0].message.content or "").strip()
            if not content:
                last_error = ValueError("model returned empty content")
                continue
            try:
                return extract_json(content)
            except json.JSONDecodeError as e:
                last_error = e
                continue
        raise RuntimeError(
            f"failed to parse a valid JSON action after retries: {last_error}"
        )
