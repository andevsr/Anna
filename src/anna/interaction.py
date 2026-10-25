from __future__ import annotations

import re
from typing import TYPE_CHECKING, Protocol

from anna.audio.tts import speak

if TYPE_CHECKING:
    from anna.audio.listener import SpeechListener
    from anna.audio.stt import Transcriber


_YES_WORDS = {
    "yes",
    "yeah",
    "yep",
    "yup",
    "sure",
    "ok",
    "okay",
    "proceed",
    "confirm",
    "confirmed",
    "approve",
    "approved",
    "affirmative",
    "correct",
    "y",
}

_NO_WORDS = {
    "no",
    "nope",
    "nah",
    "cancel",
    "stop",
    "deny",
    "negative",
    "never",
    "don't",
    "dont",
    "n",
}

_YES_PHRASES = (("go", "ahead"), ("do", "it"), ("sounds", "good"), ("go", "for", "it"))
_NO_PHRASES = (("do", "not"), ("not", "now"), ("not", "sure"))


def _contains_phrase(tokens: list[str], phrase: tuple[str, ...]) -> bool:
    size = len(phrase)
    return any(
        tuple(tokens[index : index + size]) == phrase for index in range(len(tokens))
    )


def parse_yes_no(text: str) -> bool | None:
    tokens = re.findall(r"[a-z']+", text.lower())
    if not tokens:
        return None
    if any(_contains_phrase(tokens, phrase) for phrase in _NO_PHRASES):
        return False
    if any(word in _NO_WORDS for word in tokens):
        return False
    if any(_contains_phrase(tokens, phrase) for phrase in _YES_PHRASES):
        return True
    if any(word in _YES_WORDS for word in tokens):
        return True
    return None


class Interaction(Protocol):
    def ask(self, question: str) -> str: ...

    def confirm(self, description: str, reason: str) -> bool: ...


class TextInteraction:
    def ask(self, question: str) -> str:
        print(f"[ask_user] {question}")
        try:
            return input("Answer (or 'skip'): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return ""

    def confirm(self, description: str, reason: str) -> bool:
        print(f"[confirm] {reason}")
        print(f"          {description}")
        try:
            answer = input("Approve? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        return answer in {"y", "yes", "yeah", "ok", "okay"}


class VoiceInteraction:
    def __init__(
        self,
        listener: SpeechListener,
        stt: Transcriber,
        tts: bool = True,
        timeout_s: float = 5.0,
    ) -> None:
        self.listener = listener
        self.stt = stt
        self.tts = tts
        self.timeout_s = timeout_s

    def _speak(self, text: str) -> None:
        if self.tts:
            speak(text)

    def _listen(self, timeout_s: float) -> str:
        utterance = self.listener.listen(timeout_s=timeout_s)
        if utterance is None:
            return ""
        text = self.stt.transcribe(utterance)
        if text:
            print(f"[heard] {text}")
        return text

    def ask(self, question: str) -> str:
        print(f"[ask_user] {question}")
        self._speak(question)
        return self._listen(self.timeout_s)

    def confirm(self, description: str, reason: str) -> bool:
        print(f"[confirm] {reason}")
        print(f"          {description}")
        prompt = f"{reason}. Should I proceed?"
        for attempt in range(2):
            self._speak(prompt)
            answer = parse_yes_no(self._listen(self.timeout_s))
            if answer is not None:
                return answer
            if attempt == 0:
                prompt = "Please say yes or no. Should I proceed?"
        print("[confirm] no clear answer, skipping")
        self._speak("No clear answer, skipping that.")
        return False
