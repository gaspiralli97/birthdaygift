"""Open Graph preview images.

When a card link is pasted into Telegram, WhatsApp or iMessage, this is what
the recipient actually sees first - so it is drawn to match the card itself:
same palette, same big number, same row of candles.

Fonts are chosen per string by script. The bundled faces cover Latin, the Uzbek
okina and Cyrillic; Hangul comes from a system CJK font, because every font that
covers Korean is far too large to keep in a repository.
"""

from __future__ import annotations

import contextlib
import logging
import math
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import Card
from .themes import Theme, get_theme

logger = logging.getLogger(__name__)

WIDTH, HEIGHT = 1200, 630
PAD = 90

_FONTS = Path(__file__).parent / "static" / "fonts"
_DISPLAY = _FONTS / "BigShouldersDisplay.ttf"
_SERIF = _FONTS / "InstrumentSerif-Regular.ttf"
_SANS = _FONTS / "NotoSans.ttf"

#: Where a system CJK face usually lives. First hit wins.
_CJK_CANDIDATES = (
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
)

_HANGUL_RANGES = ((0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F))
_CYRILLIC_RANGE = (0x0400, 0x04FF)


def _has(text: str, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(any(low <= ord(ch) <= high for low, high in ranges) for ch in text)


@lru_cache(maxsize=1)
def _cjk_path() -> Path | None:
    for candidate in _CJK_CANDIDATES:
        if candidate.exists():
            return candidate
    logger.warning(
        "no system CJK font found; Korean names will not render in OG images. "
        "Install fonts-noto-cjk."
    )
    return None


@lru_cache(maxsize=64)
def _font(path: Path, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    """A face at a size, with the weight axis pinned.

    Both bundled families are variable fonts whose default instance is Thin.
    Loading one without setting the axis gives hairline strokes that all but
    vanish at display sizes, so every caller states the weight it wants.
    """
    font = ImageFont.truetype(str(path), size)
    if weight is not None:
        # A static face has no axes to set; its default weight is already right.
        with contextlib.suppress(OSError):
            font.set_variation_by_axes([weight])
    return font


def _text_font(text: str, size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    """The first bundled face that can actually draw ``text``."""
    if _has(text, _HANGUL_RANGES):
        cjk = _cjk_path()
        if cjk is not None:
            return _font(cjk, size)
        return _font(_SANS, size, weight)
    if _has(text, (_CYRILLIC_RANGE,)):
        return _font(_SANS, size, weight)
    return _font(_SERIF, size)


def _rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b, strict=True))  # type: ignore[return-value]


def _background(theme: Theme) -> Image.Image:
    """The card's radial glow, approximated with concentric bands.

    Pillow has no gradient primitive, and pulling in numpy for one image would
    be a poor trade; 160 ellipses are visually indistinguishable here.
    """
    base = _rgb(theme.bg)
    glow = _rgb(theme.bg_glow)
    image = Image.new("RGB", (WIDTH, HEIGHT), base)
    draw = ImageDraw.Draw(image)

    steps = 160
    max_radius = int(math.hypot(WIDTH, HEIGHT) * 0.8)
    centre_x, centre_y = WIDTH // 2, -HEIGHT // 5
    for step in range(steps, 0, -1):
        t = step / steps
        radius = int(max_radius * t)
        draw.ellipse(
            (centre_x - radius, centre_y - radius, centre_x + radius, centre_y + radius),
            fill=_mix(glow, base, t),
        )
    return image


def _draw_candles(draw: ImageDraw.ImageDraw, theme: Theme, count: int, base_y: int) -> None:
    """One row of candles, however old the person is.

    Left-aligned with everything else: a centred row reads as a mistake beside
    a left-aligned number, and looks worst of all at one candle.
    """
    shown = max(1, min(count, 22))
    accent = _rgb(theme.accent)
    flame = _rgb(theme.flame)
    ink = _rgb(theme.ink)

    pitch = min(34, (WIDTH - 2 * PAD) / shown)
    start = PAD + pitch / 2

    for index in range(shown):
        x = start + pitch * index
        draw.rounded_rectangle(
            (x - 4, base_y - 36, x + 4, base_y), radius=3, fill=ink if index % 2 else accent
        )
        draw.ellipse((x - 5.5, base_y - 53, x + 5.5, base_y - 36), fill=flame)


def _fit(
    draw: ImageDraw.ImageDraw, text: str, max_width: int, start: int, floor: int, weight: int
) -> ImageFont.FreeTypeFont:
    """The largest size at which ``text`` still fits ``max_width``."""
    size = start
    while size > floor:
        font = _text_font(text, size, weight)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 4
    return _text_font(text, floor, weight)


def render_card_image(card: Card) -> bytes:
    """A 1200x630 PNG preview of one card.

    Layout: the wordmark sits top-left, the age fills the left third as a slab
    of colour, and the name occupies the space beside it - which is what keeps
    the right half of the frame from reading as empty.
    """
    theme = get_theme(card.theme)
    image = _background(theme)
    draw = ImageDraw.Draw(image)

    accent = _rgb(theme.accent)
    ink = _rgb(theme.ink)
    muted = _rgb(theme.muted)

    draw.text((PAD, PAD - 10), "birthdaygift", font=_font(_SANS, 26, 500), fill=muted)

    candle_base = HEIGHT - PAD
    centre_y = (PAD + 60 + candle_base - 60) // 2

    if card.age is not None:
        number_font = _font(_DISPLAY, 330, 800)
        number = str(card.age)
        # Big Shoulders carries a lot of leading; measure instead of guessing.
        box = draw.textbbox((0, 0), number, font=number_font)
        number_width = box[2] - box[0]
        draw.text(
            (PAD - box[0], centre_y),
            number,
            font=number_font,
            fill=accent,
            anchor="lm",
        )
        name_x = PAD + number_width + 56
    else:
        name_x = PAD

    name_font = _fit(draw, card.name, WIDTH - name_x - PAD, 86, 34, 600)
    draw.text((name_x, centre_y), card.name, font=name_font, fill=ink, anchor="lm")

    _draw_candles(draw, theme, card.age or 1, candle_base)

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
