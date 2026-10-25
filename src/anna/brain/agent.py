from __future__ import annotations

import json
import time

import httpx
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from pydantic import ValidationError

from anna.actions import AskUser, Done, parse_action
from anna.control import screen
from anna.control.executor import execute
from anna.interaction import Interaction, TextInteraction
from anna.safety.audit import AuditLog
from anna.safety.policy import Decision, Policy

_TRANSIENT_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)

_TRANSIENT_STATUS = {408, 409, 429, 500, 502, 503, 504}

_REPEAT_EXEMPT = {"wait", "scroll", "mouse_move"}


def _is_transient(error: Exception) -> bool:
    if isinstance(error, _TRANSIENT_ERRORS):
        return True
    if isinstance(error, httpx.TransportError):
        return True
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    if status is None:
        status = getattr(error, "status_code", None)
    return status in _TRANSIENT_STATUS


class Agent:
    def __init__(
        self,
        provider,
        max_steps: int = 25,
        policy: Policy | None = None,
        interaction: Interaction | None = None,
        audit: AuditLog | None = None,
        capture_fn=None,
        retry_attempts: int = 3,
        retry_delay: float = 0.5,
    ) -> None:
        self.provider = provider
        self.max_steps = max_steps
        self.policy = policy or Policy()
        self.interaction = interaction or TextInteraction()
        self.audit = audit or AuditLog()
        self._capture = capture_fn or screen.capture
        self.retry_attempts = max(1, retry_attempts)
        self.retry_delay = retry_delay

    def run(self, goal: str) -> str:
        goal = goal.strip()
        if not goal:
            return "No instruction provided."

        history: list[dict] = []
        last_signature: str | None = None
        repeats = 0
        invalid_actions = 0

        for step in range(1, self.max_steps + 1):
            shot = self._capture_screen()

            try:
                raw = self._request(goal, history, shot.to_base64())
                action = parse_action(raw)
            except (ValidationError, json.JSONDecodeError, TypeError) as exc:
                invalid_actions += 1
                note = f"invalid action: {exc}"
                print(f"[invalid] {note}")
                history.append({"action": "invalid", "note": note})
                self.audit.record(
                    goal=goal,
                    step=step,
                    action=None,
                    decision="invalid",
                    reason=note,
                )
                if invalid_actions >= 3:
                    return "Stopped: the model produced invalid actions three times."
                continue
            invalid_actions = 0

            if isinstance(action, Done):
                summary = action.summary or "Done."
                print(f"[done] {summary}")
                self.audit.record(
                    goal=goal,
                    step=step,
                    action=action,
                    decision="done",
                    outcome=summary,
                )
                return summary

            if isinstance(action, AskUser):
                answer = self.interaction.ask(action.question)
                note = f"ask_user: {action.question!r} -> {answer!r}"
                history.append({"action": action.action, "note": note})
                self.audit.record(
                    goal=goal,
                    step=step,
                    action=action,
                    decision="ask_user",
                    outcome=note,
                )
                continue

            signature = json.dumps(action.model_dump(), sort_keys=True)
            if signature == last_signature:
                repeats += 1
            else:
                last_signature = signature
                repeats = 1

            if action.action not in _REPEAT_EXEMPT and repeats >= 3:
                warning = (
                    f"you have repeated {action.action!r} {repeats} times; "
                    "change approach or ask the user"
                )
                print(f"[warn] {warning}")
                history.append({"action": "system", "note": warning})
                self.audit.record(
                    goal=goal,
                    step=step,
                    action=action,
                    decision="repeat-warning",
                    reason=warning,
                )
                if repeats >= 5:
                    return (
                        f"Stopped: repeated {action.action!r} {repeats} times "
                        "without making progress."
                    )

            verdict = self.policy.evaluate(action)
            if verdict.decision is Decision.DENY:
                print(f"[blocked] {verdict.reason}")
                note = f"blocked by policy: {verdict.reason}"
                history.append({"action": action.action, "note": note})
                self.audit.record(
                    goal=goal,
                    step=step,
                    action=action,
                    decision="deny",
                    reason=verdict.reason,
                    outcome="blocked",
                )
                continue

            if verdict.decision is Decision.CONFIRM:
                description = self.policy.describe(action)
                approved = self.interaction.confirm(description, verdict.reason)
                if not approved:
                    print("[skipped] not approved")
                    note = f"skipped by user: {verdict.reason}"
                    history.append({"action": action.action, "note": note})
                    self.audit.record(
                        goal=goal,
                        step=step,
                        action=action,
                        decision="confirm",
                        reason=verdict.reason,
                        outcome="denied",
                    )
                    continue

            try:
                result = execute(action, shot.scale)
            except Exception as exc:
                print(f"[error] {exc}")
                note = f"action failed: {exc}"
                history.append({"action": action.action, "note": note})
                self.audit.record(
                    goal=goal,
                    step=step,
                    action=action,
                    decision=verdict.decision.value,
                    reason=verdict.reason,
                    outcome="error",
                    error=str(exc),
                )
                continue

            print(f"[step {step}] {result}")
            note = f"{action.action}: {result}"
            history.append({"action": action.action, "note": note})
            self.audit.record(
                goal=goal,
                step=step,
                action=action,
                decision=verdict.decision.value,
                reason=verdict.reason,
                outcome=result,
            )

        return f"Reached max steps ({self.max_steps}) without completing the goal."

    def _capture_screen(self):
        try:
            return self._capture()
        except Exception as exc:
            raise RuntimeError(
                "Could not capture the screen. Grant Screen Recording permission "
                "to your terminal in System Settings, then restart it."
            ) from exc

    def _request(self, goal: str, history: list[dict], screenshot_b64: str) -> dict:
        delay = self.retry_delay
        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                return self.provider.next_action(goal, history, screenshot_b64)
            except Exception as exc:
                last_error = exc
                if attempt >= self.retry_attempts or not _is_transient(exc):
                    raise
                print(f"[retry] provider error ({exc}); retrying in {delay:.1f}s")
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("provider request failed") from last_error
