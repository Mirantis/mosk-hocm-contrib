# docker_logging module

Module for configuring Docker daemon log rotation settings (`max-size` and `max-file`) in `/etc/docker/daemon.json`.
The module merges the logging options into the existing `daemon.json` without overwriting unrelated settings, then creats of a special file for LCM agent to request a subsequent reboot.

Changes to daemon.json require a Docker daemon restart to take effect. As a result of the configuration changes Docker daemon will be restarted and subsequent reboot request created. It is recommended to perform this reboot during the next available maintenance window.

## Supported parameters

- `max_size` (string) - Maximum size of a single log file before rotation. Format: `<number>(k\|m\|g)`, e.g. `100m`, `1g`. Default values is `"200m"`.
- `max_file` (string) - Maximum number of rotated log files to retain. Must be a positive integer string, e.g. `"3"`. Default values is `"3"`.

## Example HostOSConfiguration

```yaml
apiVersion: kaas.mirantis.com/v1alpha1
kind: HostOSConfiguration
metadata:
  name: docker-logging-config-300
spec:
  configs:
  - module: docker_logging
    moduleVersion: 1.0.0
    values:
      max_size: "200m"
      max_file: "3"
  machineSelector:
    matchLabels:
      day2-docker_logging-label: "true"
```
