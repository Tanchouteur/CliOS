#!/usr/bin/env bash
# ==============================================================================
# CliOS - Testeur d'installation dans un conteneur Debian (Raspberry Pi OS)
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

for suite in bookworm trixie; do
    image_name="clios-install-test-${suite}"

    echo -e "\033[1;36m▶ [${suite}] Construction de l'image de test Docker...\033[0m"
    docker build \
        --build-arg "DEBIAN_SUITE=${suite}" \
        -t "$image_name" \
        -f "${SCRIPT_DIR}/docker/Dockerfile.debian_test" \
        "${SCRIPT_DIR}/docker"

    echo -e "\n\033[1;36m▶ [${suite}] Test du mode simulation (--dry-run)...\033[0m"
    docker run --rm -v "${ROOT_DIR}:/home/pi/CliOS:ro" "$image_name" \
        bash -c "cd /home/pi/CliOS && ./install.sh --dry-run --yes"

    echo -e "\n\033[1;36m▶ [${suite}] Test d'installation complète non-interactive...\033[0m"
    # Le projet est copié afin que l'installation ne modifie jamais l'hôte.
    docker run --rm -v "${ROOT_DIR}:/mnt/src:ro" "$image_name" bash -c "
        mkdir -p /home/pi/CliOS_Test
        cd /home/pi/CliOS_Test
        tar -C /mnt/src --exclude='.venv' --exclude='.git' --exclude='__pycache__' -cf - . | tar -xf -
        ./install.sh --non-interactive --yes
        echo -e '\n\033[1;36m▶ Validation du lanceur clios dans le conteneur...\033[0m'
        ./clios --help
    "
done

echo -e "\n\033[1;32m✓ Tous les tests d'installation dans Docker ont réussi avec succès !\033[0m\n"
