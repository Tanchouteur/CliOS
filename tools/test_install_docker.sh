#!/usr/bin/env bash
# ==============================================================================
# CliOS - Testeur d'installation dans un conteneur Debian (Raspberry Pi OS)
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME="clios-install-test"
CONTAINER_NAME="clios-test-runner"

echo -e "\033[1;36m▶ [1/3] Construction de l'image de test Docker (Debian Bookworm)...\033[0m"
docker build -t "$IMAGE_NAME" -f "${SCRIPT_DIR}/docker/Dockerfile.debian_test" "${SCRIPT_DIR}/docker"

echo -e "\n\033[1;36m▶ [2/3] Test du mode simulation (--dry-run) dans le conteneur...\033[0m"
docker run --rm -v "${ROOT_DIR}:/home/pi/CliOS:ro" "$IMAGE_NAME" bash -c "cd /home/pi/CliOS && ./install.sh --dry-run --yes"

echo -e "\n\033[1;36m▶ [3/3] Test d'installation complète non-interactive dans un conteneur isolé...\033[0m"
# On copie le projet dans le conteneur pour tester l'installation sans toucher à l'hôte
docker run --rm -v "${ROOT_DIR}:/mnt/src:ro" "$IMAGE_NAME" bash -c "
    mkdir -p /home/pi/CliOS_Test
    cd /home/pi/CliOS_Test
    tar -C /mnt/src --exclude='.venv' --exclude='.git' --exclude='__pycache__' -cf - . | tar -xf -
    ./install.sh --non-interactive --yes
    echo -e '\n\033[1;36m▶ Validation du lanceur clios dans le conteneur...\033[0m'
    ./clios --help
"

echo -e "\n\033[1;32m✓ Tous les tests d'installation dans Docker ont réussi avec succès !\033[0m\n"
