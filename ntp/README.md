# ntp module

The ntp module allows the operator to manage ntp servers at runtime on cluster machines using the mechanism implemented in the day-2 operations API.

> Note: This module is implemented and validated against the following Ansible versions provided by MCC for Ubuntu 22.04
> in the Cluster releases 16.3.0 and 17.3.0: Ansible core 2.12.10 and Ansible collection 5.10.0.
>
> To verify the Ansible version in a specific Cluster release, refer to
> [Container Cloud documentation: Release notes - Cluster releases](https://docs.mirantis.com/container-cloud/latest/release-notes/cluster-releases.html).
> Use the *Artifacts > System and MCR artifacts* section of the corresponding Cluster release. For example, for
> [17.3.0](https://docs.mirantis.com/container-cloud/latest/release-notes/cluster-releases/17-x/17-3-x/17-3-0/17-3-0-artifacts.html#system-and-mcr-artifacts).

# Version 1.0.0 (latest)

Using the ntp module 1.0.0, you can configure list of ntp servers.
The module contains the following input parameters:

- `ntp_servers`: List of NTP server.

# Configuration examples

Example of `HostOSConfiguration` with the ntp module 1.0.0 for configuration of ntp servers:

```
    apiVersion: kaas.mirantis.com/v1alpha1
    kind: HostOSConfiguration
    metadata:
      name: ntp-200
      namespace: default
    spec:
      configs:
      - module: ntp
        moduleVersion: 1.0.0
        values:
          ntp_servers:
            - 0.ubuntu.pool.ntp.org
            - 1.ubuntu.pool.ntp.org
            - 2.ubuntu.pool.ntp.org
            - 3.ubuntu.pool.ntp.org
      machineSelector:
        matchLabels:
          day2-custom-label: "true"
```
