"""Jinja environment.

Kept apart from the routers so the custom filters are registered exactly once,
wherever templates are first imported from.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from .view import group_thousands, lived_days, prime_factors

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.filters["thousands"] = group_thousands
templates.env.filters["prime_factors"] = prime_factors
templates.env.filters["lived_days"] = lived_days
