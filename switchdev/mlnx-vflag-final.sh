#!/bin/bash
set -uo pipefail
PFS_JSON="/etc/lcm/pfs.json"
BOND_NAME="${BOND_NAME:-bond2}"

log()   { logger -t mlnx-vflag-final "$*"; }
warn()  { logger -p user.warning -t mlnx-vflag-final "$*"; }

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

sriov_vf_bind() {
    local PF_NIC=$1
    if [[ ! -d "/sys/class/net/${PF_NIC}" ]]; then
        warn "NIC ${PF_NIC} not found; skipping"; return 0
    fi
    if [[ -z "${is_bond_member[$PF_NIC]:-}" ]] && ! pf_in_runtime_bond "$PF_NIC"; then
        warn "NIC ${PF_NIC} not in ${BOND_NAME} (netplan or runtime); skipping"; return 0
    fi
    cd "/sys/class/net/${PF_NIC}/device" 2>/dev/null || { warn "cannot cd to device for $PF_NIC"; return 0; }
    for i in $(readlink virtfn* 2>/dev/null || true); do
        log "Binding $(basename "$i")"
        echo "$(basename "$i")" > /sys/bus/pci/drivers/mlx5_core/bind 2>/dev/null || true
    done
}

readarray -t SRIOV_PFS < <(jq -r '.pfs[].iface' "$PFS_JSON" 2>/dev/null || true)
if [[ "${#SRIOV_PFS[@]}" -eq 0 ]]; then
  log "No PFs in $PFS_JSON; exiting successfully"; exit 0
fi

for PF in "${SRIOV_PFS[@]}"; do
    sriov_vf_bind "$PF"
done
exit 0
