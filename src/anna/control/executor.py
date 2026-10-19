from __future__ import annotations

import time

from anna.actions import (
    AskUser,
    Click,
    Done,
    Drag,
    Key,
    MouseMove,
    OpenApp,
    Scroll,
    Shell,
    Type,
    Wait,
)
from anna.control import apps, keyboard, mouse


def _pt(x: float, y: float, scale: float) -> tuple[int, int]:
    return int(round(x / scale)), int(round(y / scale))


def execute(action, scale: float) -> str:
    if isinstance(action, MouseMove):
        x, y = _pt(action.x, action.y, scale)
        mouse.move(x, y)
        return f"moved mouse to ({action.x}, {action.y})"

    if isinstance(action, Click):
        x, y = _pt(action.x, action.y, scale)
        mouse.click(x, y, action.button, action.double)
        suffix = " (double)" if action.double else ""
        return f"clicked {action.button}{suffix} at ({action.x}, {action.y})"

    if isinstance(action, Drag):
        sx, sy = _pt(action.start_x, action.start_y, scale)
        ex, ey = _pt(action.end_x, action.end_y, scale)
        mouse.drag(sx, sy, ex, ey, action.button)
        return f"dragged {action.button} from ({action.start_x}, {action.start_y}) to ({action.end_x}, {action.end_y})"

    if isinstance(action, Type):
        keyboard.type_text(action.text)
        return f"typed {action.text!r}"

    if isinstance(action, Key):
        keyboard.press(action.keys)
        return f"pressed keys {action.keys}"

    if isinstance(action, Scroll):
        x, y = _pt(action.x, action.y, scale)
        mouse.scroll(action.dx, action.dy, x, y)
        return f"scrolled ({action.dx}, {action.dy}) at ({action.x}, {action.y})"

    if isinstance(action, Wait):
        time.sleep(action.ms / 1000)
        return f"waited {action.ms}ms"

    if isinstance(action, OpenApp):
        result = apps.open_app(action.name)
        return f"open_app {action.name}: {result}"

    if isinstance(action, Shell):
        result = apps.run_shell(action.command)
        return f"shell `{action.command}` -> {result[:200]}"

    if isinstance(action, AskUser):
        return f"asked user: {action.question}"

    if isinstance(action, Done):
        return f"done: {action.summary}"

    raise ValueError(f"Unknown action type: {type(action).__name__}")
