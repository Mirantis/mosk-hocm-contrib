"""Functional tests for external user memberships."""

from __future__ import annotations

from base import EXTERNAL_TEST_USER


def test_external_user_membership_added_and_removed(membership_host, external_user) -> None:
    host = membership_host
    group_name = host.resource_name("operators")

    with_membership = {
        "groups": [
            {
                "name": group_name,
                "gid": 29010,
                "users": [external_user],
            },
        ],
        "users": [],
    }
    host.apply_and_refresh(with_membership)

    assert group_name in host.user_groups(EXTERNAL_TEST_USER)
    fact = host.read_local_fact()
    assert fact["ext_memberships"] == [{"user": EXTERNAL_TEST_USER, "group": group_name}]

    without_membership = {
        "groups": [
            {
                "name": group_name,
                "gid": 29010,
                "users": [],
            },
        ],
        "users": [],
    }
    host.apply_and_refresh(without_membership)

    assert group_name not in host.user_groups(EXTERNAL_TEST_USER)
    fact = host.read_local_fact()
    assert fact["ext_memberships"] == []
