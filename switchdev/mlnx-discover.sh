#!/bin/bash
set -euo pipefail
PFS_JSON="/etc/lcm/pfs.json"
tmp="$(mktemp "${PFS_JSON}.XXXXXX")"

shopt -s nullglob
declare -a rows=()
for path in /sys/class/net/*; do
  iface="$(basename "$path")"
  [[ "$iface" == "lo" ]] && continue
  if [[ -f "$path/device/vendor" ]] && grep -qi '^0x15b3' "$path/device/vendor"; then
    pci="$(basename "$(realpath "$path/device")")"
    rows+=("{\"iface\":\"${iface}\",\"pci\":\"${pci}\"}")
  fi
done

printf '{ "pfs": [%s] }\n' "$(IFS=,; echo "${rows[*]-}")" | jq -c . > "$tmp" || echo '{ "pfs": [] }' > "$tmp"
install -o root -g root -m 0644 "$tmp" "$PFS_JSON"
rm -f "$tmp"
logger -t mlnx-discover "PF inventory written to $PFS_JSON"
exit 0
