# switchdev - host OS configuration module for MOSK

This module allows the operator to enable VFs and the switchdev mode for Mellanox/Nvidia NICs on MOSK deployed computes.

## Configuration examples

```
apiVersion: kaas.mirantis.com/v1alpha1
kind: HostOSConfiguration
metadata:
  name: compute-switchdev-bond2
  namespace: managed_cloud
spec:
   machineSelector:
      matchLabels:
        machines.mosk.nsscloud.io/node: "compute-bond2"
   configs:
   - description: Enable switchdev mode on supported Mellanox NICs
     module: switchdev
     moduleVersion: 1.0.0
     values:
       bond_name: bond2
       num_vfs: 64
```