"""Unit tests for the normalize_users_groups Ansible filter plugin."""

from __future__ import annotations

from conftest import DEFAULT_GROUP, DEFAULT_SHELL, FilterModule


def test_filters_registers_normalize_users_groups(normalize) -> None:
    filter_module = FilterModule()
    filters = filter_module.filters()
    assert "normalize_users_groups" in filters
    assert callable(filters["normalize_users_groups"])

def test_empty_input_and_empty_fact(normalize) -> None:
    result = normalize({}, {})

    assert result["fact"]["users"] == []
    assert result["fact"]["groups"] == []
    assert result["fact"]["ext_memberships"] == []
    assert result["to_remove"]["users"] == []
    assert result["to_remove"]["groups"] == []
    assert result["to_remove"]["ext_memberships"] == []
    assert result["to_ensure"]["groups"] == []
    assert result["to_ensure"]["users"] == []
    assert result["to_ensure"]["ext_memberships"] == []
    assert "default_group" not in result["to_ensure"]

def test_none_input_and_fact_treated_as_empty(normalize) -> None:
    result = normalize(None, None)
    assert result["fact"]["users"] == []
    assert result["fact"]["groups"] == []
    assert result["fact"]["ext_memberships"] == []

def test_first_run_creates_facts_and_module_payloads(normalize) -> None:
    input_config = {
            "groups": [{"name": "admins", "gid": 2001, "users": ["alice"]}],
            "users": [{"name": "alice"}, {"name": "bob", "uid": 2002}],
    }

    result = normalize(input_config, {})

    assert result["fact"]["users"] == ["alice", "bob"]
    assert result["fact"]["groups"] == ["admins", DEFAULT_GROUP]
    assert result["fact"]["ext_memberships"] == []
    assert result["to_remove"]["users"] == []
    assert result["to_remove"]["groups"] == []
    assert result["to_remove"]["ext_memberships"] == []

    assert result["to_ensure"]["groups"] == [
                {"name": DEFAULT_GROUP},
                {"name": "admins", "gid": 2001},
            ]
    assert result["to_ensure"]["users"][0] == {
                "name": "alice",
                "group": DEFAULT_GROUP,
                "shell": DEFAULT_SHELL,
                "groups": ["admins"],
            }
    assert result["to_ensure"]["users"][1]["uid"] == 2002
    assert result["to_ensure"]["users"][1]["groups"] == []
    assert "uid_min" not in result["to_ensure"]["users"][0]
    assert "uid_max" not in result["to_ensure"]["users"][0]
    assert "gid_min" not in result["to_ensure"]["groups"][0]
    assert "gid_max" not in result["to_ensure"]["groups"][0]
    assert result["to_ensure"]["ext_memberships"] == []

def test_gid_range_sets_gid_min_and_gid_max_on_groups(normalize) -> None:
    input_config = {
            "gid_range": [1000, 10000],
            "groups": [{"name": "admins"}, {"name": "developers", "gid": 2001}],
            "users": [{"name": "alice"}],
    }

    result = normalize(input_config, {})

    for group in result["to_ensure"]["groups"]:
            assert group["gid_min"] == 1000
            assert group["gid_max"] == 10000

    groups_by_name = {group["name"]: group for group in result["to_ensure"]["groups"]}
    assert groups_by_name["developers"]["gid"] == 2001

def test_uid_range_sets_uid_min_and_uid_max_on_users(normalize) -> None:
    input_config = {
            "uid_range": [1000, 10000],
            "users": [{"name": "alice"}, {"name": "bob", "uid": 2002}],
    }

    result = normalize(input_config, {})

    for user in result["to_ensure"]["users"]:
            assert user["uid_min"] == 1000
            assert user["uid_max"] == 10000

    assert result["to_ensure"]["users"][1]["uid"] == 2002

def test_readme_example_ext_memberships_and_external_group(normalize) -> None:
    input_config = {
            "default_shell": "/bin/bash",
            "groups": [
                {"name": "admins", "gid": 2001, "users": ["alice", "external_system_user"]},
                {"name": "developers", "users": ["bob"]},
            ],
            "users": [
                {"name": "alice"},
                {"name": "bob", "uid": 2001, "groups": ["developers"]},
                {"name": "vincent", "groups": ["sudo"]},
            ],
    }

    result = normalize(input_config, {})

    assert result["fact"]["ext_memberships"] == [{"user": "external_system_user", "group": "admins"}]
    assert result["to_ensure"]["ext_memberships"] == [{"user": "external_system_user", "group": "admins"}]
    users_by_name = {
            user["name"]: user for user in result["to_ensure"]["users"]
    }
    assert users_by_name["alice"]["groups"] == ["admins"]
    assert users_by_name["bob"]["groups"] == ["developers"]
    assert users_by_name["vincent"]["groups"] == ["sudo"]

def test_ext_memberships_produce_flat_user_group_pairs(normalize) -> None:
    input_config = {
            "groups": [
                {"name": "admins", "users": ["external_system_user"]},
                {"name": "operators", "users": ["external_system_user"]},
            ],
            "users": [],
    }

    result = normalize(input_config, {})

    assert result["to_ensure"]["ext_memberships"] == [
                {"user": "external_system_user", "group": "admins"},
                {"user": "external_system_user", "group": "operators"},
            ]

def test_membership_deduplication(normalize) -> None:
    input_config = {
            "groups": [{"name": "developers", "users": ["bob"]}],
            "users": [{"name": "bob", "groups": ["developers"]}],
    }

    result = normalize(input_config, {})

    assert result["fact"]["ext_memberships"] == []
    assert result["to_ensure"]["ext_memberships"] == []
    assert result["to_ensure"]["users"][0]["groups"] == ["developers"]

def test_groups_only_input_has_no_users_in_to_ensure(normalize) -> None:
    input_config = {"groups": [{"name": "admins"}]}

    result = normalize(input_config, {})

    assert result["fact"]["groups"] == ["admins"]
    assert result["to_ensure"]["users"] == []

def test_custom_default_shell(normalize) -> None:
    input_config = {
            "default_shell": "/bin/zsh",
            "users": [{"name": "alice"}],
    }

    result = normalize(input_config, {})

    assert result["to_ensure"]["users"][0]["shell"] == "/bin/zsh"

def test_reconciliation_removes_stale_users_groups_and_ext_memberships(normalize) -> None:
    input_config = {
            "groups": [{"name": "admins", "users": ["alice"]}],
            "users": [{"name": "alice"}],
    }
    previous_fact = {
            "users": ["alice", "retired_user"],
            "groups": ["admins", "retired_group", DEFAULT_GROUP],
            "ext_memberships": [
                {"user": "retired_user", "group": "retired_group"},
            ],
    }

    result = normalize(input_config, previous_fact)

    assert result["to_remove"]["users"] == ["retired_user"]
    assert result["to_remove"]["groups"] == ["retired_group"]
    assert result["to_remove"]["ext_memberships"] == [{"user": "retired_user", "group": "retired_group"}]

def test_reconciliation_removes_partial_ext_memberships(normalize) -> None:
    input_config = {
            "groups": [{"name": "admins", "users": ["external_system_user"]}],
            "users": [],
    }
    previous_fact = {
            "users": [],
            "groups": ["admins", "operators"],
            "ext_memberships": [
                {"user": "external_system_user", "group": "admins"},
                {"user": "external_system_user", "group": "operators"},
            ],
    }

    result = normalize(input_config, previous_fact)

    assert result["to_remove"]["groups"] == ["operators"]
    assert result["to_remove"]["ext_memberships"] == [{"user": "external_system_user", "group": "operators"}]

def test_reconciliation_removes_default_group_when_users_cleared(normalize) -> None:
    input_config = {"groups": [{"name": "admins"}], "users": []}
    previous_fact = {
            "users": ["alice"],
            "groups": ["admins", DEFAULT_GROUP],
            "ext_memberships": [],
    }

    result = normalize(input_config, previous_fact)

    assert result["to_remove"]["groups"] == [DEFAULT_GROUP]
    assert result["fact"]["groups"] == ["admins"]

def test_wipe_out_empty_input_removes_all_previous_state(normalize) -> None:
    previous_fact = {
            "users": ["alice", "bob"],
            "groups": ["admins", DEFAULT_GROUP],
            "ext_memberships": [
                {"user": "external_system_user", "group": "admins"},
            ],
    }

    result = normalize({"groups": [], "users": []}, previous_fact)

    assert result["to_remove"]["users"] == ["alice", "bob"]
    assert result["to_remove"]["groups"] == ["admins", DEFAULT_GROUP]
    assert result["to_remove"]["ext_memberships"] == [{"user": "external_system_user", "group": "admins"}]

def test_to_ensure_ext_memberships_include_only_non_managed_users(normalize) -> None:
    input_config = {
            "groups": [
                {"name": "admins", "users": ["alice", "external_system_user"]},
                {"name": "operators", "users": ["service_account"]},
            ],
            "users": [{"name": "alice", "groups": ["operators"]}],
    }

    result = normalize(input_config, {})

    assert result["to_ensure"]["ext_memberships"] == [
                {"user": "external_system_user", "group": "admins"},
                {"user": "service_account", "group": "operators"},
            ]
    assert result["to_ensure"]["users"][0]["groups"] == ["operators", "admins"]

def test_normalizes_legacy_aggregated_ext_membership_fact(normalize) -> None:
    input_config = {
            "groups": [{"name": "admins", "users": ["external_system_user"]}],
            "users": [],
    }
    previous_fact = {
            "users": [],
            "groups": ["admins", "operators"],
            "ext_memberships": [
                {"user": "external_system_user", "groups": ["admins", "operators"]},
            ],
    }

    result = normalize(input_config, previous_fact)

    assert result["to_remove"]["ext_memberships"] == [{"user": "external_system_user", "group": "operators"}]

def test_normalizes_missing_group_users_and_user_groups(normalize) -> None:
    input_config = {
            "groups": [{"name": "admins"}],
            "users": [{"name": "alice"}],
    }

    result = normalize(input_config, {})

    assert result["fact"]["ext_memberships"] == []
    assert result["to_ensure"]["users"][0]["groups"] == []
    assert "gid" not in result["to_ensure"]["groups"][0]
    assert "gid_min" not in result["to_ensure"]["groups"][0]
    assert "gid_max" not in result["to_ensure"]["groups"][0]
    assert "uid" not in result["to_ensure"]["users"][0]
    assert "uid_min" not in result["to_ensure"]["users"][0]
    assert "uid_max" not in result["to_ensure"]["users"][0]

