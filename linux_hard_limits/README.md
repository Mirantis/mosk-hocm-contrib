# linux_hard_limit module

The `linux_hard_limit` module allows the operator to manage system hard limits at runtime on cluster machines using the mechanism implemented in the day-2 operations API.

> Note: This module is implemented only for the Ubuntu 22.04 host OS.

> Note: This module is implemented and validated against the following Ansible versions provided by MCC for Ubuntu 22.04 in the Cluster release 17.3.0: Ansible Core 2.12.10 and Ansible Collection 5.10.0.
>
> To verify the Ansible version in a specific Cluster release, refer to
> [Container Cloud documentation: Release notes - Cluster releases](https://docs.mirantis.com/container-cloud/latest/release-notes/cluster-releases.html).
> Use the *Artifacts > System and MCR artifacts* section of the corresponding Cluster release. For example, for [17.3.0](https://docs.mirantis.com/container-cloud/latest/release-notes/cluster-releases/17-x/17-3-x/17-3-0/17-3-0-artifacts.html#system-and-mcr-artifacts).

# Version 1.0.0 (latest)

Using the `linux_hard_limit` module 1.0.0, you can configure the hard limits of the Linux kernel using several mechanisms:
- `ulimit` rules, which will be stored in the `/etc/security/limits.d/98-day2-limits.conf` configuration file.
- `nproc` limit will also update the sysctl parameter `kernel.pid_max` using the `/etc/sysctl.d/98-day2-fs.file-max.conf` configuration file.
- `nofile` limit is more complicated to configure under the hood:
  1. A corresponding `ulimit` rule will be added to `/etc/security/limits.d/98-day2-limits.conf`.
  2. The sysctl parameters `fs.file-max` and `fs.nr_open` will be applied using the `/etc/sysctl.d/98-day2-fs.file-max.conf` configuration file.
  3. The systemd parameter `DefaultLimitNOFILE` will be updated using the `/etc/systemd/system.conf` and `/etc/systemd/user.conf` files.
  4. pamd daemon configuration will be extended with the `pam_limits.so` module for the `/etc/pam.d/common-session` and `/etc/pam.d/common-session-noninteractive` configuration files.

> CAUTION: The module could produce conflicts with the sysctl module for `fs.file-max` and `fs.nr_open` parameters.

The module contains the following input parameters:

- `cleanup_before`: Optional, boolean. Enables pre-cleanup of any module traces, including all configuration files mentioned above. Default is false (cleanup disabled).
- `disable_reboot_request`: Optional, boolean. Disables creating files for reboot requests. Default is false (reboot will be requested).
- `limits_filename`: Optional, string. Specifies config file name for /etc/security/limits.d/ directory (without `.conf`). Default is `98-day2-limits`.
- `sysctl_filename`: Optional, string. Specifies config file name for /etc/sysctl.d/ directory (without `.conf`). Default is `98-day2-limits`.
- `system`: Dictionary of `limit_item: limit_value` that will be configured at the system level (`*` for limits.conf rules, additional configuration for `nproc` and `nofile` limits).
- `user`: Limit configurations per user, see the example below.

If the parameter `cleanup_before` is set to `true` and the sections `system` and `user` are not present, the module will wipe all limits configured by itself, effectively restoring system's default parameters.
It is advised to set `cleanup_before` to true to avoid misconfiguration of the target host.

> WARNING: Changing `limits_filename` or `sysctl_filename` when limits are applied will not delete old files. This could lead to leftover traces in the OS, potentially causing unpredictable behavior. It is strongly advised to trigger the cleanup procedure described in this documentation.

> WARNING: Do not use system-wide `/etc/sysctl/sysctl.conf` and `/etc/security/limits.conf` files. The module will erase the files at cleanup state which will causes unpredictable issues.

> Note: Changing limits on the fly is not possible consistently. Rebooting the system is required to apply limits for all running processes.
> To perform the reboot, create a [GracefulRebootRequest](https://docs.mirantis.com/container-cloud/latest/api/api-graceful-reboot-request.html) object with a specific machine name.

> WARNING: on host with running Docker Swarm setting limits value for `system` or `root` lower than listed below will cause Docker Swarm to fail:
> `nproc`: `1048576`
> `nofile`: `524288`

# Configuration examples

Example of `HostOSConfiguration` with the `linux_hard_limit` module 1.0.0 for configuring limits for maximum open files and maximum processes:

```yaml
apiVersion: kaas.mirantis.com/v1alpha1
kind: HostOSConfiguration
metadata:
  name: limits-200
  namespace: mosk
spec:
  configs:
  - module: linux_hard_limits
    moduleVersion: 1.0.0
    values:
      cleanup_before: true
      system:
        nofile: 2147483583
        nproc: 4194303
      users:
        mcc-user:
          nofile: 16384
          nproc: 4096
        root:
          nofile: 524288
          nproc: 63228
  machineSelector:
    matchLabels:
      day2-linux-module: 'true'
```

Example of `HostOSConfiguration` with the `linux_hard_limits` module 1.0.0 for dropping previously configured kernel parameters:

```yaml
apiVersion: kaas.mirantis.com/v1alpha1
kind: HostOSConfiguration
metadata:
  name: limits-200
  namespace: mosk
spec:
  configs:
  - module: linux_hard_limits
    moduleVersion: 1.0.0
    values:
      cleanup_before: true
  machineSelector:
    matchLabels:
      day2-linux-module: 'true'
```

---
