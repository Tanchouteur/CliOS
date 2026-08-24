#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:---fixture}"
if [[ "$mode" != "--fixture" && "$mode" != "--full" ]]; then
    echo "usage: $0 [--fixture|--full]" >&2
    exit 2
fi

for suite in bookworm trixie; do
    image="clios-updater-lab:${suite}"
    container="clios-updater-lab-${suite}-${RANDOM}"
    docker build --build-arg "DEBIAN_SUITE=${suite}" -t "$image" \
        -f "$root_dir/tools/updater_lab/Dockerfile.systemd" "$root_dir"
    docker run --privileged --detach --name "$container" \
        --tmpfs /run --tmpfs /run/lock -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
        -v "$root_dir:/workspace:ro" "$image" >/dev/null
    cleanup() { docker rm --force "$container" >/dev/null 2>&1 || true; }
    trap cleanup EXIT

    systemd_ready=false
    for _attempt in {1..50}; do
        if docker exec "$container" systemctl show-environment >/dev/null 2>&1; then
            systemd_ready=true
            break
        fi
        sleep 0.2
    done
    if [[ "$systemd_ready" != true ]]; then
        docker logs "$container" >&2
        echo "systemd n'est pas devenu disponible dans $container" >&2
        exit 1
    fi
    docker exec -w /workspace "$container" python3 -m unittest \
        tests.test_updater_service tests.test_updater_socket_lab tests.test_updater_signed_fixtures \
        tests.test_release_manager -v
    docker exec "$container" systemd-run --wait --pipe --collect \
        --unit="clios-updater-probe-${suite}" \
        --property=User=root --property=Group=clios --property=NoNewPrivileges=yes \
        --property=PrivateTmp=yes --property=PrivateDevices=yes --property=ProtectSystem=strict \
        --property=ProtectHome=yes --property=MemoryDenyWriteExecute=yes \
        --property="CapabilityBoundingSet=CAP_CHOWN CAP_DAC_OVERRIDE CAP_FOWNER CAP_SETGID CAP_SETUID" \
        --property=AmbientCapabilities=CAP_SETUID \
        --property="RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6" \
        --property=RuntimeDirectory=clios-updater-lab \
        --property=RuntimeDirectoryMode=0770 \
        --property=ReadWritePaths=/run/clios-updater-lab \
        /usr/bin/python3 /workspace/tools/updater_lab/systemd_probe.py

    if [[ "$mode" == "--full" ]]; then
        target="${suite}-arm64"
        docker exec -w /workspace "$container" python3 tools/verify_wheelhouse.py \
            "requirements-${target}.lock" "wheelhouses/${target}"
    fi
    cleanup
    trap - EXIT
done
