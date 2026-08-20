# Instructions pour la Release GitHub v1.21.1

## Informations de la release

- Tag : v1.21.1
- Target : main
- Release title :
CliOS v1.21.1 - Automated Installer, Wayland Kiosk Integration, and Sound DSP Engine

---

## Contenu a copier/coller dans la description :

## Overview

CliOS v1.21.1 introduces an automated interactive installation script, Cage Wayland kiosk integration for Raspberry Pi, improvements to the audio DSP synthesis pipeline, and refined QML telemetry views.

---

## Key Highlights & Features

### Automated System Installer (install.sh)
- Interactive setup script covering OS package resolution (apt, can-utils, cage).
- Automatic compilation and installation of pyo audio DSP library.
- Systemd service configuration (clios.service) for fast unattended kiosk boot without a heavy desktop environment.
- Hardware configuration presets for USB-CAN, slcan, and Candlelight adapters.

### Audio DSP & Engine Sound Pipeline
- Lazy loading for the Pyo library and graceful audio device initialization fallbacks.
- Integrated cabin noise level smoothing and ambient LED synchronization hooks.

### UI & Maintenance Improvements
- Fullscreen maintenance overlay accessible via touch actions or keyboard shortcuts (F12 / Ctrl+M).
- Enhanced theme switcher and layout refinements across Apex and Atelier Luxe dashboards.
- Touch gesture stabilization and event handling cleanup.

### Core Architecture & Stability
- Hardened exception handling within the service orchestrator lifecycle.
- OBD frame callback registration directly within the CAN service layer.
- Zero-hardware mock simulation improvements for cross-platform desktop development (./clios --mock).

---

## Quickstart

Run without hardware on macOS, Linux, or Windows:

```bash
git clone https://github.com/Tanchouteur/ClOS.git
cd ClOS
./clios --mock
```

Automated installation on Raspberry Pi (Debian/Ubuntu):

```bash
./install.sh
```

---

## Commits & Changes
- 4cfd13a: chore: bump version to 1.21.1
- 51082a1: feat: update documentation with comprehensive guides and French localization
- b7f6aba: feat: implement smoothing for cabin noise levels and enhance UI state properties
- bd30eff: feat: add maintenance menu access and update dashboard documentation
- 9b91a2a: feat: improve installation script with enhanced Python detection and pyo handling
- 2a08bb2: feat: add interactive installation script and CAN configuration guide
- 134eafb: feat: enhance CAN service with OBD callback registration
- 4029259: fix(touch): remove blocking MultiPointTouchArea and restore stable runtime
- d4a1a6c: fix: exception safety in orchestrator service lifecycle
- 46bc0da: feat: lazy load Pyo library and handle sounddevice import gracefully
