from __future__ import annotations

import time

import Quartz
from Quartz import CGEventCreateKeyboardEvent, CGEventPost, kCGHIDEventTap

_MODIFIERS = {
    "cmd": Quartz.kCGEventFlagMaskCommand,
    "command": Quartz.kCGEventFlagMaskCommand,
    "shift": Quartz.kCGEventFlagMaskShift,
    "option": Quartz.kCGEventFlagMaskAlternate,
    "alt": Quartz.kCGEventFlagMaskAlternate,
    "ctrl": Quartz.kCGEventFlagMaskControl,
    "control": Quartz.kCGEventFlagMaskControl,
}

_KEYCODES = {
    "a": 0,
    "s": 1,
    "d": 2,
    "f": 3,
    "h": 4,
    "g": 5,
    "z": 6,
    "x": 7,
    "c": 8,
    "v": 9,
    "b": 11,
    "q": 12,
    "w": 13,
    "e": 14,
    "r": 15,
    "y": 16,
    "t": 17,
    "1": 18,
    "2": 19,
    "3": 20,
    "4": 21,
    "6": 22,
    "5": 23,
    "=": 24,
    "9": 25,
    "7": 26,
    "-": 27,
    "8": 28,
    "0": 29,
    "]": 30,
    "o": 31,
    "u": 32,
    "[": 33,
    "i": 34,
    "p": 35,
    "return": 36,
    "enter": 36,
    "l": 37,
    "j": 38,
    "'": 39,
    "k": 40,
    ";": 41,
    "\\": 42,
    ",": 43,
    "/": 44,
    "n": 45,
    "m": 46,
    ".": 47,
    "tab": 48,
    "space": 49,
    "`": 50,
    "backspace": 51,
    "delete": 51,
    "esc": 53,
    "escape": 53,
    "up": 126,
    "down": 125,
    "left": 123,
    "right": 124,
    "home": 115,
    "end": 119,
    "pageup": 116,
    "pagedown": 121,
    "f1": 122,
    "f2": 120,
    "f3": 99,
    "f4": 118,
    "f5": 96,
    "f6": 97,
    "f7": 98,
    "f8": 100,
    "f9": 101,
    "f10": 109,
    "f11": 103,
    "f12": 111,
}


def type_text(text: str) -> None:
    down = CGEventCreateKeyboardEvent(None, 0, True)
    Quartz.CGEventKeyboardSetUnicodeString(down, len(text), text)
    CGEventPost(kCGHIDEventTap, down)
    up = CGEventCreateKeyboardEvent(None, 0, False)
    Quartz.CGEventKeyboardSetUnicodeString(up, len(text), text)
    CGEventPost(kCGHIDEventTap, up)


def _post_key(code: int, flags: int) -> None:
    down = CGEventCreateKeyboardEvent(None, code, True)
    if flags:
        Quartz.CGEventSetFlags(down, flags)
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.02)
    up = CGEventCreateKeyboardEvent(None, code, False)
    if flags:
        Quartz.CGEventSetFlags(up, flags)
    CGEventPost(kCGHIDEventTap, up)


def press(keys: list[str]) -> None:
    modifiers: list[str] = []
    main_key: str | None = None
    for k in keys:
        lowered = k.lower()
        if lowered in _MODIFIERS:
            modifiers.append(lowered)
        else:
            main_key = lowered

    flags = 0
    for m in modifiers:
        flags |= _MODIFIERS[m]

    if main_key is not None and main_key in _KEYCODES:
        _post_key(_KEYCODES[main_key], flags)
    elif main_key is not None:
        type_text(main_key)
