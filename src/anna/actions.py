from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter


class MouseMove(BaseModel):
    action: Literal["mouse_move"] = "mouse_move"
    x: int
    y: int


class Click(BaseModel):
    action: Literal["click"] = "click"
    x: int
    y: int
    button: Literal["left", "right", "middle"] = "left"
    double: bool = False


class Drag(BaseModel):
    action: Literal["drag"] = "drag"
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    button: Literal["left", "right", "middle"] = "left"


class Type(BaseModel):
    action: Literal["type"] = "type"
    text: str


class Key(BaseModel):
    action: Literal["key"] = "key"
    keys: list[str]


class Scroll(BaseModel):
    action: Literal["scroll"] = "scroll"
    x: int
    y: int
    dx: int = 0
    dy: int = 0


class Wait(BaseModel):
    action: Literal["wait"] = "wait"
    ms: int = 500


class OpenApp(BaseModel):
    action: Literal["open_app"] = "open_app"
    name: str


class Shell(BaseModel):
    action: Literal["shell"] = "shell"
    command: str


class AskUser(BaseModel):
    action: Literal["ask_user"] = "ask_user"
    question: str


class Done(BaseModel):
    action: Literal["done"] = "done"
    summary: str


Action = Annotated[
    MouseMove
    | Click
    | Drag
    | Type
    | Key
    | Scroll
    | Wait
    | OpenApp
    | Shell
    | AskUser
    | Done,
    Field(discriminator="action"),
]

_action_adapter = TypeAdapter(Action)


def parse_action(data: dict) -> Action:
    return _action_adapter.validate_python(data)
