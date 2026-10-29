"""Card looks.

A theme is only a palette plus two switches, so adding one means adding an
entry here and a name in each translation file - no template changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

ThemeKey = Literal["midnight", "paper", "neon"]
THEME_KEYS: tuple[ThemeKey, ...] = get_args(ThemeKey)
DEFAULT_THEME: ThemeKey = "midnight"


@dataclass(frozen=True, slots=True)
class Theme:
    key: ThemeKey
    bg: str
    bg_glow: str
    ink: str
    muted: str
    accent: str
    accent_soft: str
    flame: str
    panel: str
    border: str
    #: Whether the animated starfield is drawn behind the card.
    stars: bool
    confetti: tuple[str, ...]
    color_scheme: Literal["dark", "light"]

    @property
    def css_variables(self) -> str:
        """The palette as a CSS custom-property block."""
        pairs = {
            "--bg": self.bg,
            "--bg-glow": self.bg_glow,
            "--ink": self.ink,
            "--muted": self.muted,
            "--accent": self.accent,
            "--accent-soft": self.accent_soft,
            "--flame": self.flame,
            "--panel": self.panel,
            "--border": self.border,
        }
        return ";".join(f"{name}:{value}" for name, value in pairs.items())


THEMES: dict[ThemeKey, Theme] = {
    "midnight": Theme(
        key="midnight",
        bg="#0d1526",
        bg_glow="#16223a",
        ink="#f2ede3",
        muted="#9aa6bd",
        accent="#e9c47c",
        accent_soft="#b8975a",
        flame="#ffb347",
        panel="rgba(242,237,227,0.04)",
        border="rgba(233,196,124,0.22)",
        stars=True,
        confetti=("#e9c47c", "#f2ede3", "#ffb347", "#8fb3ff", "#f28b82"),
        color_scheme="dark",
    ),
    "paper": Theme(
        key="paper",
        bg="#f6f3ec",
        bg_glow="#fffdf8",
        ink="#1d1a16",
        muted="#6f6861",
        accent="#9a5b3d",
        accent_soft="#c08a6b",
        flame="#e08a2e",
        panel="rgba(29,26,22,0.03)",
        border="rgba(29,26,22,0.14)",
        stars=False,
        confetti=("#9a5b3d", "#1d1a16", "#e08a2e", "#6f8f6a", "#b5544f"),
        color_scheme="light",
    ),
    "neon": Theme(
        key="neon",
        bg="#0a0613",
        bg_glow="#1b0f33",
        ink="#f3ecff",
        muted="#9d8fc4",
        accent="#ff4ecd",
        accent_soft="#9b5cff",
        flame="#4ee6ff",
        panel="rgba(243,236,255,0.05)",
        border="rgba(255,78,205,0.28)",
        stars=True,
        confetti=("#ff4ecd", "#4ee6ff", "#9b5cff", "#f3ecff", "#ffe14e"),
        color_scheme="dark",
    ),
}


def get_theme(key: str | None) -> Theme:
    return THEMES.get(key, THEMES[DEFAULT_THEME])  # type: ignore[arg-type]


def normalize_theme(key: str | None) -> ThemeKey:
    return key if key in THEME_KEYS else DEFAULT_THEME  # type: ignore[return-value]
