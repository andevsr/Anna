from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from anna.brain.providers.base import ModelProvider


@dataclass
class ProviderSpec:
    name: str
    description: str
    api_key_env: str | None
    base_url: str | None
    default_model: str
    factory: Callable[[str | None, str | None, str], ModelProvider]


_REGISTRY: dict[str, ProviderSpec] = {}


def register(spec: ProviderSpec) -> None:
    _REGISTRY[spec.name] = spec


def get(name: str) -> ProviderSpec | None:
    return _REGISTRY.get(name)


def names() -> list[str]:
    return sorted(_REGISTRY)


def resolve(
    name: str,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> ModelProvider:
    spec = get(name)
    if spec is None:
        raise SystemExit(f"Unknown provider '{name}'. Available: {', '.join(names())}")

    key = api_key
    if spec.api_key_env and not key:
        key = os.getenv(spec.api_key_env)
    if spec.api_key_env and not key:
        raise SystemExit(
            f"Provider '{name}' requires an API key. Set {spec.api_key_env} in .env or pass --api-key."
        )

    return spec.factory(
        key or "", base_url or spec.base_url, model or spec.default_model
    )


def register_builtins() -> None:
    from anna.brain.providers.ollama import OllamaProvider
    from anna.brain.providers.openai_compat import OpenAICompatProvider

    def _openai(api_key, base_url, model):
        return OpenAICompatProvider(api_key=api_key, base_url=base_url, model=model)

    def _ollama(api_key, base_url, model):
        return OllamaProvider(
            base_url=base_url or "http://localhost:11434", model=model
        )

    register(
        ProviderSpec(
            "openai", "OpenAI cloud models", "OPENAI_API_KEY", None, "gpt-4o", _openai
        )
    )
    register(
        ProviderSpec(
            "deepseek",
            "DeepSeek cloud (vision: deepseek-flash)",
            "DEEPSEEK_API_KEY",
            "https://api.deepseek.com",
            "deepseek-flash",
            _openai,
        )
    )
    register(
        ProviderSpec(
            "openrouter",
            "OpenRouter (many models via one key)",
            "OPENROUTER_API_KEY",
            "https://openrouter.ai/api/v1",
            "openai/gpt-4o",
            _openai,
        )
    )
    register(
        ProviderSpec(
            "ollama",
            "Local models via Ollama (vision: qwen2.5vl, llama3.2-vision)",
            None,
            "http://localhost:11434",
            "qwen2.5vl:7b",
            _ollama,
        )
    )


register_builtins()
