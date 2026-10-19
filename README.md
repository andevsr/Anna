# anna

Voice-controlled computer-use agent for macOS. Sees the screen and controls the Mac (mouse, keyboard, apps, shell) via a vision-capable LLM, driven by text or by voice ("Hey Anna").

## Setup

```bash
brew install portaudio ffmpeg
uv sync
cp .env.example .env          # add your provider API key
```

Grant permissions: **Accessibility**, **Screen Recording**, and **Microphone** (see `scripts/permissions.md`), then restart your terminal.

## Usage

```bash
# One-shot instruction
uv run anna "open Safari and go to apple.com"

# Interactive REPL
uv run anna

# List providers
uv run anna --list-providers

# Pick a provider/model (defaults: deepseek -> deepseek-flash)
uv run anna --provider openai --model gpt-4o "open the calculator app"
uv run anna --provider openrouter --model anthropic/claude-sonnet-4.5 "open the calculator app"
uv run anna --provider deepseek --model deepseek-flash "open the calculator app"

# Local models via Ollama (vision: qwen2.5vl, llama3.2-vision)
ollama serve                 # start Ollama
ollama pull qwen2.5vl:7b     # pull a vision model
uv run anna --provider ollama "open the calculator app"

# Voice mode: always listening for the wake word "hey anna"
uv run anna --voice
uv run anna --voice --wake-word "hey jarvis" --no-tts
```

Say "Hey Anna, open the calculator" and it will transcribe locally (mlx-whisper) and drive the agent. First voice run downloads the Whisper model (~145 MB).

## Architecture

```
CLI ─► Agent ─► provider.next_action(goal, history, screenshot) ─► Action (JSON)
                    │                                                    │
                    └────────── model (OpenAI / OpenRouter / later Ollama)
                                                                         ▼
                                              executor ─► Quartz mouse/keyboard, apps, shell
```

- `anna/control/` — screen capture (mss/Quartz), mouse, keyboard, apps, executor
- `anna/brain/` — agent loop, system prompt, model providers (OpenAI / DeepSeek / OpenRouter / Ollama) behind a registry
- `anna/audio/` — mic capture, VAD + utterance segmentation, wake-word matching, STT (mlx-whisper / OpenAI), TTS (`say`)
- `anna/voice.py` — always-listening voice loop (wake word → command → agent)
- `anna/actions.py` — pydantic action schema (`mouse_move`, `click`, `drag`, `type`, `key`, `scroll`, `wait`, `open_app`, `shell`, `ask_user`, `done`)
- `anna/safety/policy.py` — risk confirmation hook (shell commands require approval)

## Status

- [x] Phase 0 — env + permissions + control primitives
- [x] Phase 1 — text-driven agent loop (OpenAI-compatible provider)
- [x] Phase 2 — provider registry + Ollama local models
- [x] Phase 3 — voice input (wake word "Hey Anna", VAD, mlx-whisper)
- [ ] Phase 4 — safety policy + confirmation
- [ ] Phase 5 — menubar overlay, TTS, `.app` bundling
