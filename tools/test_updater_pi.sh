#!/usr/bin/env bash
set -euo pipefail

remote=""
if [[ "${1:-}" == "--ssh" ]]; then
    remote="${2:?usage: $0 [--ssh user@raspberry-pi]}"
fi

probe='systemd-run --wait --pipe --collect --unit=clios-updater-pi-probe \
  --property=User=root --property=Group=clios --property=NoNewPrivileges=yes \
  --property=PrivateTmp=yes --property=PrivateDevices=yes --property=ProtectSystem=strict \
  --property=ProtectHome=yes --property=MemoryDenyWriteExecute=yes \
  --property="CapabilityBoundingSet=CAP_CHOWN CAP_DAC_OVERRIDE CAP_FOWNER CAP_SETGID CAP_SETUID" \
  --property=AmbientCapabilities=CAP_SETUID \
  --property="RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6" \
  --property=RuntimeDirectory=clios-updater-lab --property=RuntimeDirectoryMode=0770 \
  --property=ReadWritePaths=/run/clios-updater-lab \
  /usr/bin/python3 /opt/clios/current/tools/updater_lab/systemd_probe.py'

if [[ -n "$remote" ]]; then
    ssh "$remote" "sudo $probe"
else
    sudo bash -c "$probe"
fi
