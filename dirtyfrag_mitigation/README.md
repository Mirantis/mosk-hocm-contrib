# dirtyfrag_mitigation module

The `dirtyfrag_mitigation` module allows operators to mitigate the Dirty Frag [CVE-2026-43284](https://nvd.nist.gov/vuln/detail/CVE-2026-43284) / [CVE-2026-43500](https://nvd.nist.gov/vuln/detail/CVE-2026-43500)  across many cluster nodes in one operation.

> **Note:** This module supports Ubuntu 22.04 and 24.04 host operating systems.

> **Note:** This module is implemented and validated against the specific Ansible versions provided by MOSK for Ubuntu 22.04 and Ubuntu 24.04 in Cluster release 20.1.0: **Ansible Core 2.16.3** and **Ansible Collection 8.3.0**.
>
> To verify the Ansible version in a specific Cluster release, refer to the
> **Release artifacts > Management cluster artifacts > System and MCR artifacts**
> section of the required management Cluster release in the
> [MOSK documentation: Release notes](https://docs.mirantis.com/mosk/latest/release-notes.html).

# Version 1.0.0 (latest)

The `dirtyfrag_mitigation` module is designed to mitigate the following vulnerability: [Local privilege escalation (Linux kernel "Dirty Frag", CVE-2026-43284 and CVE-2026-43500) affects Mirantis OpenStack for Kubernetes (MOSK) cluster nodes when ESP or RxRPC paths are exposed](https://github.com/Mirantis/security/blob/main/advisories/0017.md).

The module accepts the following input parameters:

- `skipDisablingEspModules`: Boolean. Optional. Defaults to `true`. Set to `false` to skip disabling Linux kernel modules `esp4` and `esp6`. See the [MOSK clusters with Neutron IPsec-based features enabled](https://github.com/Mirantis/security/blob/main/advisories/0017.md#c-mosk-clusters-with-neutron-ipsec-based-features-enabled) section of the security advisory for details.
- `revert`: Boolean. Optional. Defaults to `false`. Set to `true` to revert the mitigation and restore original kernel settings.

## Pre-mitigation requirements

For clouds using `East–West tenant traffic encryption` and/or `VPNaaS` (OpenStack Neutron IPsec features, not control-plane WireGuard encryption), `esp4` / `esp6` are required for that functionality. Until patched modules are available, disable the relevant features using the procedures from the [MOSK clusters with Neutron IPsec-based features enabled](https://github.com/Mirantis/security/blob/main/advisories/0017.md#c-mosk-clusters-with-neutron-ipsec-based-features-enabled) (only the features you use), or accept residual exposure until patches arrive—risk acceptance must be explicit.

## Mitigation workflow

When `revert` is NOT set to `true`, the module performs the following actions:

1. Creates `/etc/modprobe.d/blacklist-rxrpc.conf` to block loading of the `rxrpc` kernel module.
2. Attempts to unload `rxrpc` from the live kernel memory space if loaded.
3. If `skipDisablingEspModules` is not set to `true`, creates `/etc/modprobe.d/blacklist-esp.conf` to block `esp4` and `esp6` kernel modules.
4. Verifies whether `esp4` or `esp6` is currently loaded.

If any of the kernel modules are loaded on the host, the `dirtyfrag_mitigation` module also performs the following actions:

1. Flushes the IPsec `xfrm` state and policy to clear module hooks.
2. Attempts to unload `esp4` and `esp6` from the live kernel memory space if loaded.

If any of `rxrpc`, `esp4`, or `esp6` were loaded on the host:

1. Flushes the kernel page cache after a successful unload to purge any volatile in-memory exploitation artifacts.
2. Creates a reboot request.

## Rebooting the hosts

After applying the mitigation, you must reboot the affected hosts as soon as possible.
Plan a maintenance window and use the official Mirantis procedure on how to [Perform a graceful reboot of a cluster](https://docs.mirantis.com/mosk/latest/ops/general-operations/graceful-reboot.html).

## Reversion workflow

When the `revert` parameter is set to `true`, the `dirtyfrag_mitigation` module automatically removes `/etc/modprobe.d/blacklist-rxrpc.conf` and `/etc/modprobe.d/blacklist-esp.conf` files. This action unblocks the loading of the `rxrpc`, `esp4`, and `esp6` kernel modules.
Once the `HostOSConfiguration` (HOC) has been successfully applied with the `revert: true` parameter, you can safely delete the HOC object using the `kubectl delete hoc` command.

# Configuration examples

Example of a `HostOSConfiguration` custom resource for the `dirtyfrag_mitigation` module version 1.0.0 for applying the mitigation:

```yaml
apiVersion: kaas.mirantis.com/v1alpha1
kind: HostOSConfiguration
metadata:
  name: dirtyfrag-mitigation
  namespace: default
spec:
  configs:
  - module: dirtyfrag_mitigation
    moduleVersion: 1.0.0
    values: {}
  machineSelector:
    matchLabels:
      dirtyfrag-mitigation-label: 'true'
```

Example of a `HostOSConfiguration` custom resource for the `dirtyfrag_mitigation` module version 1.0.0 for applying the mitigation while keeping modules `esp4`/`esp6` untouched:

```yaml
apiVersion: kaas.mirantis.com/v1alpha1
kind: HostOSConfiguration
metadata:
  name: dirtyfrag-mitigation
  namespace: default
spec:
  configs:
  - module: dirtyfrag_mitigation
    moduleVersion: 1.0.0
    values:
      skipDisablingEspModules: true
  machineSelector:
    matchLabels:
      dirtyfrag-mitigation-label: 'true'
```

Example of a `HostOSConfiguration` custom resource for the `dirtyfrag_mitigation` module version 1.0.0 for reverting the mitigation:

```yaml
apiVersion: kaas.mirantis.com/v1alpha1
kind: HostOSConfiguration
metadata:
  name: dirtyfrag-mitigation
  namespace: default
spec:
  configs:
  - module: dirtyfrag_mitigation
    moduleVersion: 1.0.0
    values:
      revert: true
  machineSelector:
    matchLabels:
      dirtyfrag-mitigation-label: 'true'
```

---