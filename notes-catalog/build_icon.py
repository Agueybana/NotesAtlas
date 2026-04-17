from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
ICONSET = ROOT / "NotesAtlas.iconset"


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def vertical_gradient(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGBA", (size, size))
    px = img.load()
    for y in range(size):
        t = y / max(size - 1, 1)
        color = tuple(lerp(top[i], bottom[i], t) for i in range(3)) + (255,)
        for x in range(size):
            px[x, y] = color
    return img


def rounded_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill, outline=None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def build_master_icon(size: int = 1024) -> Image.Image:
    img = vertical_gradient(size, (246, 239, 229), (236, 227, 214))
    draw = ImageDraw.Draw(img)

    for i in range(7):
        alpha = int(18 - i * 2)
        offset = int(size * (0.05 + i * 0.018))
        draw.arc(
            (offset, offset, size - offset, size - offset),
            start=190,
            end=350,
            fill=(15, 107, 98, alpha),
            width=max(1, size // 150),
        )

    orb = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    orb_draw = ImageDraw.Draw(orb)
    orb_draw.ellipse(
        (size * 0.58, size * 0.07, size * 0.98, size * 0.47),
        fill=(218, 139, 65, 48),
    )
    orb = orb.filter(ImageFilter.GaussianBlur(radius=size // 18))
    img.alpha_composite(orb)

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    note_box = (
        int(size * 0.18),
        int(size * 0.13),
        int(size * 0.82),
        int(size * 0.87),
    )
    rounded_rect(shadow_draw, (note_box[0], note_box[1] + size // 36, note_box[2], note_box[3] + size // 36), size // 16, fill=(80, 58, 30, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=size // 30))
    img.alpha_composite(shadow)

    note = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    note_draw = ImageDraw.Draw(note)
    rounded_rect(note_draw, note_box, size // 15, fill=(255, 251, 246, 255), outline=(213, 199, 182, 255), width=size // 170)

    fold = [
        (int(size * 0.66), int(size * 0.13)),
        (int(size * 0.82), int(size * 0.13)),
        (int(size * 0.82), int(size * 0.29)),
    ]
    note_draw.polygon(fold, fill=(240, 231, 221, 255))
    note_draw.line([fold[0], fold[1], fold[2]], fill=(213, 199, 182, 255), width=size // 170)

    line_color = (164, 151, 134, 210)
    for y in range(0, 5):
        yy = int(size * (0.28 + y * 0.09))
        note_draw.rounded_rectangle(
            (int(size * 0.27), yy, int(size * 0.74), yy + size // 90),
            radius=size // 110,
            fill=line_color,
        )

    ring_center = (int(size * 0.42), int(size * 0.42))
    outer_r = int(size * 0.13)
    inner_r = int(size * 0.08)
    note_draw.ellipse(
        (ring_center[0] - outer_r, ring_center[1] - outer_r, ring_center[0] + outer_r, ring_center[1] + outer_r),
        outline=(15, 107, 98, 255),
        width=size // 45,
    )
    note_draw.ellipse(
        (ring_center[0] - inner_r, ring_center[1] - inner_r, ring_center[0] + inner_r, ring_center[1] + inner_r),
        outline=(15, 107, 98, 195),
        width=size // 80,
    )
    for angle in (0, 90, 45, 135):
        radians = math.radians(angle)
        x1 = ring_center[0] + math.cos(radians) * inner_r
        y1 = ring_center[1] + math.sin(radians) * inner_r
        x2 = ring_center[0] + math.cos(radians) * outer_r
        y2 = ring_center[1] + math.sin(radians) * outer_r
        note_draw.line((x1, y1, x2, y2), fill=(15, 107, 98, 220), width=size // 90)

    pin_top = (int(size * 0.58), int(size * 0.39))
    pin_bottom = (int(size * 0.58), int(size * 0.61))
    note_draw.ellipse(
        (pin_top[0] - size // 18, pin_top[1] - size // 18, pin_top[0] + size // 18, pin_top[1] + size // 18),
        fill=(218, 139, 65, 255),
    )
    note_draw.ellipse(
        (pin_top[0] - size // 34, pin_top[1] - size // 34, pin_top[0] + size // 34, pin_top[1] + size // 34),
        fill=(255, 244, 232, 255),
    )
    note_draw.polygon(
        [
            (pin_top[0], pin_bottom[1]),
            (pin_top[0] - size // 26, pin_top[1] + size // 38),
            (pin_top[0] + size // 26, pin_top[1] + size // 38),
        ],
        fill=(218, 139, 65, 255),
    )

    img.alpha_composite(note)
    return img


def main() -> None:
    ICONSET.mkdir(parents=True, exist_ok=True)
    master = build_master_icon(1024)
    sizes = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    for filename, px in sizes.items():
        master.resize((px, px), Image.Resampling.LANCZOS).save(ICONSET / filename)


if __name__ == "__main__":
    main()
