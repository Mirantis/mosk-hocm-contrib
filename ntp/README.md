# NTP - host OS configuration module for MOSK

The module allows cloud operators to enable and configure NTP-based time synchronisation on deployed machines comprising a MOSK cluster. The module is implemented within the MOSK's [Host OS configuration framework](https://docs.mirantis.com/mosk/latest/ops/bm-operations/host-os-conf.html)

> Note: This module is tested against the following versions of Ansible that are provided by Ubuntu 22.04 shipped with MOSK Cluster releases 16.3.0 and 17.3.0: Ansible core 2.12.10 and Ansible collection 5.10.0.
>
> To verify the Ansible version in a specific Cluster release, refer to
> [Container Cloud documentation: Release notes - Cluster releases](https://docs.mirantis.com/container-cloud/latest/release-notes/cluster-releases.html).
> Use the *Artifacts > System and MCR artifacts* section of the corresponding Cluster release. For example, for
> [17.3.0](https://docs.mirantis.com/container-cloud/latest/release-notes/cluster-releases/17-x/17-3-x/17-3-0/17-3-0-artifacts.html#system-and-mcr-artifacts).

# Version 1.0.0 (latest)

Using the NTP module 1.0.0, you can configure the list of NTP servers on the hosts.

The module contains the following input parameters:

- `ntp_servers`: List of NTP servers.

# Configuration examples

Example of `HostOSConfiguration` with the `ntp` module 1.0.0 that configures NTP servers on MOSK compute nodes. 

```yaml
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
          openstack-compute-node=enabled: "true"
```
