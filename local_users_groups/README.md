# Local Users and Groups Management

This Host OS configuration module for Mirantis OpenStack for K8 (MOSK) 
securely manages local users, groups, and memberships on the hosts of a MOSK
cluster using strict declarative semantics: the settings provided in the input
are the exact desired end state for resources managed by this module.
Empty `groups` / `users` lists remove previously managed resources tracked in
local facts.

## Features

- Strict reconciliation: resources previously managed by the module but absent from the current input are removed
- Persistent state tracking on each node via Ansible local facts (`/etc/ansible/facts.d/mosk_local_users_groups.fact`)
- `groups` and `users` entities are provided separately
- Optional `uid` and `gid` overrides per user / group
- Automatic creation of the `mosk_managed_users` primary group for users to distinguish them
- External local users are never created or removed; only their memberships in managed groups are enforced
- Managed users' passwords are locked (`*`); use password-less auth (e.g. SSH keys)
- `default_shell` controls the login shell for all managed users
- Automatic management of users' home directories, created and removed with the owners

## Requirements

- Ubuntu 24.04 as the host OS 

## Configuration

### Top-level parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `groups` | No | `[]` | List of managed group records |
| `users` | No | `[]` | List of managed user records |
| `default_shell` | No | `/bin/bash` | Login shell for managed users |

### Group record

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | Yes | — | Group name |
| `gid` | No | — | Optional group ID. When omitted, the system assigns a GID from `/etc/login.defs` |
| `users` | No | `[]` | Users that should be members of this group (managed or existing local users) |

### User record

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | Yes | — | User name |
| `uid` | No | — | Optional user ID. When omitted, the system assigns a UID from `/etc/login.defs` |
| `groups` | No | `[]` | Supplementary groups for the user (managed groups and/or existing local groups) |

## Strict management model

On each run the module:

1. Reads the previously stored managed state from local facts
2. Reconciles the desired configuration from input with that state
3. Ensures managed groups and users exist
4. Adds or removes external user memberships in managed groups
5. Removes managed users, groups, and memberships that exist in facts but are missing from the current input
6. Writes the updated managed state back to local facts

### Persisted state

The local fact file (`/etc/ansible/facts.d/mosk_local_users_groups.fact`) stores:

| Key | Description |
|-----|-------------|
| `users` | Names of user accounts managed by the module |
| `groups` | Names of groups managed by the module, including `mosk_managed_users` when users are defined |
| `ext_memberships` | Flat list of `{user, group}` pairs for non-managed users that must be members of managed groups |

### Memberships

Memberships are derived from both `groups[].users` and `users[].groups`:

- For a **managed user** listed in `groups[].users` or `users[].groups`, membership is applied via `ansible.builtin.user` supplementary groups. That list is the full desired set: undeclared supplementary group memberships for that user are removed.
- For an **existing local user** listed only in `groups[].users`, membership is tracked in `ext_memberships` and applied with `adduser` / `deluser`. Only those declared memberships in managed groups are added or removed; other memberships of that external user are left unchanged.

A group's `users` list may name any existing local user, not only users defined in the `users` section. A managed user's `groups` list may reference groups defined in the `groups` section or already present on the system.

Each managed user uses `mosk_managed_users` as its primary group. That group is created automatically when users are defined. The name `mosk_managed_users` is reserved and must not appear in the `groups` section.

Note: removing a managed group will fail if non-managed users are still members of that group.

## Example

```yaml
apiVersion: kaas.mirantis.com/v1alpha1
kind: HostOSConfiguration
metadata:
  name: my-local-users
  namespace: default
spec:
  configs:
  - module: local_users_groups
    moduleVersion: 2.0.0
    values:
      default_shell: /bin/bash
      
      groups:
        - name: admins
          gid: 2001
          users:
            - alice
            - external_system_user
        - name: developers
          users:
            - bob
      users:
        - name: alice
        - name: bob
          uid: 2001
          groups:
            - developers
        - name: vincent
          groups: [sudo]
```

In this example:

**Groups**

- `admins` is created with explicit GID `2001`. Its `users` list adds managed user `alice` and the existing local account `external_system_user` as members.
- `developers` has no explicit `gid`, so the system assigns a GID (from `/etc/login.defs`). Its `users` list adds managed user `bob` as a member.

**Users**

- `alice` has no explicit `uid` or `groups`, so her UID is system-assigned. She becomes a member of `admins` via the group record.
- `bob` is created with explicit UID `2001` and supplementary group `developers`. He is also listed as a member of `developers` via the group record.
- `vincent` has no explicit `uid` and is added to the existing `sudo` group via `users[].groups`.

All three managed users (`alice`, `bob`, and `vincent`) use `mosk_managed_users` as their primary group. That group is created automatically and also receives a system-assigned GID until range options are enabled. `external_system_user` is not managed as a user account; only its membership in `admins` is enforced and tracked in `ext_memberships`.

To remove all module-managed users and groups, provide empty lists:

```yaml
apiVersion: kaas.mirantis.com/v1alpha1
kind: HostOSConfiguration
metadata:
  name: local-users-1
  namespace: default
spec:
  configs:
  - module: local_users_groups
    moduleVersion: 2.0.0
    values:
      groups: []
      users: []
```

## Tests

Runner scripts use [uv](https://docs.astral.sh/uv/) to provision `pytest` (and `ansible-core` for functional tests) on the fly.

### Unit tests

```bash
./tests/run-unit.sh
```

### Functional tests

Functional tests apply the module playbook over SSH to a real Ubuntu 24.04 host and verify users, groups, memberships, home directories, password lock state, and the local fact file.

#### Prerequisites

- [uv](https://docs.astral.sh/uv/) on the machine running the tests
- Ubuntu 24.04 test host reachable via SSH
- Passwordless `sudo` on the test host (the playbook runs with `become`)

`ansible` and `pytest` are provided by `uv run` for functional tests.

#### Configuration

Set environment variables before running the tests:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEST_HOST` | Yes | — | SSH hostname or IP of the test host |
| `TEST_USER` | No | current user | SSH login user |
| `TEST_SSH_KEY` | No | — | Path to SSH private key |

Privilege escalation (`become`) is always enabled.

An example static inventory is provided in [`tests/functional/inventory.example.yml`](tests/functional/inventory.example.yml). The test runner writes ephemeral inventory under `tests/functional/.ansible/` (gitignored) from the environment variables above.

#### Running

```bash
export TEST_HOST=192.0.2.10
export TEST_USER=ubuntu
export TEST_SSH_KEY=~/.ssh/id_rsa

./tests/run-functional.sh
```

#### Test behavior

- Managed test users and groups use the `hocm_lug_*` name prefix; tests that need stable IDs set explicit UIDs/GIDs in the `29000–29999` band (others use system-assigned IDs).
- External membership tests temporarily create `hocm_lug_ft_external`.
- Each test cleans up by applying empty `groups` and `users` input via a pytest fixture teardown.
- `TEST_HOST` and `ansible`/`ansible-playbook` on `PATH` are required; the run fails immediately if they are missing.
