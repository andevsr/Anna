from __future__ import annotations

import time

import Quartz
from Quartz import (
    CGEventCreateMouseEvent,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseDragged,
    kCGEventLeftMouseUp,
    kCGEventMouseMoved,
    kCGEventOtherMouseDown,
    kCGEventOtherMouseDragged,
    kCGEventOtherMouseUp,
    kCGEventRightMouseDown,
    kCGEventRightMouseDragged,
    kCGEventRightMouseUp,
    kCGHIDEventTap,
    kCGMouseButtonCenter,
    kCGMouseButtonLeft,
    kCGMouseButtonRight,
)

_BUTTONS = {
    "left": (kCGEventLeftMouseDown, kCGEventLeftMouseUp, kCGMouseButtonLeft),
    "right": (kCGEventRightMouseDown, kCGEventRightMouseUp, kCGMouseButtonRight),
    "middle": (kCGEventOtherMouseDown, kCGEventOtherMouseUp, kCGMouseButtonCenter),
}

_DRAG = {
    "left": kCGEventLeftMouseDragged,
    "right": kCGEventRightMouseDragged,
    "middle": kCGEventOtherMouseDragged,
}


def _post(event) -> None:
    Quartz.CGEventPost(kCGHIDEventTap, event)


def move(x: int, y: int) -> None:
    _post(CGEventCreateMouseEvent(None, kCGEventMouseMoved, (x, y), kCGMouseButtonLeft))


def click(x: int, y: int, button: str = "left", double: bool = False) -> None:
    down, up, btn = _BUTTONS[button]
    move(x, y)
    time.sleep(0.02)
    count = 2 if double else 1
    for _ in range(count):
        _post(CGEventCreateMouseEvent(None, down, (x, y), btn))
        _post(CGEventCreateMouseEvent(None, up, (x, y), btn))
        time.sleep(0.05)


def drag(
    start_x: int, start_y: int, end_x: int, end_y: int, button: str = "left"
) -> None:
    down, up, btn = _BUTTONS[button]
    drag_event = _DRAG[button]
    move(start_x, start_y)
    time.sleep(0.02)
    _post(CGEventCreateMouseEvent(None, down, (start_x, start_y), btn))
    steps = 20
    for i in range(1, steps + 1):
        x = int(start_x + (end_x - start_x) * i / steps)
        y = int(start_y + (end_y - start_y) * i / steps)
        _post(CGEventCreateMouseEvent(None, drag_event, (x, y), btn))
        time.sleep(0.01)
    _post(CGEventCreateMouseEvent(None, up, (end_x, end_y), btn))


def scroll(dx: int, dy: int, x: int | None = None, y: int | None = None) -> None:
    if x is not None and y is not None:
        move(x, y)
        time.sleep(0.02)
    event = Quartz.CGEventCreateScrollWheelEvent(
        None, Quartz.kCGScrollEventUnitLine, 2, dy, dx
    )
    _post(event)
