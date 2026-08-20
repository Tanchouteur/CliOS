#!/usr/bin/env bash
# ==============================================================================
#  ____ _ _  ___  ____  
# / ___| (_)/ _ \/ ___| 
#| |   | | | | | \___ \ 
#| |___| | | |_| |___) |
# \____|_|_|\___/|____/ 
#
# CliOS - Installateur Interactif & Gestionnaire de Déploiement
# Description: Prépare les dépendances système, compile pyo, configure l'environnement
#              virtuel .venv, les règles udev, les services CAN et l'autostart Kiosk.
# ==============================================================================

set -eo pipefail

# ------------------------------------------------------------------------------
# 1. Variables & Chemins
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}"
CURRENT_USER="${SUDO_USER:-${USER:-$(id -un 2>/dev/null || whoami)}}"
VENV_DIR="${PROJECT_DIR}/.venv"
INSTALL_ETC_DIR="${PROJECT_DIR}/installation/etc"

SYSTEMD_DIR="/etc/systemd/system"
UDEV_RULES_DIR="/etc/udev/rules.d"

# Flags d'exécution
DRY_RUN=0
VENV_ONLY=0
NON_INTERACTIVE=0
DO_UNINSTALL=0

# ------------------------------------------------------------------------------
# 2. Couleurs & Mise en page CLI
# ------------------------------------------------------------------------------
if [[ -t 1 ]]; then
    C_RESET="\033[0m"
    C_BOLD="\033[1m"
    C_DIM="\033[2m"
    C_RED="\033[1;31m"
    C_GREEN="\033[1;32m"
    C_YELLOW="\033[1;33m"
    C_BLUE="\033[1;34m"
    C_MAGENTA="\033[1;35m"
    C_CYAN="\033[1;36m"
    C_WHITE="\033[1;37m"
else
    C_RESET=""
    C_BOLD=""
    C_DIM=""
    C_RED=""
    C_GREEN=""
    C_YELLOW=""
    C_BLUE=""
    C_MAGENTA=""
    C_CYAN=""
    C_WHITE=""
fi

print_banner() {
    echo -e "${C_CYAN}${C_BOLD}"
    cat << "EOF"
   ____ _ _  ___  ____  
  / ___| (_)/ _ \/ ___| 
 | |   | | | | | \___ \ 
 | |___| | | |_| |___) |
  \____|_|_|\___/|____/ 
EOF
    echo -e "${C_RESET}${C_WHITE}${C_BOLD} Tableau de Bord Automobile Modulaire${C_RESET}"
    echo -e "${C_DIM} Assistant d'installation & configuration système${C_RESET}"
    echo -e "${C_DIM} Dossier cible : ${PROJECT_DIR}${C_RESET}"
    echo -e "${C_CYAN}══════════════════════════════════════════════════════════════════${C_RESET}\n"
}

log_step() {
    echo -e "\n${C_BLUE}${C_BOLD}▶ [$1] $2${C_RESET}"
    echo -e "${C_DIM}──────────────────────────────────────────────────────────────────${C_RESET}"
}

log_info() {
    echo -e " ${C_CYAN}ℹ${C_RESET} $1"
}

log_success() {
    echo -e " ${C_GREEN}✓${C_RESET} $1"
}

log_warn() {
    echo -e " ${C_YELLOW}⚠${C_RESET} ${C_BOLD}$1${C_RESET}"
}

log_error() {
    echo -e " ${C_RED}✗ ERREUR :${C_RESET} $1" >&2
}

log_dry() {
    echo -e " ${C_MAGENTA}[DRY-RUN]${C_RESET} ${C_DIM}$1${C_RESET}"
}

# ------------------------------------------------------------------------------
# 3. Fonctions Utilitaires
# ------------------------------------------------------------------------------
run_cmd() {
    local cmd_desc="$1"
    shift
    if [[ $DRY_RUN -eq 1 ]]; then
        log_dry "Commande simulée : $*"
        return 0
    fi
    log_info "$cmd_desc"
    "$@"
}

run_sudo_cmd() {
    local cmd_desc="$1"
    shift
    if [[ $DRY_RUN -eq 1 ]]; then
        log_dry "Commande sudo simulée : sudo $*"
        return 0
    fi
    log_info "$cmd_desc"
    if [[ $EUID -eq 0 ]]; then
        "$@"
    else
        sudo "$@"
    fi
}

safe_systemctl() {
    local action_desc="$1"
    shift
    if command -v systemctl &>/dev/null; then
        run_sudo_cmd "$action_desc" systemctl "$@"
    else
        log_info "systemctl non disponible dans cet environnement (${action_desc} ignoré)."
    fi
}

safe_udevadm() {
    local action_desc="$1"
    shift
    if command -v udevadm &>/dev/null; then
        run_sudo_cmd "$action_desc" udevadm "$@"
    else
        log_info "udevadm non disponible dans cet environnement (${action_desc} ignoré)."
    fi
}

backup_system_file() {
    local file_path="$1"
    if [[ -f "$file_path" ]]; then
        local timestamp
        timestamp=$(date +"%Y%m%d_%H%M%S")
        local backup_path="${file_path}.bak_${timestamp}"
        log_warn "Fichier existant détecté : ${file_path}"
        if [[ $DRY_RUN -eq 1 ]]; then
            log_dry "Sauvegarde simulée : ${file_path} -> ${backup_path}"
        else
            if [[ $EUID -eq 0 ]]; then
                cp "$file_path" "$backup_path"
            else
                sudo cp "$file_path" "$backup_path"
            fi
            log_success "Sauvegarde créée : ${backup_path}"
        fi
    fi
}

prompt_confirm() {
    local message="$1"
    local default="${2:-Y}" # Y ou N
    if [[ $NON_INTERACTIVE -eq 1 ]]; then
        if [[ "$default" =~ ^[Yy]$ ]]; then return 0; else return 1; fi
    fi

    local prompt_text
    if [[ "$default" =~ ^[Yy]$ ]]; then
        prompt_text="${C_BOLD}${message}${C_RESET} [O/n] : "
    else
        prompt_text="${C_BOLD}${message}${C_RESET} [o/N] : "
    fi

    while true; do
        read -r -p "$(echo -e "${prompt_text}")" response
        response="${response:-$default}"
        case "$response" in
            [oOyY][uUeE][sS]|[oOyY])
                return 0
                ;;
            [nN][oO]|[nN])
                return 1
                ;;
            *)
                echo -e " ${C_YELLOW}Veuillez répondre par 'o' (oui) ou 'n' (non).${C_RESET}"
                ;;
        esac
    done
}

# ------------------------------------------------------------------------------
# 4. Désinstallation propre
# ------------------------------------------------------------------------------
do_uninstall() {
    print_banner
    log_step "DÉSINSTALLATION" "Suppression des services et configurations système"

    if prompt_confirm "Voulez-vous désactiver et supprimer les services CliOS de /etc/systemd et /etc/udev ?" "N"; then
        local services=("clios.service" "can-usb.service" "can-wake.service" "slcan.service")
        for srv in "${services[@]}"; do
            if [[ -f "${SYSTEMD_DIR}/${srv}" ]]; then
                log_info "Désactivation du service ${srv}..."
                safe_systemctl "Arrêt et désactivation de ${srv}" disable --now "${srv}" 2>/dev/null || true
                run_sudo_cmd "Suppression de ${SYSTEMD_DIR}/${srv}" rm -f "${SYSTEMD_DIR}/${srv}"
                log_success "Service ${srv} supprimé."
            fi
        done

        if [[ -f "${UDEV_RULES_DIR}/99-slcan.rules" ]]; then
            run_sudo_cmd "Suppression de ${UDEV_RULES_DIR}/99-slcan.rules" rm -f "${UDEV_RULES_DIR}/99-slcan.rules"
            log_success "Règles udev supprimées."
        fi

        safe_systemctl "Rechargement de systemd et udev" daemon-reload
        safe_udevadm "Rechargement des règles udev" control --reload-rules 2>/dev/null || true
        log_success "Services système nettoyés."
    else
        log_info "Suppression des services système ignorée."
    fi

    if prompt_confirm "Voulez-vous également supprimer l'environnement Python .venv ?" "N"; then
        if [[ -d "$VENV_DIR" ]]; then
            run_cmd "Suppression du dossier .venv" rm -rf "$VENV_DIR"
            log_success "Dossier .venv supprimé."
        fi
    fi

    echo -e "\n${C_GREEN}${C_BOLD}✓ Désinstallation terminée.${C_RESET}\n"
    exit 0
}

# ------------------------------------------------------------------------------
# 5. Parsing des Arguments
# ------------------------------------------------------------------------------
usage() {
    echo -e "${C_BOLD}Utilisation :${C_RESET} $0 [options]"
    echo ""
    echo -e "${C_BOLD}Options :${C_RESET}"
    echo -e "  ${C_CYAN}-d, --dry-run${C_RESET}         Mode simulation : affiche les actions sans modifier le système"
    echo -e "  ${C_CYAN}-v, --venv-only${C_RESET}       Configure uniquement le .venv Python (pas d'apt, pas de sudo, pas de systemd)"
    echo -e "  ${C_CYAN}-y, --yes${C_RESET}             Mode non-interactif : valide automatiquement les choix recommandés"
    echo -e "  ${C_CYAN}-u, --uninstall${C_RESET}       Désinstalle les services systemd et règles udev de CliOS"
    echo -e "  ${C_CYAN}-h, --help${C_RESET}            Affiche ce message d'aide"
    echo ""
    echo -e "${C_BOLD}Exemples :${C_RESET}"
    echo -e "  $0                  # Installation interactive complète"
    echo -e "  $0 --dry-run        # Prévisualiser sans rien modifier"
    echo -e "  $0 --venv-only      # Préparer uniquement Python / développement"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -d|--dry-run)
            DRY_RUN=1
            shift
            ;;
        -v|--venv-only)
            VENV_ONLY=1
            shift
            ;;
        -y|--yes|--non-interactive)
            NON_INTERACTIVE=1
            shift
            ;;
        -u|--uninstall)
            DO_UNINSTALL=1
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Option inconnue : $1"
            usage
            ;;
    esac
done

if [[ $DO_UNINSTALL -eq 1 ]]; then
    do_uninstall
fi

# ------------------------------------------------------------------------------
# 6. Début de l'installation
# ------------------------------------------------------------------------------
print_banner

if [[ $DRY_RUN -eq 1 ]]; then
    echo -e "${C_MAGENTA}${C_BOLD}▶ MODE SIMULATION ACTIF (--dry-run) : Aucune modification ne sera écrite.${C_RESET}\n"
fi

# ------------------------------------------------------------------------------
# ÉTAPE 1 : Détection de l'Environnement
# ------------------------------------------------------------------------------
log_step "1/6" "Analyse de l'environnement système"

OS_NAME="$(uname -s)"
ARCH_NAME="$(uname -m)"
DISTRO="Inconnue"

if [[ "$OS_NAME" == "Linux" ]]; then
    if [[ -f /etc/os-release ]]; then
        # shellcheck disable=SC1091
        source /etc/os-release
        DISTRO="${PRETTY_NAME:-$NAME}"
    fi
elif [[ "$OS_NAME" == "Darwin" ]]; then
    DISTRO="macOS $(sw_vers -productVersion 2>/dev/null || true)"
fi

log_info "Système d'exploitation : ${C_BOLD}${DISTRO}${C_RESET} (${OS_NAME} ${ARCH_NAME})"
log_info "Utilisateur cible     : ${C_BOLD}${CURRENT_USER}${C_RESET}"
log_info "Répertoire du projet  : ${C_BOLD}${PROJECT_DIR}${C_RESET}"

# Détection de Python 3
find_python_bin() {
    for candidate in python3.13 python3.12 python3.11 python3; do
        if command -v "$candidate" &>/dev/null; then
            echo "$(command -v "$candidate")"
            return 0
        fi
    done
    return 1
}

PYTHON_BIN="$(find_python_bin || true)"

if [[ -n "$PYTHON_BIN" ]]; then
    PY_VER="$($PYTHON_BIN --version 2>&1 | awk '{print $2}')"
    log_info "Binaire Python détecté : ${C_BOLD}${PYTHON_BIN}${C_RESET} (version ${PY_VER})"
    log_success "Environnement identifié avec succès."
else
    if [[ "$OS_NAME" == "Linux" && -f /etc/debian_version && $VENV_ONLY -eq 0 ]]; then
        log_warn "Python 3 n'est pas encore installé. Il sera installé à l'étape 2 (APT)."
    else
        log_error "Python 3 est introuvable. Veuillez installer Python 3.11+."
        exit 1
    fi
fi

# ------------------------------------------------------------------------------
# ÉTAPE 2 : Dépendances Système (APT)
# ------------------------------------------------------------------------------
log_step "2/6" "Dépendances système C, Audio, Affichage Kiosk & CAN"

if [[ $VENV_ONLY -eq 1 ]]; then
    log_info "Option --venv-only active : passage de l'étape des paquets système."
elif [[ "$OS_NAME" == "Linux" && -f /etc/debian_version ]]; then
    log_info "Distribution Debian / Ubuntu / Raspberry Pi OS détectée."
    
    APT_PACKAGES=(
        build-essential
        python3
        python3-dev
        python3-venv
        python3-pip
        portaudio19-dev
        libsndfile1-dev
        liblo-dev
        libjack-jackd2-dev
        libportmidi-dev
        can-utils
        dfu-util
        cage
        seatd
        libgl1
        libegl1
        libxkbcommon0
        libglib2.0-0
        libfontconfig1
        libdbus-1-3
    )

    echo -e "\n Paquets système requis pour l'audio (pyo), le bus CAN et le rendu graphique Qt / Cage (OpenGL/Wayland) :"
    echo -e " ${C_DIM}${APT_PACKAGES[*]}${C_RESET}\n"

    if prompt_confirm "Voulez-vous installer / mettre à jour ces paquets système via apt ?" "Y"; then
        run_sudo_cmd "Mise à jour du catalogue apt" apt-get update -y
        run_sudo_cmd "Installation des paquets système" apt-get install -y "${APT_PACKAGES[@]}"
        log_success "Paquets système installés."
    else
        log_warn "Installation des paquets apt ignorée par l'utilisateur."
    fi

    # Re-détection de Python si absent au départ
    if [[ -z "$PYTHON_BIN" ]]; then
        PYTHON_BIN="$(find_python_bin || true)"
        if [[ -z "$PYTHON_BIN" ]]; then
            if [[ $DRY_RUN -eq 1 ]]; then
                PYTHON_BIN="/usr/bin/python3"
            else
                log_error "Python 3 n'a pas pu être trouvé après l'installation apt."
                exit 1
            fi
        fi
        log_success "Python 3 (${PYTHON_BIN}) opérationnel."
    fi
elif [[ "$OS_NAME" == "Darwin" ]]; then
    log_info "macOS détecté : les paquets apt et services systemd ne s'appliquent pas."
    log_info "Les dépendances Python seront installées pour le mode simulation/développement."
else
    log_warn "Système non-Debian. Assurez-vous d'avoir les headers C pour portaudio, liblo, can-utils et cage."
fi

# ------------------------------------------------------------------------------
# ÉTAPE 3 : Environnement Virtuel Python (.venv) & Compilation Pyo
# ------------------------------------------------------------------------------
log_step "3/6" "Environnement Virtuel Python (.venv) & Dépendances"

if [[ -d "$VENV_DIR" ]]; then
    log_info "Un environnement virtuel existe déjà dans : ${VENV_DIR}"
    if prompt_confirm "Souhaitez-vous le recréer à neuf (recommandé en cas de problème) ?" "N"; then
        run_cmd "Suppression de l'ancien .venv" rm -rf "$VENV_DIR"
        run_cmd "Création d'un nouvel environnement .venv" "$PYTHON_BIN" -m venv "$VENV_DIR"
        log_success "Nouvel environnement virtuel créé."
    else
        log_info "Conservation du .venv existant."
    fi
else
    run_cmd "Création de l'environnement virtuel .venv" "$PYTHON_BIN" -m venv "$VENV_DIR"
    log_success "Environnement virtuel créé dans ${VENV_DIR}."
fi

VENV_PIP="${VENV_DIR}/bin/pip"
VENV_PYTHON="${VENV_DIR}/bin/python3"

# Mise à niveau des outils de packaging
run_cmd "Mise à jour de pip, setuptools et wheel" "$VENV_PIP" install --upgrade pip setuptools wheel

# Compilation sécurisée de pyo
echo -e "\n${C_BOLD}Installation de la bibliothèque DSP Audio (pyo)...${C_RESET}"
log_info "Application des drapeaux GCC adaptés pour Python 3.13+ (-Wno-incompatible-pointer-types)..."

if [[ $DRY_RUN -eq 1 ]]; then
    log_dry "CFLAGS=\"-Wno-incompatible-pointer-types -Wno-error\" $VENV_PIP install --no-build-isolation pyo~=1.0.5"
    log_dry "$VENV_PIP install -r ${PROJECT_DIR}/requirements.txt"
else
    # Tentative d'installation de pyo avec CFLAGS
    if CFLAGS="-Wno-incompatible-pointer-types -Wno-error" "$VENV_PIP" install --no-build-isolation "pyo~=1.0.5"; then
        log_success "Compilation et installation de pyo réussies."
    else
        log_warn "Échec de l'installation standard de pyo. Tentative de secours sans OSC..."
        if "$VENV_PIP" install --no-binary :all: --config-settings="--build-option=--no-osc" "pyo~=1.0.5"; then
            log_success "Installation de pyo réussie (mode fallback sans OSC)."
        else
            log_warn "Impossible de compiler pyo. Le reste des dépendances va tout de même être installé."
        fi
    fi

    # Installation des autres dépendances depuis requirements.txt
    log_info "Installation des dépendances depuis requirements.txt..."
    "$VENV_PIP" install -r "${PROJECT_DIR}/requirements.txt"
    log_success "Toutes les dépendances Python sont installées."

    # Validation rapide des imports critiques
    log_info "Validation des modules Python critiques..."
    if "$VENV_PYTHON" -c "import PySide6; print(f'PySide6 version: {PySide6.__version__}')" &>/dev/null; then
        log_success "PySide6 opérationnel."
    else
        log_warn "PySide6 n'a pas pu être validé lors du test rapide."
    fi

    if "$VENV_PYTHON" -c "import pyo; print(f'pyo version: {pyo.PYO_VERSION}')" &>/dev/null; then
        log_success "pyo audio opérationnel."
    else
        log_warn "pyo audio n'est pas actif (les fonctionnalités sonores moteur seront désactivées)."
    fi
fi

# ------------------------------------------------------------------------------
# ÉTAPE 4 : Configuration Matérielle CAN & Udev
# ------------------------------------------------------------------------------
log_step "4/6" "Configuration du Matériel CAN & Règles Udev"

if [[ $VENV_ONLY -eq 1 || "$OS_NAME" != "Linux" ]]; then
    log_info "Étape CAN ignorée (mode venv-only ou système non-Linux)."
else
    echo -e "Sélectionnez votre type de modem CAN pour configurer les services système :"
    echo -e "  ${C_CYAN}1)${C_RESET} ${C_BOLD}Modem natif Candlelight / CAN-USB${C_RESET} (Active can-usb.service)"
    echo -e "  ${C_CYAN}2)${C_RESET} ${C_BOLD}Modem SLCAN USB (/dev/ttyACM0)${C_RESET}   (Active slcan.service + règle udev)"
    echo -e "  ${C_CYAN}3)${C_RESET} ${C_BOLD}Réveil DFU STM32 seul${C_RESET}            (Active can-wake.service)"
    echo -e "  ${C_CYAN}4)${C_RESET} ${C_BOLD}Natif + Réveil DFU STM32${C_RESET}         (can-usb.service + can-wake.service)"
    echo -e "  ${C_CYAN}5)${C_RESET} ${C_BOLD}Ne rien modifier / Mode Simulation${C_RESET} [Recommandé si déjà configuré]"

    CHOICE="5"
    if [[ $NON_INTERACTIVE -eq 0 ]]; then
        read -r -p "$(echo -e "\n${C_BOLD}Votre choix [1-5] (défaut: 5) : ${C_RESET}")" input_choice
        CHOICE="${input_choice:-5}"
    fi

    run_sudo_cmd "Création des répertoires système" mkdir -p "${SYSTEMD_DIR}" "${UDEV_RULES_DIR}"

    case "$CHOICE" in
        1)
            log_info "Configuration du modem natif Candlelight (can-usb.service)..."
            backup_system_file "${SYSTEMD_DIR}/can-usb.service"
            run_sudo_cmd "Copie de can-usb.service" cp "${INSTALL_ETC_DIR}/systemd/system/can-usb.service" "${SYSTEMD_DIR}/"
            safe_systemctl "Rechargement daemon systemd" daemon-reload
            safe_systemctl "Activation de can-usb.service" enable can-usb.service
            log_success "Service can-usb configuré et activé."
            ;;
        2)
            log_info "Configuration du modem SLCAN (/dev/ttyACM0)..."
            backup_system_file "${SYSTEMD_DIR}/slcan.service"
            backup_system_file "${UDEV_RULES_DIR}/99-slcan.rules"
            run_sudo_cmd "Copie de slcan.service" cp "${INSTALL_ETC_DIR}/systemd/system/slcan.service" "${SYSTEMD_DIR}/"
            run_sudo_cmd "Copie de 99-slcan.rules" cp "${INSTALL_ETC_DIR}/udev/rules.d/99-slcan.rules" "${UDEV_RULES_DIR}/"
            safe_systemctl "Rechargement de systemd" daemon-reload
            safe_udevadm "Rechargement des règles udev" control --reload-rules
            safe_udevadm "Application des règles udev" trigger
            safe_systemctl "Activation de slcan.service" enable slcan.service
            log_success "Service SLCAN et règles udev configurés."
            ;;
        3)
            log_info "Configuration du réveil DFU STM32..."
            backup_system_file "${SYSTEMD_DIR}/can-wake.service"
            run_sudo_cmd "Copie de can-wake.service" cp "${INSTALL_ETC_DIR}/systemd/system/can-wake.service" "${SYSTEMD_DIR}/"
            safe_systemctl "Rechargement de systemd" daemon-reload
            safe_systemctl "Activation de can-wake.service" enable can-wake.service
            log_success "Service can-wake configuré."
            ;;
        4)
            log_info "Configuration Natif + Réveil DFU..."
            backup_system_file "${SYSTEMD_DIR}/can-usb.service"
            backup_system_file "${SYSTEMD_DIR}/can-wake.service"
            run_sudo_cmd "Copie de can-usb.service" cp "${INSTALL_ETC_DIR}/systemd/system/can-usb.service" "${SYSTEMD_DIR}/"
            run_sudo_cmd "Copie de can-wake.service" cp "${INSTALL_ETC_DIR}/systemd/system/can-wake.service" "${SYSTEMD_DIR}/"
            safe_systemctl "Rechargement de systemd" daemon-reload
            safe_systemctl "Activation de can-usb.service" enable can-usb.service
            safe_systemctl "Activation de can-wake.service" enable can-wake.service
            log_success "Services can-usb et can-wake configurés."
            ;;
        *)
            log_info "Aucune modification apportée aux services CAN matériels."
            ;;
    esac
fi

# ------------------------------------------------------------------------------
# ÉTAPE 5 : Démarrage Automatique Kiosk (Wayland / Cage clios.service)
# ------------------------------------------------------------------------------
log_step "5/6" "Démarrage Automatique au Boot (Kiosk Standalone via Cage)"

if [[ $VENV_ONLY -eq 1 || "$OS_NAME" != "Linux" ]]; then
    log_info "Étape Autostart Kiosk ignorée (mode venv-only ou système non-Linux)."
else
    echo -e "CliOS peut se lancer automatiquement en plein écran au démarrage via le compositeur Wayland ${C_BOLD}Cage${C_RESET} (sans nécessiter de bureau)."
    if prompt_confirm "Voulez-vous installer le service de démarrage Kiosk (clios.service) ?" "N"; then
        
        USER_UID="$(id -u "$CURRENT_USER" 2>/dev/null || echo 1000)"
        TMP_SERVICE_FILE="/tmp/clios.service"
        cat << EOF > "$TMP_SERVICE_FILE"
[Unit]
Description=CliOS Automotive Dashboard (Wayland Kiosk via Cage)
After=graphical.target sound.target can0.service systemd-user-sessions.service
Wants=can0.service

[Service]
Type=simple
User=${CURRENT_USER}
PAMName=login
WorkingDirectory=${PROJECT_DIR}
Environment=XDG_RUNTIME_DIR=/run/user/${USER_UID}
Environment=QT_QPA_PLATFORM=wayland
ExecStart=/usr/bin/cage -s -- ${PROJECT_DIR}/.venv/bin/python3 -u ${PROJECT_DIR}/main.py --ui gui
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical.target
EOF

        run_sudo_cmd "Création des répertoires système" mkdir -p "${SYSTEMD_DIR}"
        backup_system_file "${SYSTEMD_DIR}/clios.service"

        if [[ $DRY_RUN -eq 1 ]]; then
            log_dry "Contenu du service généré (${TMP_SERVICE_FILE}) :"
            cat "$TMP_SERVICE_FILE"
        else
            run_sudo_cmd "Installation de clios.service" cp "$TMP_SERVICE_FILE" "${SYSTEMD_DIR}/clios.service"
            run_sudo_cmd "Permission sur clios.service" chmod 644 "${SYSTEMD_DIR}/clios.service"
            safe_systemctl "Rechargement daemon systemd" daemon-reload
            rm -f "$TMP_SERVICE_FILE"

            if prompt_confirm "Activer le lancement automatique de CliOS à chaque démarrage maintenant ?" "Y"; then
                safe_systemctl "Activation de clios.service" enable clios.service
                log_success "clios.service configuré pour le démarrage du système."
            else
                log_info "clios.service installé mais non activé (utilisez 'sudo systemctl enable clios.service' plus tard)."
            fi
        fi
        log_success "Configuration du service Kiosk terminée."
    else
        log_info "Installation du service Kiosk ignorée."
    fi
fi

# ------------------------------------------------------------------------------
# ÉTAPE 6 : Optimisations Fast-Boot pour Raspberry Pi
# ------------------------------------------------------------------------------
log_step "6/6" "Optimisations Fast-Boot (Démarrage Rapide)"

if [[ $VENV_ONLY -eq 1 || "$OS_NAME" != "Linux" ]]; then
    log_info "Étape Fast-Boot ignorée (mode venv-only ou système non-Linux)."
else
    echo -e "Accélération du temps de démarrage (gain estimé : ~10 à 12 secondes) :"
    echo -e "Désactivation des services de fond lents (NetworkManager-wait-online, timers apt, swap)."
    if prompt_confirm "Souhaitez-vous désactiver ces services lents au démarrage ?" "N"; then
        SLOW_SERVICES=(
            NetworkManager-wait-online.service
            apt-daily.timer
            apt-daily-upgrade.timer
            man-db.timer
            dphys-swapfile.service
            rpi-eeprom-update.service
        )
        for srv in "${SLOW_SERVICES[@]}"; do
            safe_systemctl "Désactivation de ${srv}" disable "${srv}" 2>/dev/null || true
        done
        log_success "Services lents désactivés avec succès."
        echo -e "\n ${C_CYAN}ℹ${C_RESET} ${C_BOLD}Astuce Matérielle :${C_RESET} Pour optimiser également l'EEPROM et le fichier /boot/firmware/config.txt,"
        echo -e "   consultez le guide détaillé : ${C_CYAN}installation/guide_optimisation_boot_rpi5.md${C_RESET}"
    else
        log_info "Optimisations Fast-Boot ignorées."
    fi
fi

# ------------------------------------------------------------------------------
# Rendu Final & Instructions d'utilisation
# ------------------------------------------------------------------------------
echo -e "\n${C_GREEN}${C_BOLD}══════════════════════════════════════════════════════════════════${C_RESET}"
echo -e "${C_GREEN}${C_BOLD}  ✓ INSTALLATION DE CliOS TERMINÉE AVEC SUCCÈS !${C_RESET}"
echo -e "${C_GREEN}${C_BOLD}══════════════════════════════════════════════════════════════════${C_RESET}\n"

echo -e "${C_BOLD}Vous pouvez maintenant démarrer CliOS facilement :${C_RESET}\n"
echo -e "  ${C_CYAN}./clios${C_RESET}                 # Lancement standard (Dashboard GUI sur véhicule)"
echo -e "  ${C_CYAN}./clios --mock${C_RESET}          # Lancement en mode Simulation (sans matériel)"
echo -e "  ${C_CYAN}./clios --ui cli --mock${C_RESET} # Lancement en mode Terminal interactif"
echo -e "  ${C_CYAN}./clios --help${C_RESET}          # Consulter toutes les options disponibles"
echo ""
echo -e "${C_DIM}Pour gérer le service Kiosk :${C_RESET}"
echo -e "  ${C_DIM}sudo systemctl start clios.service   # Démarrer le service${C_RESET}"
echo -e "  ${C_DIM}sudo systemctl status clios.service  # Voir l'état du service${C_RESET}"
echo -e "  ${C_DIM}journalctl -u clios.service -f       # Voir les logs en direct${C_RESET}\n"
