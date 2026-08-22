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

# Si un venv est actuellement actif dans le terminal appelant, on le désactive pour ce sous-shell
if [[ -n "$VIRTUAL_ENV" ]]; then
    PATH="${PATH//${VIRTUAL_ENV}\/bin:/}"
    unset VIRTUAL_ENV
fi

SYSTEMD_DIR="/etc/systemd/system"
UDEV_RULES_DIR="/etc/udev/rules.d"
LOCAL_LIBEXEC_DIR="/usr/local/libexec"
POLKIT_RULES_DIR="/etc/polkit-1/rules.d"
SUDOERS_DIR="/etc/sudoers.d"

# Flags d'exécution
DRY_RUN=0
VENV_ONLY=0
NON_INTERACTIVE=0
DO_UNINSTALL=0
KIOSK_INSTALLED=0
KIOSK_AUTOSTART_ENABLED=0

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

run_target_cmd() {
    local cmd_desc="$1"
    shift
    if [[ $DRY_RUN -eq 1 ]]; then
        log_dry "Commande utilisateur simulée : $*"
        return 0
    fi
    log_info "$cmd_desc"
    if [[ $EUID -eq 0 && "$(id -un)" != "$CURRENT_USER" ]]; then
        runuser -u "$CURRENT_USER" -- "$@"
    else
        "$@"
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

install_release_tree() {
    local release_dir="$1"
    local release_parent staging_dir previous_dir source_archive
    local source_device target_device

    release_parent="$(dirname "$release_dir")"
    staging_dir="${release_dir}.installing"
    previous_dir="${release_dir}.previous-install"

    source_device="$(stat -c %d "$VENV_DIR")"
    target_device="$(stat -c %d "$release_parent")"
    if [[ "$source_device" != "$target_device" ]]; then
        log_error "Le projet et ${release_parent} doivent être sur le même système de fichiers pour transférer le .venv sans copie."
        log_error "Copiez d'abord CliOS dans /home/${CURRENT_USER}, puis relancez install.sh."
        return 1
    fi

    source_archive="$(mktemp /tmp/clios-release-tree.XXXXXX.tar)"
    if ! tar \
        --exclude='./.git' \
        --exclude='./.venv' \
        --exclude='./__pycache__' \
        --exclude='*/__pycache__' \
        --exclude='./.idea' \
        --exclude='./.pytest_cache' \
        --exclude='./.portfolio' \
        --exclude='./dist' \
        --exclude='./wheelhouses' \
        --exclude='.DS_Store' \
        -C "$PROJECT_DIR" -cf "$source_archive" .; then
        rm -f "$source_archive"
        log_error "Impossible de préparer les fichiers de la release."
        return 1
    fi

    run_sudo_cmd "Nettoyage du staging de release" rm -rf "$staging_dir" "$previous_dir"
    run_sudo_cmd "Création du staging de release" mkdir -p "$staging_dir"
    if ! run_sudo_cmd "Installation du code de la release" tar -C "$staging_dir" -xf "$source_archive"; then
        rm -f "$source_archive"
        run_sudo_cmd "Nettoyage du staging incomplet" rm -rf "$staging_dir"
        return 1
    fi
    rm -f "$source_archive"

    # /home et /opt partagent normalement la partition racine. Un renommage ne
    # relit pas les gros fichiers Qt et conserve un environnement isolé par release.
    if ! run_sudo_cmd "Transfert de l'environnement Python vers la release" mv "$VENV_DIR" "${staging_dir}/.venv"; then
        run_sudo_cmd "Nettoyage du staging incomplet" rm -rf "$staging_dir"
        return 1
    fi

    # Actualise pyvenv.cfg et les lanceurs standards après le changement de chemin.
    if ! run_sudo_cmd "Actualisation du chemin de l'environnement Python" \
        "$PYTHON_BIN" -m venv --upgrade "${staging_dir}/.venv"; then
        run_sudo_cmd "Restauration de l'environnement Python source" mv "${staging_dir}/.venv" "$VENV_DIR"
        run_sudo_cmd "Nettoyage du staging incomplet" rm -rf "$staging_dir"
        return 1
    fi

    if ! run_target_cmd "Self-check Python de la release" \
        "${staging_dir}/.venv/bin/python3" -c "import PySide6, numpy, psutil, can, serial, pyudev"; then
        run_sudo_cmd "Restauration de l'environnement Python source" mv "${staging_dir}/.venv" "$VENV_DIR"
        run_sudo_cmd "Nettoyage du staging incomplet" rm -rf "$staging_dir"
        return 1
    fi
    if [[ -f "${staging_dir}/tools/qml_smoke.py" ]] && ! run_target_cmd "Self-check QML de la release" \
        env QT_QPA_PLATFORM=offscreen "${staging_dir}/.venv/bin/python3" "${staging_dir}/tools/qml_smoke.py"; then
        run_sudo_cmd "Restauration de l'environnement Python source" mv "${staging_dir}/.venv" "$VENV_DIR"
        run_sudo_cmd "Nettoyage du staging incomplet" rm -rf "$staging_dir"
        return 1
    fi

    if [[ -e "$release_dir" || -L "$release_dir" ]]; then
        run_sudo_cmd "Mise à l'écart de la release incomplète ou précédente" mv "$release_dir" "$previous_dir"
    fi
    if ! run_sudo_cmd "Validation atomique de la release" mv "$staging_dir" "$release_dir"; then
        if [[ -e "$previous_dir" || -L "$previous_dir" ]]; then
            run_sudo_cmd "Restauration de la release précédente" mv "$previous_dir" "$release_dir"
        fi
        return 1
    fi
    run_sudo_cmd "Nettoyage de l'installation précédente" rm -rf "$previous_dir" \
        || log_warn "L'ancien staging ${previous_dir} devra être supprimé manuellement."
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
        safe_systemctl "Arrêt des montages USB CliOS" stop "clios-usb-mount@*.service" 2>/dev/null || true
        local services=("clios.service" "clios-updater.service" "clios-updater.socket" "clios-usb-mount@.service" "can-usb.service" "can-wake.service" "slcan.service")
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

        if [[ -f "${UDEV_RULES_DIR}/90-clios-usb-storage.rules" ]]; then
            run_sudo_cmd "Suppression de ${UDEV_RULES_DIR}/90-clios-usb-storage.rules" rm -f "${UDEV_RULES_DIR}/90-clios-usb-storage.rules"
            log_success "Règle de stockage USB supprimée."
        fi

        if [[ -f "${LOCAL_LIBEXEC_DIR}/clios-usb-mount" ]]; then
            run_sudo_cmd "Suppression du helper de montage USB" rm -f "${LOCAL_LIBEXEC_DIR}/clios-usb-mount"
        fi

        if [[ -f "${SUDOERS_DIR}/clios-overlayfs" ]]; then
            run_sudo_cmd "Suppression de l'autorisation OverlayFS" rm -f "${SUDOERS_DIR}/clios-overlayfs"
        fi

        if [[ -f "${POLKIT_RULES_DIR}/49-clios-power.rules" ]]; then
            run_sudo_cmd "Suppression de la règle Polkit CliOS" rm -f "${POLKIT_RULES_DIR}/49-clios-power.rules"
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
RELEASE_TARGET=""
EXPECTED_PYTHON_MINOR=""

if [[ "$OS_NAME" == "Linux" ]]; then
    if [[ -f /etc/os-release ]]; then
        # shellcheck disable=SC1091
        source /etc/os-release
        DISTRO="${PRETTY_NAME:-$NAME}"
    fi
elif [[ "$OS_NAME" == "Darwin" ]]; then
    DISTRO="macOS $(sw_vers -productVersion 2>/dev/null || true)"
fi

if [[ "$OS_NAME" == "Linux" && "$ARCH_NAME" == "aarch64" && -f /etc/debian_version ]]; then
    case "${VERSION_CODENAME:-}" in
        bookworm)
            RELEASE_TARGET="bookworm-arm64"
            EXPECTED_PYTHON_MINOR="3.11"
            ;;
        trixie)
            RELEASE_TARGET="trixie-arm64"
            EXPECTED_PYTHON_MINOR="3.13"
            ;;
        *)
            log_error "Version Debian ARM64 non prise en charge : ${VERSION_CODENAME:-inconnue}. Utilisez Bookworm ou Trixie."
            exit 1
            ;;
    esac
fi

log_info "Système d'exploitation : ${C_BOLD}${DISTRO}${C_RESET} (${OS_NAME} ${ARCH_NAME})"
log_info "Utilisateur cible     : ${C_BOLD}${CURRENT_USER}${C_RESET}"
log_info "Répertoire du projet  : ${C_BOLD}${PROJECT_DIR}${C_RESET}"

# Détection de Python 3
find_python_bin() {
    local candidates=()
    if [[ -n "$EXPECTED_PYTHON_MINOR" ]]; then
        candidates+=("/usr/bin/python${EXPECTED_PYTHON_MINOR}" "python${EXPECTED_PYTHON_MINOR}")
    fi
    candidates+=(
        /opt/homebrew/bin/python3.13
        /opt/homebrew/bin/python3.12
        /opt/homebrew/bin/python3.11
        /opt/homebrew/bin/python3
        /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13
        /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12
        /Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11
        /usr/local/bin/python3.13
        /usr/local/bin/python3.12
        /usr/local/bin/python3.11
        /usr/local/bin/python3
        /usr/bin/python3.13
        /usr/bin/python3.12
        /usr/bin/python3.11
        /usr/bin/python3
        python3.13
        python3.12
        python3.11
        python3
    )
    for candidate in "${candidates[@]}"; do
        if command -v "$candidate" &>/dev/null; then
            local resolved
            resolved="$(command -v "$candidate")"
            if [[ "$resolved" != *"${PROJECT_DIR}/.venv"* ]]; then
                echo "$resolved"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_BIN="$(find_python_bin || true)"

if [[ -n "$PYTHON_BIN" ]]; then
    PY_VER="$($PYTHON_BIN --version 2>&1 | awk '{print $2}')"
    PY_MINOR="$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    if [[ -n "$EXPECTED_PYTHON_MINOR" && "$PY_MINOR" != "$EXPECTED_PYTHON_MINOR" ]]; then
        log_error "${RELEASE_TARGET} exige Python ${EXPECTED_PYTHON_MINOR}, mais ${PYTHON_BIN} fournit ${PY_MINOR}."
        exit 1
    fi
    log_info "Binaire Python détecté : ${C_BOLD}${PYTHON_BIN}${C_RESET} (version ${PY_VER})"
    if [[ -n "$RELEASE_TARGET" ]]; then
        log_info "Cible de release      : ${C_BOLD}${RELEASE_TARGET}${C_RESET}"
    fi
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
        exfatprogs
        ntfs-3g
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

VENV_PYTHON="${VENV_DIR}/bin/python3"
BUNDLED_LOCK="${PROJECT_DIR}/requirements-${RELEASE_TARGET}.lock"
BUNDLED_WHEELS="${PROJECT_DIR}/wheels"

if [[ -n "$RELEASE_TARGET" && -f "$BUNDLED_LOCK" && -d "$BUNDLED_WHEELS" ]] && compgen -G "${BUNDLED_WHEELS}/*.whl" >/dev/null; then
    log_info "Installation hors ligne depuis le wheelhouse ${RELEASE_TARGET}."
    if [[ $DRY_RUN -eq 1 ]]; then
        log_dry "$VENV_PYTHON -m pip install --no-index --no-deps ${BUNDLED_WHEELS}/*.whl"
        log_dry "$VENV_PYTHON -m pip install --no-index --require-hashes -r $BUNDLED_LOCK"
    else
        "$VENV_PYTHON" -m pip install --no-index --no-deps "${BUNDLED_WHEELS}"/*.whl
        "$VENV_PYTHON" -m pip install --no-index --require-hashes -r "$BUNDLED_LOCK"
        "$VENV_PYTHON" -m pip check
        log_success "Wheelhouse ${RELEASE_TARGET} installé et vérifié."
    fi
else
    # Le checkout de développement conserve le chemin PyPI historique. Les
    # archives publiées passent toujours par le wheelhouse ci-dessus.
    run_cmd "Mise à jour de pip, setuptools et wheel" "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel
    echo -e "\n${C_BOLD}Installation de la bibliothèque DSP Audio (pyo)...${C_RESET}"
    BREW_CFLAGS=""
    if [[ "$OS_NAME" == "Darwin" ]]; then
        if [[ -d "/opt/homebrew/include" ]]; then
            BREW_CFLAGS="-I/opt/homebrew/include -L/opt/homebrew/lib"
        elif [[ -d "/usr/local/include" ]]; then
            BREW_CFLAGS="-I/usr/local/include -L/usr/local/lib"
        fi
    fi
    PYO_CFLAGS="${BREW_CFLAGS} -Wno-incompatible-pointer-types -Wno-error"

    if [[ $DRY_RUN -eq 1 ]]; then
        log_dry "CFLAGS=\"${PYO_CFLAGS}\" $VENV_PYTHON -m pip install --no-build-isolation pyo~=1.0.5"
        log_dry "$VENV_PYTHON -m pip install -r ${PROJECT_DIR}/requirements.txt"
    else
        PYO_INSTALLED=0
        if CFLAGS="${PYO_CFLAGS}" "$VENV_PYTHON" -m pip install --no-build-isolation "pyo~=1.0.5" 2>/dev/null; then
            log_success "Compilation et installation de pyo réussies."
            PYO_INSTALLED=1
        else
            log_warn "Échec de la compilation standard de pyo. Tentative sans OSC..."
            if CFLAGS="${PYO_CFLAGS}" "$VENV_PYTHON" -m pip install --no-binary :all: --config-settings="--build-option=--no-osc" "pyo~=1.0.5" 2>/dev/null; then
                log_success "Installation de pyo réussie (mode fallback sans OSC)."
                PYO_INSTALLED=1
            else
                log_warn "pyo n'a pas pu être compilé (en-têtes C audio absents). Les fonctionnalités de son moteur seront inactives."
            fi
        fi
        log_info "Installation des dépendances depuis requirements.txt..."
        if [[ $PYO_INSTALLED -eq 1 ]]; then
            "$VENV_PYTHON" -m pip install -r "${PROJECT_DIR}/requirements.txt"
        else
            grep -v '^pyo' "${PROJECT_DIR}/requirements.txt" | "$VENV_PYTHON" -m pip install -r /dev/stdin
        fi
        log_success "Dépendances Python installées."
    fi
fi

if [[ $DRY_RUN -eq 0 ]]; then
    log_info "Validation des modules Python critiques..."
    if "$VENV_PYTHON" -c "import PySide6; print(f'PySide6 version: {PySide6.__version__}')" &>/dev/null; then
        log_success "PySide6 opérationnel."
    else
        log_warn "PySide6 n'a pas pu être validé lors du test rapide."
    fi

    if "$VENV_PYTHON" -c "import pyo; print(f'pyo version: {pyo.PYO_VERSION}')" &>/dev/null; then
        log_success "pyo audio opérationnel."
    else
        log_info "pyo audio désactivé (normal en simulation sur Mac sans headers portaudio)."
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
        KIOSK_INSTALLED=1
        if ! getent group clios >/dev/null 2>&1; then
            run_sudo_cmd "Création du groupe système clios" groupadd --system clios
        fi
        if ! id clios >/dev/null 2>&1; then
            run_sudo_cmd "Création de l'utilisateur de self-check clios" useradd --system --gid clios --home-dir /var/lib/clios --shell /usr/sbin/nologin clios
        fi
        run_sudo_cmd "Accès de ${CURRENT_USER} au socket updater" usermod -a -G clios "${CURRENT_USER}"
        RELEASE_VERSION="$(tr -d '[:space:]' < "${PROJECT_DIR}/VERSION")"
        RELEASE_DIR="/opt/clios/releases/${RELEASE_VERSION}"
        run_sudo_cmd "Création des répertoires de release" mkdir -p "$(dirname "$RELEASE_DIR")" /var/lib/clios /run/clios
        if [[ $DRY_RUN -eq 1 ]]; then
            log_dry "Staging de ${PROJECT_DIR} sans .venv, transfert du .venv, puis lien /opt/clios/current"
        else
            safe_systemctl "Arrêt de CliOS avant remplacement de la release" stop clios.service 2>/dev/null || true
            install_release_tree "$RELEASE_DIR"
            run_sudo_cmd "Activation initiale de la release" ln -sfn "${RELEASE_DIR}" /opt/clios/current
            for legacy_dir in dash_save trips trips_mock logs; do
                if [[ -d "${PROJECT_DIR}/data/${legacy_dir}" ]]; then
                    run_sudo_cmd "Préparation du stockage ${legacy_dir}" mkdir -p "/var/lib/clios/${legacy_dir}"
                    run_sudo_cmd "Migration non destructive de ${legacy_dir}" cp -an "${PROJECT_DIR}/data/${legacy_dir}/." "/var/lib/clios/${legacy_dir}/"
                fi
            done
        fi

        USER_UID="$(id -u "$CURRENT_USER" 2>/dev/null || echo 1000)"
        TMP_SERVICE_FILE="/tmp/clios.service"
        python3 "${PROJECT_DIR}/tools/generate_systemd.py" \
            --user "${CURRENT_USER}" --uid "${USER_UID}" --output "${TMP_SERVICE_FILE}"

        run_sudo_cmd "Création des répertoires système" mkdir -p "${SYSTEMD_DIR}" "${UDEV_RULES_DIR}" "${LOCAL_LIBEXEC_DIR}" "${SUDOERS_DIR}" /etc/clios /var/lib/clios /run/clios /media/clios
        run_sudo_cmd "Création du répertoire Polkit" mkdir -p "${POLKIT_RULES_DIR}"
        run_sudo_cmd "Droits des données updater" chown root:clios /var/lib/clios /run/clios
        run_sudo_cmd "Permissions des données updater" chmod 0770 /var/lib/clios /run/clios
        backup_system_file "${SYSTEMD_DIR}/clios.service"
        backup_system_file "${SYSTEMD_DIR}/clios-updater.service"
        backup_system_file "${SYSTEMD_DIR}/clios-updater.socket"
        backup_system_file "${SYSTEMD_DIR}/clios-usb-mount@.service"
        backup_system_file "${UDEV_RULES_DIR}/90-clios-usb-storage.rules"
        backup_system_file "${LOCAL_LIBEXEC_DIR}/clios-usb-mount"
        backup_system_file "/etc/clios/updater.json"
        backup_system_file "/etc/clios/release-keys.json"
        backup_system_file "${POLKIT_RULES_DIR}/49-clios-power.rules"
        backup_system_file "${SUDOERS_DIR}/clios-overlayfs"

        if [[ $DRY_RUN -eq 1 ]]; then
            log_dry "Contenu du service généré (${TMP_SERVICE_FILE}) :"
            cat "$TMP_SERVICE_FILE"
        else
            run_sudo_cmd "Installation de clios.service" cp "$TMP_SERVICE_FILE" "${SYSTEMD_DIR}/clios.service"
            run_sudo_cmd "Permission sur clios.service" chmod 644 "${SYSTEMD_DIR}/clios.service"
            run_sudo_cmd "Installation de clios-updater.service" cp "${INSTALL_ETC_DIR}/systemd/system/clios-updater.service" "${SYSTEMD_DIR}/clios-updater.service"
            run_sudo_cmd "Installation de clios-updater.socket" cp "${INSTALL_ETC_DIR}/systemd/system/clios-updater.socket" "${SYSTEMD_DIR}/clios-updater.socket"
            run_sudo_cmd "Installation du service de montage USB" cp "${INSTALL_ETC_DIR}/systemd/system/clios-usb-mount@.service" "${SYSTEMD_DIR}/clios-usb-mount@.service"
            run_sudo_cmd "Installation de la règle de stockage USB" cp "${INSTALL_ETC_DIR}/udev/rules.d/90-clios-usb-storage.rules" "${UDEV_RULES_DIR}/90-clios-usb-storage.rules"
            run_sudo_cmd "Installation du helper de montage USB" cp "${PROJECT_DIR}/installation/usr/local/libexec/clios-usb-mount" "${LOCAL_LIBEXEC_DIR}/clios-usb-mount"
            run_sudo_cmd "Permissions du helper de montage USB" chmod 0755 "${LOCAL_LIBEXEC_DIR}/clios-usb-mount"
            run_sudo_cmd "Installation de la source de confiance updater" cp "${INSTALL_ETC_DIR}/clios/updater.json" /etc/clios/updater.json
            run_sudo_cmd "Droits de la source de confiance updater" chown root:root /etc/clios/updater.json
            run_sudo_cmd "Permissions de la source de confiance updater" chmod 0644 /etc/clios/updater.json
            run_sudo_cmd "Installation du trousseau de publication" cp "${INSTALL_ETC_DIR}/clios/release-keys.json" /etc/clios/release-keys.json
            run_sudo_cmd "Droits du trousseau de publication" chown root:root /etc/clios/release-keys.json
            run_sudo_cmd "Permissions du trousseau de publication" chmod 0644 /etc/clios/release-keys.json
            sed "s/@CLIOS_USER@/${CURRENT_USER}/g" \
                "${INSTALL_ETC_DIR}/polkit-1/rules.d/49-clios-power.rules.in" > /tmp/49-clios-power.rules
            run_sudo_cmd "Installation de la règle Polkit CliOS" cp /tmp/49-clios-power.rules "${POLKIT_RULES_DIR}/49-clios-power.rules"
            run_sudo_cmd "Permissions de la règle Polkit CliOS" chmod 0644 "${POLKIT_RULES_DIR}/49-clios-power.rules"
            rm -f /tmp/49-clios-power.rules
            sed "s/@CLIOS_USER@/${CURRENT_USER}/g" \
                "${INSTALL_ETC_DIR}/sudoers.d/clios-overlayfs.in" > /tmp/clios-overlayfs.sudoers
            run_sudo_cmd "Validation de l'autorisation OverlayFS" visudo -cf /tmp/clios-overlayfs.sudoers
            run_sudo_cmd "Installation de l'autorisation OverlayFS" cp /tmp/clios-overlayfs.sudoers "${SUDOERS_DIR}/clios-overlayfs"
            run_sudo_cmd "Permissions de l'autorisation OverlayFS" chmod 0440 "${SUDOERS_DIR}/clios-overlayfs"
            rm -f /tmp/clios-overlayfs.sudoers
            safe_systemctl "Rechargement daemon systemd" daemon-reload
            safe_udevadm "Rechargement des règles de stockage USB" control --reload-rules
            safe_udevadm "Détection des stockages USB déjà branchés" trigger --subsystem-match=block --action=add
            safe_systemctl "Activation du socket updater" enable --now clios-updater.socket
            rm -f "$TMP_SERVICE_FILE"

            if prompt_confirm "Activer le lancement automatique de CliOS à chaque démarrage maintenant ?" "Y"; then
                safe_systemctl "Activation de clios.service" enable clios.service
                KIOSK_AUTOSTART_ENABLED=1
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

if [[ $KIOSK_INSTALLED -eq 1 ]]; then
    echo -e "${C_BOLD}CliOS est installé dans /opt/clios/current.${C_RESET}\n"
    echo -e "  ${C_CYAN}sudo systemctl start clios.service${C_RESET}    # Démarrer le cockpit maintenant"
    echo -e "  ${C_CYAN}sudo systemctl status clios.service${C_RESET}   # Vérifier son état"
    echo -e "  ${C_CYAN}journalctl -u clios.service -f${C_RESET}        # Suivre les logs"
    echo -e "  ${C_DIM}./clios --help redirige automatiquement vers /opt/clios/current.${C_RESET}\n"
    if [[ $KIOSK_AUTOSTART_ENABLED -eq 1 ]] && prompt_confirm "Voulez-vous démarrer CliOS maintenant ?" "Y"; then
        safe_systemctl "Démarrage immédiat de CliOS" start clios.service
    fi
else
    echo -e "${C_BOLD}Vous pouvez maintenant démarrer CliOS depuis ce dossier :${C_RESET}\n"
    echo -e "  ${C_CYAN}./clios${C_RESET}                 # Lancement standard"
    echo -e "  ${C_CYAN}./clios --mock${C_RESET}          # Simulation sans matériel"
    echo -e "  ${C_CYAN}./clios --ui cli --mock${C_RESET} # Terminal interactif"
    echo -e "  ${C_CYAN}./clios --help${C_RESET}          # Options disponibles\n"
fi
