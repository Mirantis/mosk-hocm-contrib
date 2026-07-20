#!/bin/bash
set -euo pipefail
PFS_JSON="/etc/lcm/pfs.json"
TIMEOUT="${PFS_WAIT_TIMEOUT:-120}"
SLEEP="${PFS_WAIT_INTERVAL:-1}"

if [[ ! -s "$PFS_JSON" ]]; then
  echo "mlnx-wait-pfs: $PFS_JSON missing or empty"
  exit 1
fi

mapfile -t PF_LIST < <(jq -r '.pfs[].iface' "$PFS_JSON" 2>/dev/null || true)
if [[ "${#PF_LIST[@]}" -eq 0 ]]; then
  echo "mlnx-wait-pfs: no Mellanox PFs in $PFS_JSON (nothing to wait for)"
  exit 0
fi

deadline=$(( $(date +%s) + TIMEOUT ))

while :; do
  all_ok=1
  for pf in "${PF_LIST[@]}"; do
    [[ -d "/sys/class/net/${pf}" ]] || { all_ok=0; break; }
  done
  if [[ $all_ok -eq 1 ]]; then
    echo "mlnx-wait-pfs: all PFs present"
    exit 0
  fi
  if (( $(date +%s) >= deadline )); then
    echo "mlnx-wait-pfs: timeout waiting for PF presence"
    exit 1
  fi
  sleep "$SLEEP"
done
