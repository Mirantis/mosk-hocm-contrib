"""Pytest fixtures for local_users_groups unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

MODULE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MODULE_DIR / "filter_plugins"))

from normalize_users_groups import (  # noqa: E402
    DEFAULT_GROUP,
    DEFAULT_SHELL,
    FilterModule,
    RESERVED_GROUPS,
    RESERVED_USERS,
)


@pytest.fixture
def normalize():
    return FilterModule().filters()["normalize_users_groups"]


__all__ = [
    "DEFAULT_GROUP",
    "DEFAULT_SHELL",
    "FilterModule",
    "MODULE_DIR",
    "RESERVED_GROUPS",
    "RESERVED_USERS",
    "normalize",
]
