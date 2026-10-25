from __future__ import annotations

import argparse
import os
import sys

from anna.brain.agent import Agent
from anna.brain.providers import registry
from anna.config import Settings
from anna.interaction import TextInteraction
from anna.safety.audit import AuditLog
from anna.safety.policy import Policy


def build_provider(settings: Settings):
    return registry.resolve(
        settings.provider,
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model,
    )


def list_providers() -> None:
    print("Available providers:")
    for name in registry.names():
        spec = registry.get(name)
        key = spec.api_key_env or "(none)"
        print(
            f"  {name:<12} {spec.description}  [key: {key}, default model: {spec.default_model}]"
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="anna",
        description="Voice/computer-use agent for macOS.",
    )
    parser.add_argument(
        "instruction", nargs="?", help="Instruction to run (omit for REPL)"
    )
    parser.add_argument(
        "--provider", default=None, help="Provider name (see --list-providers)"
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument(
        "--list-providers", action="store_true", help="List providers and exit"
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Run the always-listening voice loop (wake word + speech-to-text)",
    )
    parser.add_argument("--wake-word", default=None)
    parser.add_argument("--stt-engine", default=None, help="mlx | openai")
    parser.add_argument("--stt-model", default=None)
    parser.add_argument("--no-tts", action="store_true", help="Disable spoken feedback")
    args = parser.parse_args(argv)

    if args.list_providers:
        list_providers()
        return

    settings = Settings.from_env()
    if args.provider:
        settings.provider = args.provider
    if args.model:
        settings.model = args.model
    if args.base_url:
        settings.base_url = args.base_url
    if args.api_key:
        settings.api_key = args.api_key
    if args.max_steps:
        settings.max_steps = args.max_steps
    if args.wake_word:
        settings.wake_word = args.wake_word
    if args.stt_engine:
        settings.stt_engine = args.stt_engine
    if args.stt_model:
        settings.stt_model = args.stt_model
    if args.no_tts:
        settings.tts = False

    provider = build_provider(settings)
    audit = AuditLog(path=settings.audit_log, enabled=settings.audit_enabled)
    agent = Agent(
        provider,
        max_steps=settings.max_steps,
        policy=Policy(),
        interaction=TextInteraction(),
        audit=audit,
    )

    if args.voice:
        from anna.audio.stt import Transcriber
        from anna.voice import VoiceLoop

        stt = Transcriber(
            engine=settings.stt_engine,
            model=settings.stt_model,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        loop = VoiceLoop(agent, stt, wake_word=settings.wake_word, tts=settings.tts)
        try:
            loop.run()
        except KeyboardInterrupt:
            print("\nbye")
        return

    if args.instruction:
        try:
            print(agent.run(args.instruction))
        except Exception as exc:
            print(f"[error] {exc}", file=sys.stderr)
        return

    print("anna (text mode). Type an instruction, or 'quit' to exit.")
    while True:
        try:
            goal = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not goal:
            continue
        if goal.lower() in ("quit", "exit", "q"):
            return
        try:
            print(agent.run(goal))
        except Exception as exc:
            print(f"[error] {exc}")


if __name__ == "__main__":
    sys.exit(main())
