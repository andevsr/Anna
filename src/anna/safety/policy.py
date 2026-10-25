from __future__ import annotations

import re
import shlex
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

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


class Decision(StrEnum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


@dataclass(frozen=True)
class PolicyResult:
    decision: Decision
    reason: str = ""
    risk: str = "low"


_ALLOW = PolicyResult(Decision.ALLOW)

_TERMINAL_NAMES = re.compile(
    r"terminal|iterm|warp|alacritty|kitty|wezterm|ghostty|hyper|tabby|"
    r"vscode|visual studio code|cursor|windsurf|jetbrains|pycharm|intellij",
    re.IGNORECASE,
)

_SENSITIVE_PATHS = re.compile(
    r"(^|/)(\.ssh|\.aws|\.gnupg|\.netrc|\.git-credentials|\.docker|\.kube|"
    r"library/keychains|\.config/gh)(/|$)|(^|/)\.env(\.|$)|"
    r"(^|/)id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$|\.p12$|\.pfx$|keychain",
    re.IGNORECASE,
)

_DENY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsudo\b"), "sudo is not allowed"),
    (re.compile(r"\bdoas\b"), "doas is not allowed"),
    (re.compile(r"\bsu\s+-"), "switching users is not allowed"),
    (
        re.compile(r"\brm\s+(?:-[a-z]*[rf][a-z]*\s+)+(?:/|~|\$home)(?:\s|$)"),
        "recursive delete of the root or home directory",
    ),
    (re.compile(r":\s*\(\s*\)\s*\{.*?\}\s*;\s*:"), "fork bomb"),
    (re.compile(r"\bdd\b[^\n]*\bof=/dev/"), "writing raw data to a device"),
    (re.compile(r"\bmkfs(?:\.\w+)?\b"), "formatting a filesystem"),
    (
        re.compile(
            r"\bdiskutil\s+(?:erase\w*|partitiondisk|zerodisk|secureerase|reformat)\b"
        ),
        "erasing a disk",
    ),
    (
        re.compile(r"\b(?:shutdown|reboot|halt|poweroff)\b"),
        "shutting down or restarting the machine",
    ),
    (
        re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh)\b"),
        "piping a download into a shell",
    ),
    (re.compile(r">\s*/dev/(?:sd|disk|rdisk)"), "writing to a raw disk device"),
    (re.compile(r"\bcsrutil\s+disable\b"), "disabling system integrity protection"),
    (re.compile(r"\bkill\s+-9\s+1\b"), "killing the init process"),
    (re.compile(r"\bchmod\s+-r\s+777\s+/\s*$"), "making the filesystem world-writable"),
]

_DENY_PROGRAMS = {
    "sudo",
    "doas",
    "su",
    "dd",
    "mkfs",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "fdisk",
    "gdisk",
}

_CONFIRM_PROGRAMS = {
    "rm",
    "rmdir",
    "mv",
    "cp",
    "ln",
    "touch",
    "mkdir",
    "chmod",
    "chown",
    "chgrp",
    "tee",
    "truncate",
    "kill",
    "killall",
    "pkill",
    "launchctl",
    "crontab",
    "at",
    "systemsetup",
    "softwareupdate",
    "brew",
    "pip",
    "pip3",
    "uv",
    "npm",
    "pnpm",
    "yarn",
    "cargo",
    "make",
    "go",
    "node",
    "python",
    "python3",
    "ruby",
    "perl",
    "bash",
    "sh",
    "zsh",
    "fish",
    "osascript",
    "security",
    "xattr",
    "defaults",
    "scutil",
    "nvram",
    "csrutil",
    "spctl",
    "tccutil",
    "pmset",
    "networksetup",
    "ifconfig",
    "route",
    "pfctl",
    "mysql",
    "psql",
    "sqlite3",
    "git",
    "env",
    "printenv",
}

_READ_ONLY_PROGRAMS = {
    "pwd",
    "ls",
    "whoami",
    "date",
    "cal",
    "uname",
    "sw_vers",
    "hostname",
    "which",
    "whereis",
    "echo",
    "printf",
    "cat",
    "head",
    "tail",
    "wc",
    "grep",
    "egrep",
    "fgrep",
    "rg",
    "stat",
    "file",
    "du",
    "df",
    "ps",
    "pgrep",
    "uptime",
    "mdfind",
    "basename",
    "dirname",
    "realpath",
    "readlink",
    "true",
    "false",
}

_ALLOW_PROGRAMS = _READ_ONLY_PROGRAMS | {"cd", "export", "unset", "history", "open"}

_GIT_READ_ONLY = {
    "status",
    "log",
    "diff",
    "show",
    "blame",
    "rev-parse",
    "describe",
}

_SAFE_KEY_ALIASES = {
    "cmd": "cmd",
    "command": "cmd",
    "shift": "shift",
    "option": "opt",
    "alt": "opt",
    "ctrl": "ctrl",
    "control": "ctrl",
    "fn": "fn",
}

_DANGEROUS_KEY_COMBOS = [
    {"cmd", "ctrl", "q"},
    {"cmd", "shift", "q"},
    {"cmd", "opt", "esc"},
    {"cmd", "ctrl", "power"},
]

_TEXT_KEYS = set("abcdefghijklmnopqrstuvwxyz0123456789`-=[]\\;',./")
_TEXT_KEYS |= {
    "return",
    "enter",
    "space",
    "tab",
    "backspace",
    "delete",
    "power",
}

_OPERATOR_CHARS = set("|&;()<>")


def _default_frontmost_app() -> str | None:
    try:
        from AppKit import NSWorkspace

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
    except Exception:
        return None
    if app is None:
        return None
    name = app.localizedName() or ""
    bundle = app.bundleIdentifier() or ""
    return f"{name} {bundle}".strip()


def is_terminal_app(app: str | None) -> bool:
    return bool(app and _TERMINAL_NAMES.search(app))


def _segments(command: str) -> list[list[str]] | None:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return None

    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token and all(char in _OPERATOR_CHARS for char in token):
            if current:
                segments.append(current)
                current = []
            continue
        current.append(token)
    if current:
        segments.append(current)
    return segments


def _strip_assignments(tokens: list[str]) -> list[str]:
    while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
        tokens = tokens[1:]
    return tokens


def _has_sensitive_arg(args: list[str]) -> bool:
    return any(_SENSITIVE_PATHS.search(arg) for arg in args)


def _git_is_read_only(args: list[str]) -> bool:
    if not args:
        return True
    subcommand = args[0].lower()
    if subcommand not in _GIT_READ_ONLY:
        return False
    if subcommand == "diff" and any(arg.startswith("--output") for arg in args):
        return False
    return True


def _defaults_is_read_only(args: list[str]) -> bool:
    if not args:
        return False
    return args[0].lower() in {"read", "read-type", "domains", "find"}


def _find_is_read_only(args: list[str]) -> bool:
    return not any(
        arg in {"-exec", "-execdir", "-ok", "-okdir", "-delete"} for arg in args
    )


def _classify_segment(tokens: list[str]) -> PolicyResult:
    tokens = _strip_assignments(tokens)
    if not tokens:
        return _ALLOW

    program = tokens[0].rsplit("/", 1)[-1].lower()
    args = tokens[1:]

    if program in _DENY_PROGRAMS:
        return PolicyResult(Decision.DENY, f"`{program}` is not allowed", "high")

    if program == "diskutil":
        if any(
            arg.lower().startswith(
                ("erase", "partitiondisk", "zerodisk", "secureerase")
            )
            for arg in args
        ):
            return PolicyResult(Decision.DENY, "erasing a disk", "high")
        return PolicyResult(Decision.CONFIRM, "running diskutil", "medium")

    if program == "rm":
        flags = "".join(arg[1:] for arg in args if arg.startswith("-"))
        targets = [arg for arg in args if not arg.startswith("-")]
        if "r" in flags.lower() and any(
            target in {"/", "~", "$HOME"} for target in targets
        ):
            return PolicyResult(
                Decision.DENY, "recursive delete of the root or home directory", "high"
            )
        return PolicyResult(Decision.CONFIRM, "deleting files", "medium")

    if program == "git":
        if _git_is_read_only(args):
            if _has_sensitive_arg(args):
                return PolicyResult(
                    Decision.CONFIRM, "reading a sensitive path", "medium"
                )
            return _ALLOW
        return PolicyResult(
            Decision.CONFIRM, "running a mutating git command", "medium"
        )

    if program == "defaults":
        if _defaults_is_read_only(args):
            return _ALLOW
        return PolicyResult(Decision.CONFIRM, "writing macOS defaults", "medium")

    if program == "find":
        if _find_is_read_only(args):
            if _has_sensitive_arg(args):
                return PolicyResult(
                    Decision.CONFIRM, "reading a sensitive path", "medium"
                )
            return _ALLOW
        return PolicyResult(
            Decision.CONFIRM, "running find with side effects", "medium"
        )

    if program == "sed":
        if any(arg == "-i" or arg.startswith("-i") for arg in args):
            return PolicyResult(Decision.CONFIRM, "editing files in place", "medium")
        if _has_sensitive_arg(args):
            return PolicyResult(Decision.CONFIRM, "reading a sensitive path", "medium")
        return _ALLOW

    if program == "xattr":
        if any(arg in {"-l", "-p"} for arg in args):
            return _ALLOW
        return PolicyResult(Decision.CONFIRM, "modifying file attributes", "medium")

    if program in _ALLOW_PROGRAMS:
        if _has_sensitive_arg(args):
            return PolicyResult(Decision.CONFIRM, "reading a sensitive path", "medium")
        return _ALLOW

    if program in _CONFIRM_PROGRAMS:
        return PolicyResult(Decision.CONFIRM, f"running `{program}`", "medium")

    return PolicyResult(
        Decision.CONFIRM, f"running unknown command `{program}`", "medium"
    )


def _classify_shell(command: str) -> PolicyResult:
    if not command.strip():
        return _ALLOW

    lowered = command.lower()
    for pattern, reason in _DENY_PATTERNS:
        if pattern.search(lowered):
            return PolicyResult(Decision.DENY, reason, "high")

    if "$(" in command or "`" in command or "<(" in command:
        return PolicyResult(
            Decision.CONFIRM, "shell command contains command substitution", "medium"
        )

    segments = _segments(command)
    if segments is None:
        return PolicyResult(Decision.CONFIRM, "could not parse shell command", "medium")

    first_confirm: PolicyResult | None = None
    for segment in segments:
        result = _classify_segment(segment)
        if result.decision is Decision.DENY:
            return result
        if result.decision is Decision.CONFIRM and first_confirm is None:
            first_confirm = result

    if first_confirm is not None:
        return first_confirm
    return _ALLOW


def describe(action) -> str:
    if isinstance(action, Shell):
        return f"run shell command: {action.command!r}"
    if isinstance(action, Type):
        preview = action.text if len(action.text) <= 80 else action.text[:77] + "..."
        return f"type text: {preview!r}"
    if isinstance(action, Key):
        return f"press keys: {'+'.join(action.keys)}"
    if isinstance(action, Click):
        button = "double-click" if action.double else "click"
        return f"{button} {action.button} at ({action.x}, {action.y})"
    if isinstance(action, Drag):
        return (
            f"drag {action.button} from ({action.start_x}, {action.start_y}) "
            f"to ({action.end_x}, {action.end_y})"
        )
    if isinstance(action, Scroll):
        return f"scroll ({action.dx}, {action.dy}) at ({action.x}, {action.y})"
    if isinstance(action, MouseMove):
        return f"move mouse to ({action.x}, {action.y})"
    if isinstance(action, OpenApp):
        return f"open app {action.name!r}"
    if isinstance(action, Wait):
        return f"wait {action.ms}ms"
    if isinstance(action, AskUser):
        return f"ask the user: {action.question!r}"
    if isinstance(action, Done):
        return f"finish: {action.summary!r}"
    return getattr(action, "action", type(action).__name__)


def _normalized_keys(keys: list[str]) -> set[str]:
    normalized = set()
    for key in keys:
        lowered = key.lower()
        normalized.add(_SAFE_KEY_ALIASES.get(lowered, lowered))
    return normalized


def _key_types_input(keys: list[str]) -> bool:
    modifiers = {
        _SAFE_KEY_ALIASES.get(key.lower(), key.lower())
        for key in keys
        if key.lower() in _SAFE_KEY_ALIASES
    }
    if modifiers & {"cmd", "ctrl"}:
        return False
    for key in keys:
        lowered = key.lower()
        if lowered in _SAFE_KEY_ALIASES or lowered in {"esc", "escape"}:
            continue
        if lowered in _TEXT_KEYS or len(lowered) == 1:
            return True
        if lowered.startswith("f") and lowered[1:].isdigit():
            continue
        if lowered in {
            "up",
            "down",
            "left",
            "right",
            "home",
            "end",
            "pageup",
            "pagedown",
        }:
            continue
    return False


class Policy:
    def __init__(
        self,
        frontmost_app: Callable[[], str | None] | None = None,
    ) -> None:
        self._frontmost_app = frontmost_app or _default_frontmost_app

    def _frontmost_is_terminal(self) -> bool:
        try:
            return is_terminal_app(self._frontmost_app())
        except Exception:
            return False

    def evaluate(self, action) -> PolicyResult:
        if isinstance(action, Shell):
            return _classify_shell(action.command)

        if isinstance(action, Type):
            if self._frontmost_is_terminal():
                return PolicyResult(
                    Decision.CONFIRM,
                    "the frontmost app is a terminal, so typing may run a command",
                    "high",
                )
            return _ALLOW

        if isinstance(action, Key):
            keys = _normalized_keys(action.keys)
            for combo in _DANGEROUS_KEY_COMBOS:
                if combo.issubset(keys):
                    return PolicyResult(
                        Decision.CONFIRM,
                        f"pressing {'+'.join(sorted(keys))} can log out or lock the Mac",
                        "high",
                    )
            if self._frontmost_is_terminal() and _key_types_input(action.keys):
                return PolicyResult(
                    Decision.CONFIRM,
                    "the frontmost app is a terminal, so this key may run a command",
                    "high",
                )
            return _ALLOW

        return _ALLOW

    def describe(self, action) -> str:
        return describe(action)
