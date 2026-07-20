"""Unit tests for normalize_users_groups input validation."""

from __future__ import annotations

import pytest

from conftest import DEFAULT_GROUP, normalize


def test_invalid_uid_range_raises(normalize) -> None:
    with pytest.raises(ValueError, match="uid_range must be"):
        normalize({"uid_range": [1000]}, {})

    with pytest.raises(ValueError, match="uid_range must be"):
        normalize({"uid_range": [2000, 1000]}, {})


def test_invalid_gid_range_raises(normalize) -> None:
    with pytest.raises(ValueError, match="gid_range must be"):
        normalize({"gid_range": [1000, 900, 800]}, {})


def test_reserved_default_group_name_raises(normalize) -> None:
    with pytest.raises(ValueError, match="reserved"):
        normalize({"groups": [{"name": "admin"}, {"name": DEFAULT_GROUP}]}, {})


def test_duplicate_group_names_raise(normalize) -> None:
    with pytest.raises(ValueError, match="Duplicate group name 'admins'"):
        normalize(
            {
                "groups": [
                    {"name": "admins"},
                    {"name": "admins"},
                ]
            },
            {},
        )


def test_duplicate_user_names_raise(normalize) -> None:
    with pytest.raises(ValueError, match="Duplicate user name 'alice'"):
        normalize(
            {
                "users": [
                    {"name": "alice"},
                    {"name": "alice"},
                ]
            },
            {},
        )
