"""Functional tests for create, reconcile, and wipeout lifecycle."""

from __future__ import annotations

from base import DEFAULT_GROUP


class TestLifecycle:
    prefix = "hocm_lug_lifecycle"

    def test_lifecycle_create_idempotent_reconcile_and_wipeout(self, functional_host) -> None:
        host = functional_host
        admins_group = host.resource_name("admins")
        developers_group = host.resource_name("developers")
        alice_user = host.resource_name("alice")
        bob_user = host.resource_name("bob")

        initial_values = {
            "default_shell": "/bin/bash",
            "groups": [
                {
                    "name": admins_group,
                    "gid": 29001,
                    "users": [alice_user],
                },
                {
                    "name": developers_group,
                    "users": [bob_user],
                },
            ],
            "users": [
                {"name": alice_user},
                {
                    "name": bob_user,
                    "uid": 29002,
                    "groups": [developers_group],
                },
            ],
        }

        host.apply_and_refresh(initial_values)

        admins_entry = host.getent_group(admins_group)
        developers_entry = host.getent_group(developers_group)
        default_group_entry = host.getent_group(DEFAULT_GROUP)
        alice_entry = host.getent_passwd(alice_user)
        bob_entry = host.getent_passwd(bob_user)

        assert admins_entry["gid"] == "29001"
        assert developers_entry["gid"]
        assert default_group_entry["gid"]
        assert alice_entry["uid"]
        assert bob_entry["uid"] == "29002"
        assert alice_entry["gid"] == default_group_entry["gid"]
        assert bob_entry["gid"] == default_group_entry["gid"]
        assert alice_entry["shell"] == "/bin/bash"
        assert bob_entry["shell"] == "/bin/bash"
        assert admins_group in host.user_groups(alice_user)
        assert developers_group in host.user_groups(bob_user)
        assert host.password_status(alice_user) in {"L", "NP"}
        assert host.password_status(bob_user) in {"L", "NP"}
        assert host.path_exists(alice_entry["home"])
        assert host.path_exists(bob_entry["home"])

        fact = host.read_local_fact()
        assert sorted(fact["users"]) == sorted([alice_user, bob_user])
        assert sorted(fact["groups"]) == sorted([admins_group, developers_group, DEFAULT_GROUP])
        assert fact["ext_memberships"] == []

        host.apply_and_refresh(initial_values)

        reconciled_values = {
            "default_shell": "/bin/bash",
            "groups": [
                {
                    "name": admins_group,
                    "gid": 29001,
                    "users": [alice_user],
                },
            ],
            "users": [
                {"name": alice_user},
            ],
        }
        host.apply_and_refresh(reconciled_values)

        assert host.user_exists(alice_user)
        assert not host.user_exists(bob_user)
        assert host.group_exists(admins_group)
        assert not host.group_exists(developers_group)
        assert not host.path_exists(bob_entry["home"])

        fact = host.read_local_fact()
        assert fact["users"] == [alice_user]
        assert sorted(fact["groups"]) == sorted([admins_group, DEFAULT_GROUP])

        host.apply_and_refresh({"groups": [], "users": []})

        assert not host.user_exists(alice_user)
        assert not host.group_exists(admins_group)
        assert not host.group_exists(DEFAULT_GROUP)

        fact = host.read_local_fact()
        assert fact["users"] == []
        assert fact["groups"] == []
        assert fact["ext_memberships"] == []


class TestShell:
    prefix = "hocm_lug_shell"

    def test_custom_default_shell(self, functional_host) -> None:
        host = functional_host
        user_name = host.resource_name("vincent")
        values = {
            "default_shell": "/bin/sh",
            "groups": [],
            "users": [{"name": user_name}],
        }

        host.apply_and_refresh(values)

        entry = host.getent_passwd(user_name)
        assert entry["shell"] == "/bin/sh"
