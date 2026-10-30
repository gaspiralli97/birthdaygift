"""Card colourways.

Sampled from the Baginy storefront rather than invented: near-black, burgundy
and champagne are that project's own three colours, already proven to sit
together. A colourway is only a palette plus one switch, so adding one means
an entry here and a name in each translation file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

ThemeKey = Literal["qora", "vino", "qaymoq"]
THEME_KEYS: tuple[ThemeKey, ...] = get_args(ThemeKey)
DEFAULT_THEME: ThemeKey = "qora"


@dataclass(frozen=True, slots=True)
class Theme:
    key: ThemeKey
    night: str
    night_2: str
    accent: str
    accent_soft: str
    accent_lift: str
    paper: str
    muted: str
    flame: str
    confetti: tuple[str, ...]
    #: Dark specks on a light sheet read as dirt at full strength.
    light: bool

    @property
    def css_variables(self) -> str:
        pairs = {
            "--night": self.night,
            "--night-2": self.night_2,
            "--accent": self.accent,
            "--accent-soft": self.accent_soft,
            "--accent-lift": self.accent_lift,
            "--paper": self.paper,
            "--muted": self.muted,
            "--flame": self.flame,
        }
        return ";".join(f"{name}:{value}" for name, value in pairs.items())

    @property
    def confetti_css(self) -> str:
        return ",".join(self.confetti)


THEMES: dict[ThemeKey, Theme] = {
    "qora": Theme(
        key="qora",
        night="#0c0c0c",
        night_2="#1b1b1b",
        accent="#f2d9a0",
        accent_soft="#e3c08d",
        accent_lift="#fdf6e6",
        paper="#f2e5c6",
        muted="#8a8276",
        flame="#f2d9a0",
        confetti=("#f2d9a0", "#f2e5c6", "#e3c08d", "#75162d", "#ffffff"),
        light=False,
    ),
    "vino": Theme(
        key="vino",
        night="#3a0a16",
        night_2="#75162d",
        accent="#f2d9a0",
        accent_soft="#e3c08d",
        accent_lift="#fdf6e6",
        paper="#f7ece0",
        muted="#c0a2a8",
        flame="#f2d9a0",
        confetti=("#f2d9a0", "#f7ece0", "#e3c08d", "#5c1024", "#ffffff"),
        light=False,
    ),
    "qaymoq": Theme(
        key="qaymoq",
        night="#f2e5c6",
        night_2="#faf3e4",
        accent="#75162d",
        accent_soft="#5c1024",
        accent_lift="#a8384f",
        paper="#0c0c0c",
        muted="#6b5d47",
        # A pale flame vanishes on a pale sheet; two stops down the same ramp.
        flame="#c07d1e",
        confetti=("#75162d", "#0c0c0c", "#e3c08d", "#f2d9a0", "#8a8276"),
        light=True,
    ),
}


def get_theme(key: str | None) -> Theme:
    return THEMES.get(key, THEMES[DEFAULT_THEME])  # type: ignore[arg-type]


def normalize_theme(key: str | None) -> ThemeKey:
    return key if key in THEME_KEYS else DEFAULT_THEME  # type: ignore[return-value]
