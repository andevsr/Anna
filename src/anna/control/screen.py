from __future__ import annotations

import base64
import io
from dataclasses import dataclass

import Quartz
import mss
from PIL import Image


@dataclass
class Screenshot:
    image: Image.Image
    scale: float

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height

    def to_points(self, x: float, y: float) -> tuple[int, int]:
        return int(round(x / self.scale)), int(round(y / self.scale))

    def to_png_bytes(self) -> bytes:
        buf = io.BytesIO()
        self.image.save(buf, format="PNG")
        return buf.getvalue()

    def to_base64(self) -> str:
        return base64.b64encode(self.to_png_bytes()).decode()


def display_scale() -> float:
    main = Quartz.CGMainDisplayID()
    w_px = Quartz.CGDisplayPixelsWide(main)
    bounds = Quartz.CGDisplayBounds(main)
    return w_px / bounds.size.width


def capture() -> Screenshot:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        image = Image.frombytes("RGB", shot.size, shot.rgb)
    return Screenshot(image=image, scale=display_scale())
