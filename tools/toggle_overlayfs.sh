#!/usr/bin/env bash
# ==============================================================================
# CliOS - Bascule de la protection SD (OverlayFS Raspberry Pi)
# ==============================================================================

set -eo pipefail

if ! command -v raspi-config &>/dev/null; then
    echo -e "\033[1;33m[ATTENTION] raspi-config n'est pas installé sur ce système.\033[0m"
    echo "Cette fonctionnalité est réservée aux systèmes Raspberry Pi OS."
    exit 1
fi

# Récupération de l'état actuel : 0 = activé (Read-Only), 1 = désactivé (Read-Write).
# -n interdit toute attente de mot de passe dans Cage ; l'installateur fournit
# une règle sudoers limitée à ces trois commandes exactes.
if ! STATUS="$(sudo -n /usr/bin/raspi-config nonint get_overlay_now 2>/dev/null)"; then
    echo -e "\033[1;31m[ERREUR] Autorisation OverlayFS absente. Relancez install.sh.\033[0m" >&2
    exit 1
fi

if [[ "$STATUS" == "0" ]]; then
    echo -e "\033[1;33m[INFO] Désactivation de la protection OverlayFS (Passage en mode Lecture/Écriture)...\033[0m"
    sudo -n /usr/bin/raspi-config nonint disable_overlayfs
    echo -e "\033[1;32m✓ Protection SD désactivée. Redémarrez le Raspberry Pi pour valider.\033[0m"
else
    echo -e "\033[1;34m[INFO] Activation de la protection OverlayFS (Passage en mode Lecture Seule)...\033[0m"
    sudo -n /usr/bin/raspi-config nonint enable_overlayfs
    echo -e "\033[1;32m✓ Protection SD activée. Redémarrez le Raspberry Pi pour valider.\033[0m"
fi
