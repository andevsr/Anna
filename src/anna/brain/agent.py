from __future__ import annotations

from anna.actions import AskUser, Done, parse_action
from anna.control import screen
from anna.control.executor import execute
from anna.safety.policy import Policy


class Agent:
    def __init__(
        self, provider, max_steps: int = 25, policy: Policy | None = None
    ) -> None:
        self.provider = provider
        self.max_steps = max_steps
        self.policy = policy or Policy()

    def run(self, goal: str) -> str:
        history: list[dict] = []
        for step in range(1, self.max_steps + 1):
            shot = screen.capture()
            b64 = shot.to_base64()

            raw = self.provider.next_action(goal, history, b64)
            action = parse_action(raw)

            if isinstance(action, Done):
                print(f"[done] {action.summary}")
                return action.summary

            if isinstance(action, AskUser):
                print(f"[ask_user] {action.question}")
                answer = input("Answer (or 'skip'): ").strip()
                history.append(
                    {
                        "action": "ask_user",
                        "note": f"question={action.question!r} answer={answer!r}",
                    }
                )
                continue

            reason = self.policy.needs_confirmation(action)
            if reason:
                print(f"[confirm] {reason}")
                answer = input("Approve? [y/N]: ").strip().lower()
                if answer != "y":
                    history.append(
                        {"action": action.action, "note": "skipped (not approved)"}
                    )
                    continue

            note = execute(action, shot.scale)
            print(f"[step {step}] {note}")
            history.append({"action": action.action, "note": note})

        return "Reached max steps."
