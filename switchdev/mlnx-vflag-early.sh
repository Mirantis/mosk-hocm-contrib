#!/bin/bash
# Resilient: do not die on first error; log and continue. Exit 0 at end.
set -uo pipefail
[ -f /etc/sysconfig/sriov ] && source /etc/sysconfig/sriov

PFS_JSON="/etc/lcm/pfs.json"
BOND_NAME="${BOND_NAME:-bond2}"
SRIOV_VF_COUNT=${SRIOV_VF_COUNT:-8}

readarray -t ALL_PFS < <(jq -r '.pfs[].iface' "$PFS_JSON" 2>/dev/null || true)

log()   { logger -t mlnx-vflag-early "$*"; }
warn()  { logger -p user.warning -t mlnx-vflag-early "$*"; }

netplan_pf_list() {
  command -v netplan >/dev/null 2>&1 || return 1
  netplan get "bonds.${BOND_NAME}.interfaces" 2>/dev/null | sed -n 's/^[[:space:]]*-[[:space:]]*//p' | sed 's/[[:space:]]*$//'
}

pf_in_runtime_bond() {
  local pf="$1"
  [[ -L "/sys/class/net/${pf}/master" ]] || return 1
  [[ "$(basename "$(readlink -f "/sys/class/net/${pf}/master")")" == "$BOND_NAME" ]]
}

declare -A is_bond_member=()
if NETPLAN_MEMBERS="$(netplan_pf_list)"; then
  for m in $NETPLAN_MEMBERS; do is_bond_member["$m"]=1; done
  log "Netplan bond ${BOND_NAME} members: ${NETPLAN_MEMBERS:-<none>}"
else
  warn "netplan not available; falling back to runtime master checks"
fi

sriov_vf_create() {
    local PF_NIC=$1 VF_COUNT=$2
    if ! cd "/sys/class/net/${PF_NIC}/device" 2>/dev/null; then
      warn "Cannot cd into /sys/class/net/${PF_NIC}/device"; return 0
    fi
    local PF_PCI="pci/$(basename "$(realpath "$PWD")")"
    log "Creating ${VF_COUNT} VFs for ${PF_NIC} (${PF_PCI})"
    echo "${VF_COUNT}" > sriov_numvfs 2>/dev/null || warn "Failed to set sriov_numvfs on ${PF_NIC}"
    for i in $(readlink virtfn* 2>/dev/null || true); do
        log "Unbinding $(basename "$i")"
        echo "$(basename "$i")" > /sys/bus/pci/drivers/mlx5_core/unbind 2>/dev/null || true
    done
    devlink dev eswitch set "$PF_PCI" mode switchdev >/dev/null 2>&1 || warn "devlink switchdev set failed on $PF_PCI"
    log "After enabling switchdev: $(devlink dev eswitch show "$PF_PCI" 2>/dev/null || echo 'n/a')"
}

enable_tc_offload() {
    local PF_NIC=$1
    local TC_OFFLOAD
    TC_OFFLOAD=$(ethtool -k "$PF_NIC" 2>/dev/null | awk '/hw-tc-offload:/ {print $2}')
    if [[ "${TC_OFFLOAD:-off}" != "on" ]]; then
        log "Enabling HW TC offload for $PF_NIC"
        ethtool -K "$PF_NIC" hw-tc-offload on >/dev/null 2>&1 || warn "failed to enable hw-tc-offload on $PF_NIC"
    fi
}

FILTERED_PFS=()
for pf in "${ALL_PFS[@]}"; do
  if [[ -n "${is_bond_member[$pf]:-}" ]] || pf_in_runtime_bond "$pf"; then
    FILTERED_PFS+=("$pf")
  else
    log "Skipping $pf (not listed in netplan for ${BOND_NAME} and not currently enslaved)"
  fi
done

if [[ "${#FILTERED_PFS[@]}" -eq 0 ]]; then
  log "No PFs matched ${BOND_NAME}; exiting successfully"
  exit 0
fi

for PF in "${FILTERED_PFS[@]}"; do
    sriov_vf_create "$PF" "$SRIOV_VF_COUNT"
    enable_tc_offload "$PF"
done

exit 0
