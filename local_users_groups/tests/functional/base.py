"""Shared helpers for local_users_groups functional tests."""

from __future__ import annotations

import base64
import getpass
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

MODULE_DIR = Path(__file__).resolve().parents[2]
FUNCTIONAL_DIR = Path(__file__).resolve().parent
ANSIBLE_DIR = FUNCTIONAL_DIR / ".ansible"
WRAPPER_PLAYBOOK = FUNCTIONAL_DIR / "wrapper.yaml"
FACT_FILE = "/etc/ansible/facts.d/mosk_local_users_groups.fact"
DEFAULT_GROUP = "mosk_managed_users"
EXTERNAL_TEST_USER = "hocm_lug_ft_external"

TEST_HOST = os.environ.get("TEST_HOST", "").strip()
TEST_USER = os.environ.get("TEST_USER", "").strip() or getpass.getuser()
TEST_SSH_KEY = os.environ.get("TEST_SSH_KEY", "").strip()


def validate_test_environment() -> None:
    errors: list[str] = []

    if not TEST_HOST:
        errors.append("TEST_HOST must be set to the SSH hostname or IP of the test host")
    if shutil.which("ansible") is None:
        errors.append("ansible must be on PATH")
    if shutil.which("ansible-playbook") is None:
        errors.append("ansible-playbook must be on PATH")
    if TEST_SSH_KEY:
        ssh_key = Path(TEST_SSH_KEY).expanduser()
        if not ssh_key.is_file():
            errors.append(f"TEST_SSH_KEY does not exist: {ssh_key}")

    if errors:
        raise RuntimeError("; ".join(errors))


class FunctionalHost:
    """SSH host helper for applying and verifying the module playbook."""

    def __init__(self, inventory: str, prefix: str = "hocm_lug") -> None:
        self.inventory = inventory
        self.prefix = prefix

    def resource_name(self, suffix: str) -> str:
        return f"{self.prefix}_{suffix}"

    def run_playbook(self, test_values: dict[str, Any]) -> subprocess.CompletedProcess[str]:
        return _run_ansible_playbook(self.inventory, test_values)

    def apply_and_refresh(self, test_values: dict[str, Any]) -> subprocess.CompletedProcess[str]:
        result = self.run_playbook(test_values)
        if result.returncode != 0:
            raise AssertionError(
                f"ansible-playbook failed:\n{result.stdout}\n{result.stderr}"
            )
        return result

    def wipe_managed_state(self) -> None:
        self.run_playbook({"groups": [], "users": []})

    def run_adhoc(self, module: str, args: str) -> dict[str, Any]:
        return _run_ansible_adhoc(self.inventory, module, args)

    def run_command(self, command: str) -> str:
        # Free-form -a args for ansible.builtin.command (do not prefix with cmd=).
        host_result = self.run_adhoc("command", command)
        if host_result.get("rc", 1) != 0:
            raise AssertionError(
                f"command failed ({command}): "
                f"{host_result.get('stderr', host_result.get('msg', ''))}"
            )
        return str(host_result.get("stdout", "")).strip()

    def getent_passwd(self, name: str) -> dict[str, str]:
        line = self.run_command(f"getent passwd {name}")
        if not line:
            raise AssertionError(f"passwd entry not found for {name}")
        parts = line.split(":")
        if len(parts) < 7:
            raise AssertionError(f"unexpected passwd format for {name}: {line}")
        return {
            "name": parts[0],
            "password": parts[1],
            "uid": parts[2],
            "gid": parts[3],
            "gecos": parts[4],
            "home": parts[5],
            "shell": parts[6],
        }

    def getent_group(self, name: str) -> dict[str, Any]:
        line = self.run_command(f"getent group {name}")
        if not line:
            raise AssertionError(f"group entry not found for {name}")
        parts = line.split(":")
        if len(parts) < 4:
            raise AssertionError(f"unexpected group format for {name}: {line}")
        members = [member for member in parts[3].split(",") if member]
        return {
            "name": parts[0],
            "password": parts[1],
            "gid": parts[2],
            "members": members,
        }

    def user_exists(self, name: str) -> bool:
        # shell keeps the ansible task successful when getent misses.
        host_result = self.run_adhoc(
            "shell",
            f"getent passwd {shlex.quote(name)} >/dev/null 2>&1; echo $?",
        )
        return str(host_result.get("stdout", "")).strip() == "0"

    def group_exists(self, name: str) -> bool:
        host_result = self.run_adhoc(
            "shell",
            f"getent group {shlex.quote(name)} >/dev/null 2>&1; echo $?",
        )
        return str(host_result.get("stdout", "")).strip() == "0"

    def path_exists(self, path: str) -> bool:
        host_result = self.run_adhoc(
            "shell",
            f"test -e {shlex.quote(path)}; echo $?",
        )
        return str(host_result.get("stdout", "")).strip() == "0"

    def user_groups(self, name: str) -> list[str]:
        output = self.run_command(f"id -Gn {name}")
        return output.split()

    def password_status(self, name: str) -> str:
        output = self.run_command(f"passwd -S {name}")
        return output.split()[1] if output.split() else ""

    def read_local_fact(self) -> dict[str, Any]:
        host_result = self.run_adhoc("slurp", f"src={FACT_FILE}")
        if host_result.get("failed", False):
            raise AssertionError(f"failed to read fact file: {host_result.get('msg')}")
        content = base64.b64decode(host_result["content"]).decode("utf-8")
        return json.loads(content)

    def ensure_external_user(self, name: str = EXTERNAL_TEST_USER) -> None:
        host_result = self.run_adhoc(
            "user",
            f"name={name} state=present create_home=yes shell=/bin/bash",
        )
        if host_result.get("failed", False):
            raise AssertionError(f"failed to create external user: {host_result.get('msg')}")

    def remove_external_user(self, name: str = EXTERNAL_TEST_USER) -> None:
        self.run_adhoc("user", f"name={name} state=absent remove=yes")


def write_inventory() -> Path:
    host_vars: dict[str, Any] = {
        "ansible_host": TEST_HOST,
        "ansible_user": TEST_USER,
        "ansible_become": True,
        "ansible_become_method": "sudo",
        # Avoid "-S" (read password from stdin): with NOPASSWD sudo, Ansible can
        # still hang waiting for a privilege-escalation prompt.
        "ansible_become_flags": "-H -n",
    }
    if TEST_SSH_KEY:
        host_vars["ansible_ssh_private_key_file"] = TEST_SSH_KEY

    ANSIBLE_DIR.mkdir(parents=True, exist_ok=True)
    inventory_path = Path(tempfile.mkstemp(
        prefix="local_users_groups_inventory_",
        suffix=".yml",
        dir=ANSIBLE_DIR,
    )[1])
    lines = ["all:", "  hosts:", "    testhost:"]
    for key, value in host_vars.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        else:
            rendered = str(value)
        lines.append(f"      {key}: {rendered}")
    inventory_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return inventory_path


def _ansible_env() -> dict[str, str]:
    env = os.environ.copy()
    env["ANSIBLE_HOST_KEY_CHECKING"] = env.get("ANSIBLE_HOST_KEY_CHECKING", "False")
    # Do not force stdout callbacks (yaml/json are unavailable or awkward with
    # ansible-core 2.16 ad-hoc). Parse the default callback's embedded JSON.
    env.pop("ANSIBLE_STDOUT_CALLBACK", None)
    return env


def _run_ansible_playbook(
    inventory: str,
    test_values: dict[str, Any],
) -> subprocess.CompletedProcess[str]:
    extra_vars = json.dumps({"test_values": test_values})
    command = [
        "ansible-playbook",
        str(WRAPPER_PLAYBOOK),
        "-i",
        inventory,
        "-e",
        extra_vars,
    ]
    return subprocess.run(
        command,
        cwd=MODULE_DIR,
        capture_output=True,
        text=True,
        check=False,
        env=_ansible_env(),
    )


def _run_ansible_adhoc(inventory: str, module: str, args: str) -> dict[str, Any]:
    command = [
        "ansible",
        "testhost",
        "-i",
        inventory,
        "-m",
        module,
        "-a",
        args,
        "--become",
    ]
    result = subprocess.run(
        command,
        cwd=MODULE_DIR,
        capture_output=True,
        text=True,
        check=False,
        env=_ansible_env(),
    )
    if result.returncode != 0:
        raise AssertionError(
            f"ansible ad-hoc failed ({module} {args}):\n"
            f"{result.stdout}\n{result.stderr}"
        )

    try:
        return _module_result_from_default_callback(result.stdout)
    except AssertionError as exc:
        raise AssertionError(
            f"ansible ad-hoc failed ({module} {args}):\n"
            f"{result.stdout}\n{result.stderr}"
        ) from exc


def _module_result_from_default_callback(stdout: str) -> dict[str, Any]:
    """Parse module result from the default ansible ad-hoc callback."""
    # Form A: testhost | SUCCESS => { ...json... }
    match = re.search(r"=>\s*(\{.*\})\s*$", stdout, flags=re.DOTALL)
    if match:
        payload = json.loads(match.group(1))
        if isinstance(payload, dict):
            return payload

    # Form B: testhost | CHANGED | rc=0 >>\n<stdout lines>
    match = re.search(
        r"\|\s*(SUCCESS|CHANGED|FAILED|UNREACHABLE).*?\|\s*rc=(?P<rc>-?\d+)\s*>>\s*(?P<body>.*)\Z",
        stdout,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if match:
        status = match.group(1).upper()
        body = match.group("body").strip("\n")
        return {
            "changed": status == "CHANGED",
            "failed": status in {"FAILED", "UNREACHABLE"},
            "rc": int(match.group("rc")),
            "stdout": body,
            "stderr": "",
        }

    start = stdout.find("{")
    end = stdout.rfind("}")
    if start != -1 and end != -1 and end > start:
        payload = json.loads(stdout[start : end + 1])
        if isinstance(payload, dict):
            if "testhost" in payload and isinstance(payload["testhost"], dict):
                return payload["testhost"]
            if any(key in payload for key in ("rc", "changed", "content", "stat", "name")):
                return payload

    raise AssertionError(f"no module result found in ansible output:\n{stdout}")
