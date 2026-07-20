"""Ansible filter plugin for local users and groups reconciliation."""

from __future__ import annotations

from typing import Any

DOCUMENTATION = """
name: normalize_users_groups
short_description: Normalize managed users/groups input and reconcile with stored facts
description:
  - Accepts playbook input and the mosk_local_users_groups local fact.
  - Returns the desired fact payload, entities to remove, and work items to apply on the host.
options:
  _input:
    description:
      - Playbook values for the local_users_groups module.
      - Supported keys are C(groups), C(users), C(default_shell), C(uid_range), and C(gid_range).
    type: dict
    required: true
  _fact:
    description:
      - Previously stored mosk_local_users_groups local fact (or empty dict on first run).
      - Expected keys are C(users), C(groups), and C(ext_memberships).
    type: dict
    required: true
returns:
  description: Reconciled users/groups state and apply/remove plans for the playbook.
  type: dict
  contains:
    fact:
      description: State to persist on the node as the mosk_local_users_groups local fact.
      type: dict
      contains:
        users:
          description: Names of users managed by the module after this run.
          type: list
          elements: str
        groups:
          description:
            - Names of groups managed by the module after this run.
            - Includes the reserved primary group C(mosk_managed_users) when users are defined.
          type: list
          elements: str
        ext_memberships:
          description:
            - External user memberships in groups managed by the module.
            - Derived from C(groups[].users) entries whose user is not defined in C(users).
            - Each item is a dict with keys C(user) and C(group).
          type: list
          elements: dict
    to_remove:
      description:
        - Managed users, groups, and external memberships present in the previous fact
          but absent from the current input.
      type: dict
      contains:
        users:
          description: User names to remove with M(ansible.builtin.user).
          type: list
          elements: str
        groups:
          description: Group names to remove with M(ansible.builtin.group).
          type: list
          elements: str
        ext_memberships:
          description:
            - External group memberships to revoke.
            - Each item is a dict with keys C(user) and C(group); the playbook applies these with C(deluser).
          type: list
          elements: dict
    to_ensure:
      description: Work items for applying the desired configuration on the host.
      type: dict
      contains:
        groups:
          description:
            - Payloads for M(ansible.builtin.group).
            - Includes the reserved default primary group C(mosk_managed_users) as the first entry when managed users are defined.
            - Each item includes C(name); C(gid) is included when set in input.
            - C(gid_min) and C(gid_max) are included when C(gid_range) is configured in input.
          type: list
          elements: dict
        users:
          description:
            - Payloads for M(ansible.builtin.user).
            - Each item sets C(group) to C(mosk_managed_users), C(shell), and C(groups).
            - C(groups) lists supplementary groups from C(users[].groups) and C(groups[].users) for managed users.
            - C(uid) is included when set in input.
            - C(uid_min) and C(uid_max) are included when C(uid_range) is configured in input.
            - Password, C(create_home), and C(state) are set by the playbook, not by this filter.
          type: list
          elements: dict
        ext_memberships:
          description:
            - External user memberships to add in managed groups.
            - Derived from C(groups[].users) entries whose user is not defined in C(users).
            - Each item is a dict with keys C(user) and C(group); the playbook applies these with C(adduser).
          type: list
          elements: dict
"""

DEFAULT_GROUP = "mosk_managed_users"
DEFAULT_SHELL = "/bin/bash"


class FilterModule:
    """Ansible filter plugin entry point."""

    def filters(self) -> dict[str, Any]:
        return {
            "normalize_users_groups": self.normalize_users_groups,
        }

    def normalize_users_groups(
        self,
        input_config: dict[str, Any] | None,
        previous_fact: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Normalize input and reconcile it with the stored mosk_local_users_groups fact.

        Args:
            input_config: Playbook values (groups, users, uid_range, gid_range,
                default_shell).
            previous_fact: Content of the mosk_local_users_groups local fact.

        Returns:
            dict with keys:
              fact: State to persist on the node.
              to_remove: Managed users, groups, and external memberships to delete.
              to_ensure: Work items for the playbook (group/user module payloads and
                  external memberships to add).
        """
        input_config = input_config or {}
        previous_fact = previous_fact or {}

        groups = self._normalize_groups(input_config.get("groups", []))
        users = self._normalize_users(input_config.get("users", []))
        default_shell = input_config.get("default_shell", DEFAULT_SHELL)

        self._validate_uid_gid_range(input_config.get("uid_range", []), "uid_range")
        self._validate_uid_gid_range(input_config.get("gid_range", []), "gid_range")
        self._validate_reserved_default_group(groups)
        self._validate_duplicate_names(groups, "group")
        self._validate_duplicate_names(users, "user")

        desired_managed_groups = self._desired_managed_groups(groups, users)
        desired_managed_users = [user["name"] for user in users]
        desired_ext_memberships = self._ext_memberships(groups, desired_managed_users)

        previous_users = list(previous_fact.get("users", []))
        previous_groups = list(previous_fact.get("groups", []))
        previous_ext_memberships = self._normalize_ext_memberships(
            previous_fact.get("ext_memberships", [])
        )

        users_to_remove = sorted(set(previous_users) - set(desired_managed_users))
        groups_to_remove = sorted(set(previous_groups) - set(desired_managed_groups))
        ext_memberships_to_remove = self._diff_ext_memberships(
            previous_ext_memberships, desired_ext_memberships
        )

        fact = {
            "users": desired_managed_users,
            "groups": desired_managed_groups,
            "ext_memberships": desired_ext_memberships,
        }

        user_supplementary_groups = self._user_supplementary_groups(groups, users)
        uid_range = input_config.get("uid_range", [])
        gid_range = input_config.get("gid_range", [])

        to_ensure: dict[str, Any] = {
            "groups": self._groups_to_ensure(groups, users, gid_range),
            "users": [
                self._user_module_payload(
                    user,
                    default_shell,
                    user_supplementary_groups[user["name"]],
                    uid_range,
                )
                for user in users
            ],
            "ext_memberships": desired_ext_memberships,
        }

        return {
            "fact": fact,
            "to_remove": {
                "users": users_to_remove,
                "groups": groups_to_remove,
                "ext_memberships": ext_memberships_to_remove,
            },
            "to_ensure": to_ensure,
        }

    @staticmethod
    def _normalize_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "name": group["name"],
                **({"gid": group["gid"]} if "gid" in group else {}),
                "users": list(group.get("users", [])),
            }
            for group in groups
        ]

    @staticmethod
    def _normalize_users(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "name": user["name"],
                **({"uid": user["uid"]} if "uid" in user else {}),
                "groups": list(user.get("groups", [])),
            }
            for user in users
        ]

    @staticmethod
    def _validate_uid_gid_range(value: list[Any], name: str) -> None:
        if not value:
            return
        if len(value) != 2 or value[0] > value[1]:
            raise ValueError(
                f"{name} must be a two-element array [min, max] with min <= max."
            )

    @staticmethod
    def _validate_reserved_default_group(groups: list[dict[str, Any]]) -> None:
        for group in groups:
            if group["name"] == DEFAULT_GROUP:
                raise ValueError(
                    f"Group name '{DEFAULT_GROUP}' is reserved for the module "
                    "default primary group."
                )

    @staticmethod
    def _validate_duplicate_names(
        records: list[dict[str, Any]], entity: str
    ) -> None:
        seen: set[str] = set()
        for record in records:
            name = record["name"]
            if name in seen:
                raise ValueError(f"Duplicate {entity} name '{name}' in configuration.")
            seen.add(name)

    @staticmethod
    def _desired_managed_groups(
        groups: list[dict[str, Any]], users: list[dict[str, Any]]
    ) -> list[str]:
        names = [group["name"] for group in groups]
        if users:
            names.append(DEFAULT_GROUP)
        return sorted(set(names))

    @staticmethod
    def _ext_memberships(
        groups: list[dict[str, Any]],
        managed_user_names: list[str],
    ) -> list[dict[str, str]]:
        managed_users = set(managed_user_names)
        memberships: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for group in groups:
            group_name = group["name"]
            for username in group.get("users", []):
                if username in managed_users:
                    continue
                pair = (username, group_name)
                if pair not in seen:
                    seen.add(pair)
                    memberships.append({"user": username, "group": group_name})

        return sorted(memberships, key=lambda item: (item["user"], item["group"]))

    @staticmethod
    def _normalize_ext_memberships(
        memberships: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for item in memberships:
            username = item["user"]
            if "groups" in item:
                group_names = item["groups"]
            else:
                group_names = [item["group"]]

            for group_name in group_names:
                pair = (username, group_name)
                if pair not in seen:
                    seen.add(pair)
                    normalized.append({"user": username, "group": group_name})

        return sorted(normalized, key=lambda item: (item["user"], item["group"]))

    @staticmethod
    def _diff_ext_memberships(
        previous: list[dict[str, str]],
        desired: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        previous_pairs = {(item["user"], item["group"]) for item in previous}
        desired_pairs = {(item["user"], item["group"]) for item in desired}
        return [
            {"user": user, "group": group}
            for user, group in sorted(previous_pairs - desired_pairs)
        ]

    @staticmethod
    def _user_supplementary_groups(
        groups: list[dict[str, Any]],
        users: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        managed_users = {user["name"] for user in users}
        by_user: dict[str, list[str]] = {user["name"]: [] for user in users}

        for user in users:
            username = user["name"]
            for group_name in user.get("groups", []):
                if group_name == DEFAULT_GROUP:
                    continue
                user_groups = by_user[username]
                if group_name not in user_groups:
                    user_groups.append(group_name)

        for group in groups:
            group_name = group["name"]
            for username in group.get("users", []):
                if username not in managed_users or group_name == DEFAULT_GROUP:
                    continue
                user_groups = by_user[username]
                if group_name not in user_groups:
                    user_groups.append(group_name)

        return by_user

    @staticmethod
    def _groups_to_ensure(
        groups: list[dict[str, Any]],
        users: list[dict[str, Any]],
        gid_range: list[Any],
    ) -> list[dict[str, Any]]:
        payloads = [
            FilterModule._group_module_payload(group, gid_range) for group in groups
        ]
        if users:
            return [
                FilterModule._group_module_payload({"name": DEFAULT_GROUP}, gid_range),
                *payloads,
            ]
        return payloads

    @staticmethod
    def _group_module_payload(
        group: dict[str, Any],
        gid_range: list[Any],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": group["name"],
        }
        if "gid" in group:
            payload["gid"] = group["gid"]
        if len(gid_range) == 2:
            payload["gid_min"] = gid_range[0]
            payload["gid_max"] = gid_range[1]
        return payload

    @staticmethod
    def _user_module_payload(
        user: dict[str, Any],
        default_shell: str,
        supplementary_groups: list[str],
        uid_range: list[Any],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": user["name"],
            "group": DEFAULT_GROUP,
            "shell": default_shell,
            "groups": list(supplementary_groups),
        }
        if "uid" in user:
            payload["uid"] = user["uid"]
        if len(uid_range) == 2:
            payload["uid_min"] = uid_range[0]
            payload["uid_max"] = uid_range[1]
        return payload
