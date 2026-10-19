from __future__ import annotations

from anna.audio.capture import Microphone
from anna.audio.listener import SpeechListener
from anna.audio.stt import Transcriber
from anna.audio.tts import speak
from anna.audio.vad import VAD
from anna.audio.wakeword import extract_command


class VoiceLoop:
    def __init__(
        self,
        agent,
        stt: Transcriber,
        wake_word: str = "hey anna",
        command_timeout_s: float = 8.0,
        tts: bool = True,
    ) -> None:
        self.agent = agent
        self.stt = stt
        self.wake_word = wake_word
        self.command_timeout_s = command_timeout_s
        self.tts = tts

    def run(self) -> None:
        print("Warming up speech recognition (first run downloads the model)...")
        try:
            self.stt.warmup()
        except Exception as e:
            print(f"[warn] STT warmup failed: {e}")

        print(f'Listening for wake word "{self.wake_word}"... (Ctrl+C to quit)')
        with Microphone() as mic:
            listener = SpeechListener(mic, VAD())
            while True:
                utt = listener.listen(timeout_s=None)
                text = self.stt.transcribe(utt)
                if not text:
                    continue
                print(f"[heard] {text}")

                command = extract_command(text, self.wake_word)
                if command is None:
                    continue

                if not command:
                    if self.tts:
                        speak("Yes?")
                    command = self._listen_command(listener)
                    if not command:
                        print(f'Listening for wake word "{self.wake_word}"...')
                        continue

                print(f"[command] {command}")
                try:
                    result = self.agent.run(command)
                except Exception as e:
                    print(f"[error] {e}")
                    result = ""
                if result:
                    print(result)
                    if self.tts:
                        speak(result)
                mic.drain()
                print(f'Listening for wake word "{self.wake_word}"...')

    def _listen_command(self, listener: SpeechListener) -> str | None:
        utt = listener.listen(timeout_s=self.command_timeout_s)
        if utt is None:
            return None
        text = self.stt.transcribe(utt)
        if not text:
            return None
        print(f"[heard] {text}")
        return extract_command(text, self.wake_word) or text
