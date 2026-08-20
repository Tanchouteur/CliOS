#!/usr/bin/env bash
# ==============================================================================
# CliOS - Script de Mise à Jour Automatique
# Description: Récupère les dernières modifications Git, met à jour les dépendances
#              Python (.venv) et réapplique les permissions.
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}"
VENV_PIP="${PROJECT_DIR}/.venv/bin/pip"

echo -e "\033[1;34m▶ [1/3] Récupération des mises à jour depuis GitHub...\033[0m"
cd "$PROJECT_DIR"

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo -e "\033[1;31m[ERREUR] Le dossier ${PROJECT_DIR} n'est pas un dépôt Git valide.\033[0m" >&2
    exit 1
fi

git fetch origin

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'main')"
echo -e " ℹ Branche active : \033[1m${CURRENT_BRANCH}\033[0m"

# Application de la mise à jour Git
git pull --rebase origin "$CURRENT_BRANCH"
echo -e "\033[1;32m✓ Code source mis à jour avec succès.\033[0m"

echo -e "\n\033[1;34m▶ [2/3] Vérification des dépendances Python...\033[0m"
if [[ -f "$VENV_PIP" && -f "${PROJECT_DIR}/requirements.txt" ]]; then
    echo " ℹ Mise à niveau des paquets Python dans .venv..."
    "$VENV_PIP" install -r "${PROJECT_DIR}/requirements.txt"
    echo -e "\033[1;32m✓ Dépendances Python à jour.\033[0m"
else
    echo " ℹ Environnement .venv non trouvé ou incomplet, passage de la mise à jour pip."
fi

echo -e "\n\033[1;34m▶ [3/3] Réapplication des permissions exécutables...\033[0m"
chmod +x "${PROJECT_DIR}/clios" "${PROJECT_DIR}/install.sh" "${PROJECT_DIR}/update.sh" "${PROJECT_DIR}"/tools/*.sh 2>/dev/null || true
echo -e "\033[1;32m✓ Permissions réappliquées.\033[0m"

echo -e "\n\033[1;32m══════════════════════════════════════════════════════════════════\033[0m"
echo -e "\033[1;32m  ✓ MISE À JOUR DE CliOS TERMINÉE AVEC SUCCÈS !\033[0m"
echo -e "\033[1;32m══════════════════════════════════════════════════════════════════\033[0m\n"
