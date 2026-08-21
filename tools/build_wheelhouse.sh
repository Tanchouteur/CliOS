#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-bookworm-arm64}"
case "${TARGET}" in
    bookworm-arm64) EXPECTED_PYTHON="3.11" ;;
    trixie-arm64) EXPECTED_PYTHON="3.13" ;;
    *) echo "cible non prise en charge: ${TARGET}" >&2; exit 2 ;;
esac
WHEEL_DIR="${ROOT_DIR}/wheelhouses/${TARGET}"
LOCK_FILE="${ROOT_DIR}/requirements-${TARGET}.lock"

test "$(uname -m)" = "aarch64"
test "$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" = "${EXPECTED_PYTHON}"
mkdir -p "${WHEEL_DIR}"
BUILD_VENV="$(mktemp -d -t clios-wheelhouse.XXXXXX)"
trap 'rm -rf -- "${BUILD_VENV}"' EXIT
python3 -m venv --system-site-packages "${BUILD_VENV}"
export CFLAGS="${CFLAGS:-} -Wno-incompatible-pointer-types -Wno-error"
"${BUILD_VENV}/bin/pip" wheel --require-hashes --wheel-dir "${WHEEL_DIR}" --requirement "${LOCK_FILE}"

# Un wheel doit exister pour chaque exigence active : aucun build ne sera fait
# sur le Raspberry Pi pendant une mise à jour.
python3 "${ROOT_DIR}/tools/verify_wheelhouse.py" "${LOCK_FILE}" "${WHEEL_DIR}"
