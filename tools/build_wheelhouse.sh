#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHEEL_DIR="${ROOT_DIR}/wheels"
LOCK_FILE="${ROOT_DIR}/requirements-bookworm-arm64.lock"

test "$(uname -m)" = "aarch64"
test "$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" = "3.11"
mkdir -p "${WHEEL_DIR}"
BUILD_VENV="$(mktemp -d -t clios-wheelhouse.XXXXXX)"
trap 'rm -rf -- "${BUILD_VENV}"' EXIT
python3 -m venv "${BUILD_VENV}"
"${BUILD_VENV}/bin/pip" wheel --require-hashes --wheel-dir "${WHEEL_DIR}" --requirement "${LOCK_FILE}"

# Un wheel doit exister pour chaque exigence active : aucun build ne sera fait
# sur le Raspberry Pi pendant une mise à jour.
python3 "${ROOT_DIR}/tools/verify_wheelhouse.py" "${LOCK_FILE}" "${WHEEL_DIR}"
