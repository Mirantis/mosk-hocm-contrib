"""Pytest fixtures for local_users_groups functional tests."""

from __future__ import annotations

import pytest

from base import (
    EXTERNAL_TEST_USER,
    FunctionalHost,
    validate_test_environment,
    write_inventory,
)

pytestmark = pytest.mark.functional


def pytest_configure(config) -> None:
    try:
        validate_test_environment()
    except RuntimeError as exc:
        pytest.exit(str(exc), returncode=1)


@pytest.fixture(scope="session")
def inventory_path():
    path = write_inventory()
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def functional_host(inventory_path, request):
    prefix = "hocm_lug"
    if request.cls is not None and hasattr(request.cls, "prefix"):
        prefix = request.cls.prefix
    host = FunctionalHost(str(inventory_path), prefix=prefix)
    yield host
    try:
        host.wipe_managed_state()
    except Exception:
        pass


@pytest.fixture
def membership_host(inventory_path):
    host = FunctionalHost(str(inventory_path), prefix="hocm_lug_membership")
    host.ensure_external_user()
    yield host
    try:
        host.wipe_managed_state()
        host.remove_external_user()
    except Exception:
        pass


@pytest.fixture
def external_user():
    return EXTERNAL_TEST_USER
