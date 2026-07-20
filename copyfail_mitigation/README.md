# copyfail_mitigation module

The `copyfail_mitigation` module allows operators to mitigate the [Copy Fail vulnerability](https://nvd.nist.gov/vuln/detail/CVE-2026-31431) across many cluster nodes in one operation.

> **Note:** This module supports Ubuntu 22.04 and 24.04 host operating systems.

> **Note:** This module is implemented and validated against the specific Ansible versions provided by MOSK for Ubuntu 22.04 and Ubuntu 24.04 in Cluster release 20.1.0: **Ansible Core 2.16.3** and **Ansible Collection 8.3.0**.
>
> To verify the Ansible version in a specific Cluster release, refer to the
> **Release artifacts > Management cluster artifacts > System and MCR artifacts**
> section of the required management Cluster release in the
> [MOSK documentation: Release notes](https://docs.mirantis.com/mosk/latest/release-notes.html).

# Version 1.1.0 (latest)

The `copyfail_mitigation` module is designed to mitigate the following vulnerability: [Local privilege escalation (Linux kernel "Copy-Fail", CVE-2026-31431) affects Mirantis OpenStack for Kubernetes (MOSK) cluster nodes when AF_ALG/AEAD is exposed](https://github.com/Mirantis/security/blob/main/advisories/0015.md).

The module accepts the following input parameters:

- `revert`: Boolean. Optional (defaults to `false`). Set to `true` to revert the mitigation and restore original kernel settings.

## Mitigation workflow

When `revert` is NOT set to `true`, the module performs the following actions:

1. Creates `/etc/modprobe.d/blacklist-algif_aead.conf` to block loading of the `algif_aead` kernel module.
2. Verifies whether `algif_aead` is currently loaded.

If the kernel module is loaded on the host, the `copyfail_mitigation` module also performs the following actions:

1. Attempts to unload `algif_aead` from the live kernel memory space.
2. Flushes the kernel page cache after a successful unload to purge any volatile in-memory exploitation.
3. Creates a reboot request.

## Rebooting the hosts
After applying the mitigation, you must perform a reboot of affected hosts as soon as possible.
Plan a maintenance window and use the official Mirantis procedure on how to [Perform a graceful reboot of a cluster](https://docs.mirantis.com/mosk/latest/ops/general-operations/graceful-reboot.html).

## Reversion workflow

When the `revert` parameter is set to `true`, the `copyfail_mitigation` module automatically removes `/etc/modprobe.d/blacklist-algif_aead.conf`. This action unblocks and permits the loading of the `algif_aead` kernel module.
Once the HOC has been successfully applied with `revert: true` parameter, you can safely delete the HOC object using `kubectl delete hoc` command.

# Configuration examples

Example of a `HostOSConfiguration` custom resource for the `copyfail_mitigation` module version 1.1.0 for applying the mitigation:

```yaml
apiVersion: kaas.mirantis.com/v1alpha1
kind: HostOSConfiguration
metadata:
  name: copyfail-mitigation
  namespace: default
spec:
  configs:
  - module: copyfail_mitigation
    moduleVersion: 1.1.0
    values: {}
  machineSelector:
    matchLabels:
      copyfail-mitigation-label: 'true'
```

Example of a `HostOSConfiguration` custom resource for the `copyfail_mitigation` module version 1.1.0 for reverting the mitigation:

```yaml
apiVersion: kaas.mirantis.com/v1alpha1
kind: HostOSConfiguration
metadata:
  name: copyfail-mitigation
  namespace: default
spec:
  configs:
  - module: copyfail_mitigation
    moduleVersion: 1.1.0
    values:
      revert: true
  machineSelector:
    matchLabels:
      copyfail-mitigation-label: 'true'
```

---